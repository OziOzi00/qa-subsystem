"""
知识检索模块 - 成员3（Neo4j图谱查询与复杂问答负责人）

功能：
- 连接 Neo4j，执行 Cypher 查询
- 支持基于 object_id 的查询：收藏地、年代、作者、同作者作品、同朝代文物、相关文物推荐
- 支持统计类复杂问答：博物馆文物数量、某类型最多的博物馆
- 支持多跳关系问答：博物馆城市、同博物馆同朝代文物
- 无数据时返回 None/空列表，最终转为 NO_DATA
- 优先使用 intent.entities 中的实体，回退使用 object_id（临时兼容）
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, exceptions as neo4j_exceptions

from app.core.config import settings
from app.models.qa_pipeline import IntentResult, RetrievalResult
from app.schemas.qa import (
    AnswerSource,
    AnswerStatus,
    RelatedArtifact,
    ResolvedObject,
    SourceType,
)

logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    """知识检索器：从 Neo4j 查询图数据，同时保留 MySQL 的接口（由成员2补充）"""

    def __init__(self):
        self.neo4j_driver = None
        self._init_neo4j()

    # ------------------- Neo4j 连接初始化 -------------------
    def _init_neo4j(self):
        """建立 Neo4j 连接（从环境变量读取配置）"""
        if not settings.NEO4J_URI:
            logger.warning("未配置 NEO4J_URI，所有 Neo4j 查询将返回无数据")
            return
        try:
            self.neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_lifetime=3600,
            )
            # 测试连接
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Neo4j 连接成功: {settings.NEO4J_URI}")
        except Exception as e:
            logger.error(f"Neo4j 连接失败: {e}")
            self.neo4j_driver = None

    # ------------------- 主入口 -------------------
    def retrieve(
        self,
        intent: IntentResult,
        resolved_object: ResolvedObject,
        question: str,
    ) -> RetrievalResult:
        """
        主入口：根据意图和已解析的文物对象，查询知识库并返回结果。
        """
        # 1. 需要文物对象但未提供 -> 需要用户澄清
        if intent.needs_object and resolved_object.object_id is None:
            return RetrievalResult(
                status=AnswerStatus.NEED_CLARIFICATION,
                raw={"reason": resolved_object.resolve_source},
            )

        object_id = resolved_object.object_id

        # 2. 演示文物走 mock 数据（用于前端联调）
        if object_id in ("DEMO_001", "DEMO_002"):
            return self._retrieve_demo(intent)

        # 3. 真实查询（Neo4j 相关意图）
        if self.neo4j_driver is not None:
            # 对于不需要 object_id 的统计/多跳查询，仍可处理
            result = self._query_by_intent(intent, object_id)
            if result is not None:
                return result

        # 4. 无数据或数据库不可用
        return RetrievalResult(
            status=AnswerStatus.NO_DATA,
            facts=[],
            raw={"reason": "no_data_or_not_configured"},
        )

    # ------------------- 意图路由 -------------------
    def _query_by_intent(self, intent: IntentResult, object_id: Optional[str]) -> Optional[RetrievalResult]:
        """根据意图类型，调用对应的 Neo4j 查询方法"""
        intent_type = intent.intent

        # 基础简单问答（需要 object_id）
        if intent_type == "artifact_museum":
            return self._query_museum(object_id) if object_id else None
        elif intent_type == "artifact_period":
            return self._query_dynasty(object_id) if object_id else None
        elif intent_type == "artifact_artist":
            return self._query_artist(object_id) if object_id else None
        elif intent_type == "same_artist_artifacts":
            return self._query_artifacts_by_artist(object_id) if object_id else None
        elif intent_type == "same_dynasty_artifacts":
            return self._query_artifacts_by_dynasty(object_id) if object_id else None
        elif intent_type == "related_artifacts":
            return self._query_related_artifacts(object_id) if object_id else None

        # 统计类复杂问答（优先使用 entities，回退 object_id）
        elif intent_type == "statistics_count":
            return self._query_statistics_count(object_id, intent)
        elif intent_type == "statistics_top_museum":
            return self._query_top_museum_by_type(object_id, intent)

        # 多跳关系问答
        elif intent_type == "museum_city":
            return self._query_museum_city(object_id, intent)

        # 扩展多跳示例（未在文档中定义，但可作为附加能力）
        elif intent_type == "multi_hop_same_museum_dynasty":
            return self._query_multi_hop_same_museum_dynasty(object_id) if object_id else None

        else:
            # 其他意图（如 MySQL 负责的材质、类型等）暂不处理
            return None

    # =================== 1. 基础简单查询（Neo4j） ===================
    def _query_museum(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：查询文物的收藏博物馆（Neo4j）
        输入：object_id
        输出：博物馆名称、城市等事实
        """
        cypher = """
            MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
            RETURN m.name AS museum_name, m.city AS city
            LIMIT 1
        """
        record = self._run_cypher(cypher, oid=object_id)
        if not record or not record.get("museum_name"):
            return None
        museum = record["museum_name"]
        city = record.get("city")
        fact_text = f"{object_id} 收藏于 {museum}"
        if city:
            fact_text += f"（{city}）"
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·收藏关系",
            detailUrl=None,
            factText=fact_text,
            confidence=0.95,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact_text],
            sources=[source],
            related_artifacts=[],
        )

    def _query_dynasty(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：查询文物的年代（朝代）
        输入：object_id
        输出：朝代名称
        """
        cypher = """
            MATCH (a:Artifact {object_id: $oid})-[:BELONGS_TO]->(d:Dynasty)
            RETURN d.name_zh AS dynasty
            LIMIT 1
        """
        record = self._run_cypher(cypher, oid=object_id)
        if not record or not record.get("dynasty"):
            return None
        dynasty = record["dynasty"]
        fact_text = f"{object_id} 的年代为 {dynasty}"
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·年代关系",
            detailUrl=None,
            factText=fact_text,
            confidence=0.95,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact_text],
            sources=[source],
            related_artifacts=[],
        )

    def _query_artist(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：查询文物的作者（仅书画类）
        输入：object_id
        输出：作者名称
        """
        cypher = """
            MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)
            RETURN art.name_zh AS artist
            LIMIT 1
        """
        record = self._run_cypher(cypher, oid=object_id)
        if not record or not record.get("artist"):
            return None
        artist = record["artist"]
        fact_text = f"{object_id} 的作者是 {artist}"
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·作者关系",
            detailUrl=None,
            factText=fact_text,
            confidence=0.95,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact_text],
            sources=[source],
            related_artifacts=[],
        )

    # =================== 2. 复杂查询（同一作者/朝代、推荐） ===================
    def _query_artifacts_by_artist(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：查询同一作者的其他作品
        输入：当前文物的 object_id
        输出：其他文物列表（objectId, title）
        """
        # 第一步：获取当前文物的作者
        cypher_artist = """
            MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)
            RETURN art.name_zh AS artist
            LIMIT 1
        """
        artist_rec = self._run_cypher(cypher_artist, oid=object_id)
        if not artist_rec or not artist_rec.get("artist"):
            return None
        artist = artist_rec["artist"]

        # 第二步：查询该作者创作的其他文物
        cypher_others = """
            MATCH (art:Artist {name_zh: $artist})-[:CREATED_BY]-(other:Artifact)
            WHERE other.object_id <> $oid
            RETURN other.object_id AS object_id, other.title_zh AS title
            LIMIT 5
        """
        records = self._run_cypher_multi(cypher_others, artist=artist, oid=object_id)
        if not records:
            return None

        facts = [f"与 {artist} 相关的其他文物："]
        related = []
        for rec in records:
            oid = rec.get("object_id")
            title = rec.get("title", oid)
            facts.append(f"- {title} ({oid})")
            related.append(RelatedArtifact(
                objectId=oid,
                title=title,
                reason=f"同作者 {artist}",
                imageUrl=None,
            ))
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·同作者作品",
            detailUrl=None,
            factText="；".join(facts),
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[source],
            related_artifacts=related,
        )

    def _query_artifacts_by_dynasty(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：查询同一朝代的其他文物
        输入：当前文物的 object_id
        输出：其他文物列表
        """
        cypher_dynasty = """
            MATCH (a:Artifact {object_id: $oid})-[:BELONGS_TO]->(d:Dynasty)
            RETURN d.name_zh AS dynasty
            LIMIT 1
        """
        dynasty_rec = self._run_cypher(cypher_dynasty, oid=object_id)
        if not dynasty_rec or not dynasty_rec.get("dynasty"):
            return None
        dynasty = dynasty_rec["dynasty"]

        cypher_others = """
            MATCH (d:Dynasty {name_zh: $dynasty})-[:BELONGS_TO]-(other:Artifact)
            WHERE other.object_id <> $oid
            RETURN other.object_id AS object_id, other.title_zh AS title
            LIMIT 5
        """
        records = self._run_cypher_multi(cypher_others, dynasty=dynasty, oid=object_id)
        if not records:
            return None

        facts = [f"与 {dynasty} 同朝代的其他文物："]
        related = []
        for rec in records:
            oid = rec.get("object_id")
            title = rec.get("title", oid)
            facts.append(f"- {title} ({oid})")
            related.append(RelatedArtifact(
                objectId=oid,
                title=title,
                reason=f"同朝代 {dynasty}",
                imageUrl=None,
            ))
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·同朝代文物",
            detailUrl=None,
            factText="；".join(facts),
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[source],
            related_artifacts=related,
        )

    def _query_related_artifacts(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：相关文物推荐（基础版：同作者优先，可扩展同朝代、同类型）
        输入：当前文物的 object_id
        输出：推荐文物列表
        """
        # 简化：基于同作者推荐（也可改为 UNION 同朝代）
        cypher = """
            MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)<-[:CREATED_BY]-(other:Artifact)
            WHERE other.object_id <> $oid
            RETURN other.object_id AS object_id, other.title_zh AS title, '同作者' as reason
            LIMIT 5
        """
        records = self._run_cypher_multi(cypher, oid=object_id)
        if not records:
            return None
        related = []
        for rec in records:
            related.append(RelatedArtifact(
                objectId=rec["object_id"],
                title=rec.get("title", rec["object_id"]),
                reason=rec["reason"],
                imageUrl=None,
            ))
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[f"推荐 {len(related)} 件相关文物"],
            sources=[],
            related_artifacts=related,
        )

    # =================== 3. 统计类复杂问答 ===================
    def _query_statistics_count(self, object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]:
        """
        统计类问答：某博物馆收藏文物数量。
        优先从 intent.entities 中获取博物馆名（成员4填充），
        若没有则回退使用 object_id（仅用于开发测试）。
        """
        museum_name = None
        if hasattr(intent, 'entities') and intent.entities:
            museum_name = intent.entities.get('museum') or intent.entities.get('organization')
        if not museum_name:
            museum_name = object_id
        if not museum_name:
            return None

        cypher = """
            MATCH (m:Museum)-[:COLLECTED_BY]-(a:Artifact)
            WHERE m.name CONTAINS $name
            RETURN count(a) AS count
        """
        record = self._run_cypher(cypher, name=museum_name)
        if not record:
            return None
        count = record.get("count", 0)
        fact_text = f"博物馆 {museum_name} 收藏了 {count} 件文物"
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·统计",
            detailUrl=None,
            factText=fact_text,
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact_text],
            sources=[source],
            related_artifacts=[],
        )

    def _query_top_museum_by_type(self, object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]:
        """
        收藏某类型文物最多的博物馆及所在城市。
        优先从 intent.entities 中获取类型名，若没有则回退使用 object_id。
        """
        artifact_type = None
        if hasattr(intent, 'entities') and intent.entities:
            artifact_type = intent.entities.get('artifact_type') or intent.entities.get('type')
        if not artifact_type:
            artifact_type = object_id
        if not artifact_type:
            return None

        cypher = """
            MATCH (a:Artifact {type: $type})-[:COLLECTED_BY]->(m:Museum)
            RETURN m.name AS museum, m.city AS city, count(a) AS cnt
            ORDER BY cnt DESC
            LIMIT 1
        """
        record = self._run_cypher(cypher, type=artifact_type)
        if not record:
            return None
        museum = record.get("museum")
        city = record.get("city")
        cnt = record.get("cnt", 0)
        fact_text = f"收藏 {artifact_type} 最多的博物馆是 {museum}（{city}），共 {cnt} 件"
        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·统计",
            detailUrl=None,
            factText=fact_text,
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[fact_text],
            sources=[source],
            related_artifacts=[],
        )

    # =================== 4. 多跳关系问答 ===================
    def _query_museum_city(self, object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]:
        """
        多跳问答：查询文物所在博物馆的城市（两跳：文物→博物馆→城市）。
        如果提供了 intent.entities 中的 museum，也可直接查。
        """
        # 方式1：如果有 museum 实体，直接查询博物馆城市
        if hasattr(intent, 'entities') and intent.entities:
            museum_name = intent.entities.get('museum')
            if museum_name:
                cypher = """
                    MATCH (m:Museum {name: $name})
                    RETURN m.city AS city
                """
                record = self._run_cypher(cypher, name=museum_name)
                if record and record.get("city"):
                    city = record["city"]
                    fact_text = f"{museum_name} 位于 {city}"
                    source = AnswerSource(
                        sourceType=SourceType.NEO4J,
                        sourceName="知识图谱·多跳",
                        detailUrl=None,
                        factText=fact_text,
                        confidence=0.95,
                    )
                    return RetrievalResult(
                        status=AnswerStatus.ANSWERED,
                        facts=[fact_text],
                        sources=[source],
                        related_artifacts=[],
                    )
        # 方式2：通过文物 object_id 查询博物馆城市
        if object_id:
            cypher = """
                MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
                RETURN m.name AS museum, m.city AS city
                LIMIT 1
            """
            record = self._run_cypher(cypher, oid=object_id)
            if record and record.get("city"):
                museum = record.get("museum")
                city = record.get("city")
                fact_text = f"{museum} 位于 {city}"
                source = AnswerSource(
                    sourceType=SourceType.NEO4J,
                    sourceName="知识图谱·多跳",
                    detailUrl=None,
                    factText=fact_text,
                    confidence=0.95,
                )
                return RetrievalResult(
                    status=AnswerStatus.ANSWERED,
                    facts=[fact_text],
                    sources=[source],
                    related_artifacts=[],
                )
        return None

    def _query_multi_hop_same_museum_dynasty(self, object_id: str) -> Optional[RetrievalResult]:
        """
        简单多跳示例：查询与当前文物同一博物馆、同一朝代的其他文物。
        这是一个典型的两跳+条件查询，用于展示多跳能力。
        """
        cypher = """
            MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
            MATCH (a)-[:BELONGS_TO]->(d:Dynasty)
            MATCH (other:Artifact)-[:COLLECTED_BY]->(m)
            WHERE other <> a AND (other)-[:BELONGS_TO]->(d)
            RETURN other.object_id AS object_id, other.title_zh AS title
            LIMIT 5
        """
        records = self._run_cypher_multi(cypher, oid=object_id)
        if not records:
            return None
        related = []
        for rec in records:
            related.append(RelatedArtifact(
                objectId=rec["object_id"],
                title=rec.get("title", rec["object_id"]),
                reason="同博物馆且同朝代",
                imageUrl=None,
            ))
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=[f"找到 {len(related)} 件同博物馆且同朝代的文物"],
            sources=[],
            related_artifacts=related,
        )

    # =================== 辅助方法 ===================
    def _run_cypher(self, cypher: str, **params) -> Optional[Dict[str, Any]]:
        """执行单条记录的 Cypher 查询，返回第一条记录（字典），若无结果返回 None"""
        if not self.neo4j_driver:
            return None
        try:
            with self.neo4j_driver.session() as session:
                result = session.run(cypher, **params)
                record = result.single()
                return dict(record) if record else None
        except neo4j_exceptions.Neo4jError as e:
            logger.error(f"Cypher 执行错误: {e}")
            return None

    def _run_cypher_multi(self, cypher: str, **params) -> List[Dict[str, Any]]:
        """执行多条记录的 Cypher 查询，返回记录列表"""
        if not self.neo4j_driver:
            return []
        try:
            with self.neo4j_driver.session() as session:
                result = session.run(cypher, **params)
                return [dict(record) for record in result]
        except neo4j_exceptions.Neo4jError as e:
            logger.error(f"Cypher 多行查询错误: {e}")
            return []

    # =================== Demo 模式（用于联调） ===================
    def _retrieve_demo(self, intent: IntentResult) -> RetrievalResult:
        """演示数据，仅供 DEMO_001/002 使用"""
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
            # 为统计和多跳意图也提供演示数据（可选）
            "statistics_count": ["博物馆 British Museum 收藏了 123 件文物（演示数据）"],
            "statistics_top_museum": ["收藏 ceramics 最多的博物馆是大英博物馆，共 45 件（演示数据）"],
            "museum_city": ["克利夫兰艺术博物馆位于克利夫兰（演示数据）"],
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


# 单例实例（供主接口导入）
knowledge_retriever = KnowledgeRetriever()