from app.models.qa_pipeline import IntentResult
from app.repositories.mysql.artifact_repository import ArtifactDetail, ArtistSummary
from app.schemas.qa import AnswerStatus, ResolvedObject, SourceType
from app.services.knowledge_retriever import KnowledgeRetriever


class FakeArtifactRepository:
    def __init__(self, artifact: ArtifactDetail | None) -> None:
        self.artifact = artifact
        self.object_ids: list[str] = []
        self.related_by_type: list[ArtifactDetail] = []

    def find_by_object_id(self, object_id: str | None) -> ArtifactDetail | None:
        assert object_id is not None
        self.object_ids.append(object_id)
        return self.artifact

    def find_related_by_type(
        self,
        object_id: str,
        artifact_type: str | None,
        limit: int = 5,
    ) -> list[ArtifactDetail]:
        return self.related_by_type[:limit]

    def find_museum_by_name(self, museum_name: str | None) -> dict[str, str | None] | None:
        if museum_name == "The Metropolitan Museum of Art":
            return {
                "name": "The Metropolitan Museum of Art",
                "city": "New York",
                "country": "United States",
            }
        if museum_name == "Philadelphia Museum of Art":
            return {
                "name": "Philadelphia Museum of Art",
                "city": "Philadelphia",
                "country": "United States",
            }
        return None


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


def test_neo4j_source_uses_mysql_detail_url_when_available() -> None:
    repository = FakeArtifactRepository(_artifact())
    retriever = KnowledgeRetriever(artifact_repository=repository)
    retriever.neo4j_driver = object()
    retriever._run_cypher = lambda *args, **kwargs: {
        "museum_name": "British Museum",
        "city": "London",
    }

    result = retriever.retrieve(
        intent=IntentResult(intent="artifact_museum", confidence=0.75),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="它收藏在哪里？",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.sources[0].source_type == SourceType.NEO4J
    assert result.sources[0].detail_url == "https://example.org/artifact"


def test_dynasty_entity_query_does_not_require_object_id() -> None:
    retriever = KnowledgeRetriever()
    retriever.neo4j_driver = object()
    retriever._run_cypher_multi = lambda *args, **kwargs: [
        {"object_id": "QING_001", "title": "清代瓷器"},
    ]

    result = retriever.retrieve(
        intent=IntentResult(
            intent="same_dynasty_artifacts",
            confidence=0.84,
            entities={"dynasty": "清朝"},
            needs_object=False,
        ),
        resolved_object=ResolvedObject(
            objectId=None,
            title=None,
            resolveSource="not_required_for_intent",
        ),
        question="清朝有哪些代表性文物？",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.related_artifacts[0].object_id == "QING_001"
    assert "清朝相关代表性文物" in result.facts[0]


def test_related_artifacts_merge_graph_and_mysql_type_results() -> None:
    repository = FakeArtifactRepository(_artifact(type="Ceramics"))
    repository.related_by_type = [
        _artifact(id=11, object_id="MYSQL_001", title="同类型瓷器"),
    ]
    retriever = KnowledgeRetriever(artifact_repository=repository)
    retriever.neo4j_driver = object()
    retriever._run_cypher_multi = lambda *args, **kwargs: [
        {"object_id": "GRAPH_001", "title": "同朝代瓷器", "reason": "同朝代"},
    ]

    result = retriever.retrieve(
        intent=IntentResult(intent="related_artifacts", confidence=0.78),
        resolved_object=ResolvedObject(
            objectId="MET_123",
            title=None,
            resolveSource="request_object_id",
        ),
        question="推荐相关文物",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert [item.object_id for item in result.related_artifacts] == [
        "GRAPH_001",
        "MYSQL_001",
    ]
    assert result.sources[0].source_type == SourceType.NEO4J


def test_museum_city_backfills_city_from_mysql_when_graph_has_no_city() -> None:
    repository = FakeArtifactRepository(_artifact())
    retriever = KnowledgeRetriever(artifact_repository=repository)
    retriever.neo4j_driver = object()
    retriever._run_cypher = lambda *args, **kwargs: {
        "museum": "The Metropolitan Museum of Art",
        "city": None,
    }

    result = retriever.retrieve(
        intent=IntentResult(
            intent="museum_city",
            confidence=0.9,
            entities={"museum": "The Metropolitan Museum of Art"},
            needs_object=False,
        ),
        resolved_object=ResolvedObject(
            objectId=None,
            title=None,
            resolveSource="not_required_for_intent",
        ),
        question="The Metropolitan Museum of Art 位于哪个城市？",
    )

    assert result.status == AnswerStatus.ANSWERED
    assert result.facts == ["The Metropolitan Museum of Art 位于 New York"]
    assert result.sources[0].source_type == SourceType.NEO4J


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
