import os

from app.models.qa_pipeline import IntentResult, RetrievalResult
from app.db.mysql import MySQLClient, MySQLConfig
from app.repositories.mysql.artifact_repository import ArtifactDetail, ArtifactRepository
from app.schemas.qa import (
    AnswerSource,
    AnswerStatus,
    RelatedArtifact,
    ResolvedObject,
    SourceType,
)


class KnowledgeRetriever:
    """Retrieve facts from MySQL and Neo4j.

    This scaffold keeps the pipeline runnable before databases are available.
    Member 2 and Member 3 can replace the private retrieval methods with real
    MySQL and Neo4j implementations.
    """

    def __init__(self, artifact_repository: ArtifactRepository | None = None) -> None:
        self._artifact_repository = artifact_repository

    def retrieve(
        self,
        intent: IntentResult,
        resolved_object: ResolvedObject,
        question: str,
    ) -> RetrievalResult:
        if intent.needs_object and resolved_object.object_id is None:
            return RetrievalResult(
                status=AnswerStatus.NEED_CLARIFICATION,
                raw={"reason": resolved_object.resolve_source},
            )

        if resolved_object.object_id == "DEMO_001":
            return self._retrieve_demo(intent)

        if self._artifact_repository is not None and resolved_object.object_id:
            mysql_result = self._retrieve_mysql(intent, resolved_object.object_id)
            if mysql_result is not None:
                return mysql_result

        if not intent.needs_object and intent.intent.startswith("statistics"):
            return RetrievalResult(
                status=AnswerStatus.NO_DATA,
                facts=[],
                raw={"reason": "statistics_query_requires_neo4j"},
            )

        return RetrievalResult(
            status=AnswerStatus.NO_DATA,
            facts=[],
            raw={"reason": "database_not_connected"},
        )

    def _retrieve_mysql(
        self,
        intent: IntentResult,
        object_id: str,
    ) -> RetrievalResult | None:
        if intent.intent not in _MYSQL_FACT_RENDERERS:
            return None

        artifact = self._artifact_repository.find_by_object_id(object_id)
        if artifact is None:
            return RetrievalResult(
                status=AnswerStatus.NO_DATA,
                facts=[],
                raw={"reason": "mysql_artifact_not_found", "objectId": object_id},
            )

        fact = _MYSQL_FACT_RENDERERS[intent.intent](artifact)
        if fact is None:
            return RetrievalResult(
                status=AnswerStatus.NO_DATA,
                facts=[],
                raw={
                    "reason": "mysql_fact_missing",
                    "artifactId": artifact.id,
                    "objectId": artifact.object_id,
                    "intent": intent.intent,
                },
            )

        source = AnswerSource(
            sourceType=SourceType.MYSQL,
            sourceName="公共 MySQL 文物基础表",
            detailUrl=artifact.detail_url,
            factText=fact,
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact],
            sources=[source],
            raw={
                "dataset": "mysql",
                "artifactId": artifact.id,
                "objectId": artifact.object_id,
            },
        )

    def _retrieve_demo(self, intent: IntentResult) -> RetrievalResult:
        base_source = AnswerSource(
            sourceType=SourceType.TEMPLATE,
            sourceName="QA Demo Dataset",
            detailUrl="https://www.clevelandart.org/art/collection/search",
            factText="演示数据用于验证知识问答子系统主流程。",
            confidence=0.8,
        )
        demo_facts = {
            "artifact_museum": ["演示文物 DEMO_001 现藏于克利夫兰艺术博物馆。"],
            "artifact_period": ["演示文物 DEMO_001 的年代为 Tang Dynasty。"],
            "artifact_material": ["演示文物 DEMO_001 的材质为 porcelain。"],
            "artifact_type": ["演示文物 DEMO_001 的类型为 ceramics。"],
            "artifact_description": ["演示文物 DEMO_001 是用于系统联调的文物介绍示例。"],
            "artifact_artist": [],
            "artist_biography": [],
            "same_artist_artifacts": [],
            "same_dynasty_artifacts": ["同一朝代演示查询返回 1 件代表性演示文物。"],
            "artifact_dimensions": ["演示文物 DEMO_001 的尺寸为 H. 30 cm x W. 20 cm。"],
            "related_artifacts": ["按同类型和同朝代规则，找到 1 件相关演示文物。"],
        }
        facts = demo_facts.get(intent.intent, [])
        if not facts:
            return RetrievalResult(
                status=AnswerStatus.NO_DATA,
                facts=[],
                sources=[base_source],
                raw={"reason": "demo_fact_missing"},
            )

        related = []
        if intent.intent in {"related_artifacts", "same_dynasty_artifacts"}:
            related = [
                RelatedArtifact(
                    objectId="DEMO_002",
                    title="相关演示文物",
                    reason="同类型、同朝代演示推荐",
                    imageUrl=None,
                )
            ]

        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[base_source],
            related_artifacts=related,
            raw={"dataset": "demo"},
        )


def _render_material(artifact: ArtifactDetail) -> str | None:
    if artifact.material is None:
        return None
    return f"{artifact.title}的材质为 {artifact.material}。"


def _render_type(artifact: ArtifactDetail) -> str | None:
    if artifact.type is None:
        return None
    return f"{artifact.title}的类型为 {artifact.type}。"


def _render_description(artifact: ArtifactDetail) -> str | None:
    if artifact.description is None:
        return None
    return artifact.description


def _render_dimensions(artifact: ArtifactDetail) -> str | None:
    if artifact.dimensions is None:
        return None
    return f"{artifact.title}的尺寸与规格为 {artifact.dimensions}。"


def _render_museum(artifact: ArtifactDetail) -> str | None:
    if artifact.museum_name is None:
        return None
    location = "，".join(
        part for part in [artifact.museum_city, artifact.museum_country] if part
    )
    suffix = f"（{location}）" if location else ""
    return f"{artifact.title}现藏于{artifact.museum_name}{suffix}。"


def _render_period(artifact: ArtifactDetail) -> str | None:
    period = artifact.dynasty_name or artifact.time_period
    if period is None:
        return None
    return f"{artifact.title}的年代为 {period}。"


def _render_artist_biography(artifact: ArtifactDetail) -> str | None:
    for artist in artifact.artists:
        if artist.biography:
            return f"{artist.name}的生平信息：{artist.biography}"
    return None


_MYSQL_FACT_RENDERERS = {
    "artifact_material": _render_material,
    "artifact_type": _render_type,
    "artifact_description": _render_description,
    "artifact_dimensions": _render_dimensions,
    "artifact_museum": _render_museum,
    "artifact_period": _render_period,
    "artist_biography": _render_artist_biography,
}


def _build_default_retriever() -> KnowledgeRetriever:
    mysql_dsn = os.getenv("MYSQL_DSN")
    if not mysql_dsn:
        return KnowledgeRetriever()
    try:
        client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
    except ValueError:
        return KnowledgeRetriever()
    return KnowledgeRetriever(artifact_repository=ArtifactRepository(client))


knowledge_retriever = _build_default_retriever()
