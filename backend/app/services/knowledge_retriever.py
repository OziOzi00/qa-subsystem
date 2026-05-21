from app.models.qa_pipeline import IntentResult, RetrievalResult
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


knowledge_retriever = KnowledgeRetriever()
