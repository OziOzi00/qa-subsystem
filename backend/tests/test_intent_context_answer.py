from fastapi.testclient import TestClient

from app.models.qa_pipeline import IntentResult, RetrievalResult
from app.schemas.qa import AnswerStatus, AskRequest, ResolvedObject, SourceType
from app.services.answer_generator import AnswerGenerator
from app.services.intent_recognizer import IntentRecognizer
from app.services.object_resolver import ObjectResolver
from app.services.session_context import SessionContextStore
from app.main import app


def test_recognizes_eleven_simple_intents() -> None:
    recognizer = IntentRecognizer()
    cases = {
        "这件文物收藏在哪里？": "artifact_museum",
        "这件文物是什么朝代的？": "artifact_period",
        "这件文物的材质是什么？": "artifact_material",
        "这件文物属于什么类型？": "artifact_type",
        "介绍一下这件文物": "artifact_description",
        "这幅画的作者是谁？": "artifact_artist",
        "作者生平是什么？": "artist_biography",
        "同一作者还有哪些作品？": "same_artist_artifacts",
        "同一朝代还有哪些文物？": "same_dynasty_artifacts",
        "这件文物的尺寸是多少？": "artifact_dimensions",
        "推荐相关文物": "related_artifacts",
    }

    for question, expected_intent in cases.items():
        result = recognizer.recognize(question)
        assert result.intent == expected_intent
        assert result.needs_object is True


def test_recognizes_complex_intents_and_entities() -> None:
    recognizer = IntentRecognizer()

    count = recognizer.recognize("大英博物馆收藏了多少件中国文物？")
    assert count.intent == "statistics_count"
    assert count.needs_object is False
    assert count.entities == {"museum": "大英博物馆"}

    top = recognizer.recognize("收藏瓷器最多的博物馆是哪个？")
    assert top.intent == "statistics_top_museum"
    assert top.needs_object is False
    assert top.entities == {"artifact_type": "瓷器"}

    city = recognizer.recognize("大英博物馆位于哪个城市？")
    assert city.intent == "museum_city"
    assert city.needs_object is False
    assert city.entities == {"museum": "大英博物馆"}

    dynasty = recognizer.recognize("明朝有哪些代表性文物？")
    assert dynasty.intent == "same_dynasty_artifacts"
    assert dynasty.needs_object is False
    assert dynasty.entities == {"dynasty": "明朝"}


def test_recognizes_english_museum_entities_for_real_dataset() -> None:
    recognizer = IntentRecognizer()

    count = recognizer.recognize("The Metropolitan Museum of Art 收藏了多少件中国文物？")
    assert count.intent == "statistics_count"
    assert count.needs_object is False
    assert count.entities == {"museum": "The Metropolitan Museum of Art"}

    city = recognizer.recognize("The Metropolitan Museum of Art 位于哪个城市？")
    assert city.intent == "museum_city"
    assert city.needs_object is False
    assert city.entities == {"museum": "The Metropolitan Museum of Art"}


def test_pronoun_museum_city_uses_object_context() -> None:
    recognizer = IntentRecognizer()

    result = recognizer.recognize("该文物所在的博物馆在哪个城市？")

    assert result.intent == "museum_city"
    assert result.needs_object is True
    assert result.entities == {}


def test_explicit_object_id_wins_over_ambiguous_question_candidates(monkeypatch) -> None:
    class FakeCandidate:
        def __init__(self, object_id: str) -> None:
            self.object_id = object_id
            self.title = "花瓶"

        def to_response_candidate(self):
            return {"objectId": self.object_id, "title": self.title}

    monkeypatch.setattr(
        "app.services.object_resolver.artifact_matcher.match",
        lambda question: [FakeCandidate("1"), FakeCandidate("5")],
    )

    resolved = ObjectResolver().resolve(
        AskRequest(
            question="介绍一下花瓶",
            objectId="5",
            sessionId="candidate-confirm-test",
        ),
        IntentResult(intent="artifact_description", confidence=0.8),
    )

    assert resolved.object_id == "5"
    assert resolved.resolve_source == "request_object_id"
    assert resolved.candidates == []


def test_unique_question_entity_does_not_return_choice_candidates(monkeypatch) -> None:
    class FakeCandidate:
        object_id = "161"
        title = "犀牛角杯"

        def to_response_candidate(self):
            return {"objectId": self.object_id, "title": self.title}

    monkeypatch.setattr(
        "app.services.object_resolver.artifact_matcher.match",
        lambda question: [FakeCandidate()],
    )

    resolved = ObjectResolver().resolve(
        AskRequest(
            question="介绍一下犀牛角杯",
            sessionId="unique-candidate-test",
        ),
        IntentResult(intent="artifact_description", confidence=0.8),
    )

    assert resolved.object_id == "161"
    assert resolved.resolve_source == "question_entity"
    assert resolved.candidates == []


def test_session_context_keeps_latest_five_turns() -> None:
    store = SessionContextStore()
    resolved = ResolvedObject(
        objectId="DEMO_001",
        title="演示文物",
        resolveSource="request_object_id",
    )

    for index in range(6):
        store.update_current_object("s1", resolved)
        store.append_turn(
            "s1",
            question=f"问题 {index}",
            intent="artifact_material",
            resolved_object=resolved,
            status="answered",
        )

    turns = store.get_recent_turns("s1")
    assert len(turns) == 5
    assert turns[0]["question"] == "问题 1"
    assert turns[-1]["objectId"] == "DEMO_001"


def test_answer_generator_uses_clear_no_data_template() -> None:
    generator = AnswerGenerator()

    answer = generator.generate(
        intent=IntentResult(intent="artifact_material", confidence=0.8),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        retrieval=RetrievalResult(status=AnswerStatus.NO_DATA),
    )

    assert answer.status == AnswerStatus.NO_DATA
    assert answer.answer == "暂无该文物材质数据。"


class FakeSupplementGenerator:
    is_configured = True

    def generate_supplement(self, **kwargs):
        class Result:
            content = "该文物的事实信息已由知识库检索确认。"
            model = "fake-rag-model"

        return Result()


def test_answer_generator_adds_llm_supplement_source_when_configured() -> None:
    generator = AnswerGenerator(supplement_generator=FakeSupplementGenerator())
    retrieval = RetrievalResult(
        status=AnswerStatus.ANSWERED,
        facts=["青花瓷的材质为 porcelain。"],
    )

    answer = generator.generate(
        intent=IntentResult(intent="artifact_material", confidence=0.8),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title="青花瓷",
            resolveSource="request_object_id",
        ),
        retrieval=retrieval,
        question="这件文物的材质是什么？",
    )

    assert answer.status == AnswerStatus.ANSWERED
    assert answer.fact_content == "青花瓷的材质为 porcelain。"
    assert answer.supplemental_content == "该文物的事实信息已由知识库检索确认。"
    assert retrieval.sources[-1].source_type == SourceType.LLM


def test_ask_endpoint_uses_demo_object_and_records_context() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/qa/ask",
        json={
            "question": "演示文物的材质是什么？",
            "objectId": "DEMO_001",
            "sessionId": "member4-test-session",
        },
    )

    data = response.json()
    assert response.status_code == 200
    assert data["intent"] == "artifact_material"
    assert data["status"] == "answered"
    assert data["resolvedObject"]["objectId"] == "DEMO_001"
    assert data["debug"]["recentContext"]
