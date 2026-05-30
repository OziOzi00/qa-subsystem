from app.models.qa_pipeline import IntentResult
from app.repositories.mysql.artifact_repository import ArtifactDetail, ArtistSummary
from app.schemas.qa import AnswerStatus, ResolvedObject, SourceType
from app.services.knowledge_retriever import KnowledgeRetriever


class FakeArtifactRepository:
    def __init__(self, artifact: ArtifactDetail | None) -> None:
        self.artifact = artifact
        self.object_ids: list[str] = []

    def find_by_object_id(self, object_id: str | None) -> ArtifactDetail | None:
        assert object_id is not None
        self.object_ids.append(object_id)
        return self.artifact


def _artifact(**overrides) -> ArtifactDetail:
    values = {
        "id": 10,
        "object_id": "MET_123",
        "title": "青花瓷",
        "title_en": "Blue Porcelain",
        "time_period": "Ming dynasty",
        "dynasty_name": "明",
        "type": "Ceramics",
        "material": "porcelain",
        "description": "A porcelain artifact.",
        "dimensions": "H. 10 cm",
        "museum_name": "British Museum",
        "museum_country": "United Kingdom",
        "museum_city": "London",
        "detail_url": "https://example.org/artifact",
        "image_url": None,
        "artists": [ArtistSummary(id=7, name="佚名", biography="作者生平示例。")],
    }
    values.update(overrides)
    return ArtifactDetail(**values)


def test_retrieve_mysql_material_returns_fact_and_source() -> None:
    repository = FakeArtifactRepository(_artifact())
    retriever = KnowledgeRetriever(artifact_repository=repository)

    result = retriever.retrieve(
        intent=IntentResult(intent="artifact_material", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="它是什么材质？",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.facts == ["青花瓷的材质为 porcelain。"]
    assert result.sources[0].source_type == SourceType.MYSQL
    assert result.sources[0].source_name == "公共 MySQL 文物基础表"
    assert result.sources[0].detail_url == "https://example.org/artifact"
    assert result.sources[0].fact_text == "青花瓷的材质为 porcelain。"
    assert result.raw["artifactId"] == 10
    assert repository.object_ids == ["MET_123"]


def test_retrieve_mysql_empty_dimensions_returns_no_data() -> None:
    retriever = KnowledgeRetriever(
        artifact_repository=FakeArtifactRepository(_artifact(dimensions=None))
    )

    result = retriever.retrieve(
        intent=IntentResult(intent="artifact_dimensions", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="它的尺寸是多少？",
    )

    assert result.status == AnswerStatus.NO_DATA
    assert result.facts == []
    assert result.raw["reason"] == "mysql_fact_missing"


def test_retrieve_without_repository_keeps_demo_dataset_available() -> None:
    retriever = KnowledgeRetriever()

    result = retriever.retrieve(
        intent=IntentResult(intent="artifact_material", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="DEMO_001",
            title=None,
            resolveSource="request_object_id",
        ),
        question="演示文物是什么材质？",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.facts == ["演示文物 DEMO_001 的材质为 porcelain。"]


def test_graph_intent_falls_back_to_mysql_when_neo4j_unavailable() -> None:
    repository = FakeArtifactRepository(_artifact())
    retriever = KnowledgeRetriever(artifact_repository=repository)
    retriever.neo4j_driver = None

    result = retriever.retrieve(
        intent=IntentResult(intent="artifact_museum", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="Where is it collected?",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.sources[0].source_type == SourceType.MYSQL
    assert "British Museum" in result.facts[0]


def test_graph_intent_without_databases_returns_neo4j_not_configured() -> None:
    retriever = KnowledgeRetriever()
    retriever.neo4j_driver = None

    result = retriever.retrieve(
        intent=IntentResult(intent="related_artifacts", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="Recommend related artifacts.",
    )

    assert result.status == AnswerStatus.NO_DATA
    assert result.raw["reason"] == "neo4j_not_configured"
