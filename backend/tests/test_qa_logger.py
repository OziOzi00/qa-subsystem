import asyncio
from uuid import UUID

from app.models.qa_pipeline import GeneratedAnswer, IntentResult, QAPipelineContext, RetrievalResult
from app.schemas.qa import AnswerSource, AnswerStatus, ResolvedObject, SourceType
from app.services.qa_logger import QALogger


class FakeLogRepository:
    def __init__(self) -> None:
        self.log_payloads: list[dict[str, object]] = []
        self.source_payloads: list[tuple[int, AnswerSource]] = []
        self.failed_payloads: list[dict[str, object]] = []

    def insert_log(self, payload: dict[str, object]) -> int:
        self.log_payloads.append(payload)
        return 99

    def insert_source(self, qa_log_id: int, source: AnswerSource) -> None:
        self.source_payloads.append((qa_log_id, source))

    def insert_failed_question(self, payload: dict[str, object]) -> None:
        self.failed_payloads.append(payload)


class FailingLogRepository(FakeLogRepository):
    def insert_log(self, payload: dict[str, object]) -> int:
        raise RuntimeError("database unavailable")


def _context(status: AnswerStatus = AnswerStatus.ANSWERED) -> QAPipelineContext:
    context = QAPipelineContext(
        question="它是什么材质？",
        object_id="MET_123",
        session_id="session-1",
        conversation_id="conversation-1",
        user_id=1001,
        source_client="web",
    )
    context.intent = IntentResult(
        intent="artifact_material",
        confidence=0.92,
        matched_keywords=["材质"],
        entities={"museum": "大英博物馆"},
    )
    context.resolved_object = ResolvedObject(
        objectId="MET_123",
        title="青花瓷",
        resolveSource="request_object_id",
    )
    context.retrieval = RetrievalResult(
        status=status,
        sources=[
            AnswerSource(
                sourceType=SourceType.MYSQL,
                sourceName="公共 MySQL 文物基础表",
                detailUrl="https://example.org/artifact",
                factText="青花瓷的材质为 porcelain。",
                confidence=0.9,
            )
        ],
        raw={"artifactId": 10},
    )
    context.generated_answer = GeneratedAnswer(
        status=status,
        answer="青花瓷的材质为 porcelain。",
        fact_content="青花瓷的材质为 porcelain。",
        supplemental_content="模板补充。",
    )
    return context


def test_record_persists_log_and_sources() -> None:
    repository = FakeLogRepository()
    logger = QALogger(repository=repository)

    qa_log_uuid = asyncio.run(logger.record(_context()))

    assert isinstance(qa_log_uuid, UUID)
    payload = repository.log_payloads[0]
    assert payload["qa_log_uuid"] == str(qa_log_uuid)
    assert payload["request_object_id"] == "MET_123"
    assert payload["object_id"] == "MET_123"
    assert payload["artifact_id"] == 10
    assert payload["intent"] == "artifact_material"
    assert payload["intent_detail_json"] == {
        "matchedKeywords": ["材质"],
        "entities": {"museum": "大英博物馆"},
        "confidence": 0.92,
    }
    assert payload["fact_content"] == "青花瓷的材质为 porcelain。"
    assert payload["supplemental_content"] == "模板补充。"
    assert repository.source_payloads == [(99, _context().retrieval.sources[0])]


def test_record_returns_uuid_when_repository_fails() -> None:
    logger = QALogger(repository=FailingLogRepository())

    qa_log_uuid = asyncio.run(logger.record(_context()))

    assert isinstance(qa_log_uuid, UUID)


def test_record_failed_if_needed_persists_no_data_failure() -> None:
    repository = FakeLogRepository()
    logger = QALogger(repository=repository)
    context = _context(status=AnswerStatus.NO_DATA)
    context.retrieval.raw = {"reason": "mysql_fact_missing"}

    asyncio.run(logger.record(context))
    asyncio.run(logger.record_failed_if_needed(context))

    assert repository.failed_payloads == [
        {
            "qa_log_id": 99,
            "session_id": "session-1",
            "user_id": 1001,
            "question": "它是什么材质？",
            "normalized_question": "它是什么材质？",
            "question_hash": repository.failed_payloads[0]["question_hash"],
            "intent": "artifact_material",
            "failure_type": "no_data",
            "artifact_id": None,
            "object_id": "MET_123",
            "error_detail": "mysql_fact_missing",
            "status": "open",
        }
    ]
    assert len(str(repository.failed_payloads[0]["question_hash"])) == 64


def test_record_failed_if_needed_maps_error_to_retrieval_error() -> None:
    repository = FakeLogRepository()
    logger = QALogger(repository=repository)
    context = _context(status=AnswerStatus.ERROR)
    context.retrieval.status = AnswerStatus.ERROR
    context.retrieval.raw = {"reason": "mysql_timeout"}

    asyncio.run(logger.record(context))
    asyncio.run(logger.record_failed_if_needed(context))

    assert repository.failed_payloads[0]["failure_type"] == "retrieval_error"
    assert repository.failed_payloads[0]["error_detail"] == "mysql_timeout"
