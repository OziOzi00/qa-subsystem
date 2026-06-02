"""
知识检索模块 - 成员3（Neo4j图谱查询与复杂问答负责人）

功能：
- 连接 Neo4j，执行 Cypher 查询
- 支持基于 object_id 的查询：收藏地、年代、作者、同作者作品、同朝代文物、相关文物推荐
- 支持统计类复杂问答：博物馆文物数量、某类型最多的博物馆
- 支持多跳关系问答：博物馆城市、同博物馆同朝代文物
- 无数据时返回 None/空列表，最终转为 NO_DATA
- 优先使用 intent.entities 中的实体，无法获取时返回 None（由上层转为 NO_DATA）
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, exceptions as neo4j_exceptions

from app.core.config import settings
from app.db.mysql import MySQLClient, MySQLConfig, get_mysql_dsn
from app.models.qa_pipeline import IntentResult, RetrievalResult
from app.repositories.mysql.artifact_repository import ArtifactDetail, ArtifactRepository
from app.schemas.qa import (
    AnswerSource,
    AnswerStatus,
    RelatedArtifact,
    ResolvedObject,
    SourceType,
)

logger = logging.getLogger(__name__)


_NEO4J_INTENTS = {
    "artifact_museum",
    "artifact_period",
    "artifact_artist",
    "same_artist_artifacts",
    "same_dynasty_artifacts",
    "related_artifacts",
    "statistics_count",
    "statistics_top_museum",
    "museum_city",
    "multi_hop_same_museum_dynasty",
}


class KnowledgeRetriever:
    """知识检索器：从 Neo4j 查询图数据，同时保留 MySQL 的接口（由成员2补充）"""

    def __init__(self, artifact_repository: ArtifactRepository | None = None) -> None:
        self._artifact_repository = artifact_repository
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
        if object_id == "DEMO_001":
            return self._retrieve_demo(intent)

        # 3. Neo4j owns graph relations and complex/statistical QA.
        if self.neo4j_driver is not None and intent.intent in _NEO4J_INTENTS:
            result = self._query_by_intent(intent, object_id)
            if result is not None:
                return result

        # 4. MySQL owns basic artifact fields and acts as a fallback for
        # shared facts when the graph has no result.
        if self._artifact_repository is not None and object_id:
            mysql_result = self._retrieve_mysql(intent, object_id)
            if mysql_result is not None:
                return mysql_result

        reason = "no_data_or_not_configured"
        if intent.intent in _NEO4J_INTENTS and self.neo4j_driver is None:
            reason = "neo4j_not_configured"
        elif self._artifact_repository is None:
            reason = "mysql_not_configured"

        return RetrievalResult(
            status=AnswerStatus.NO_DATA,
            facts=[],
            raw={"reason": reason},
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
            if intent.entities.get("dynasty"):
                return self._query_artifacts_by_dynasty_entity(str(intent.entities["dynasty"]))
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
            detailUrl=self._detail_url_for_object(object_id),
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
            detailUrl=self._detail_url_for_object(object_id),
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
            detailUrl=self._detail_url_for_object(object_id),
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
            detailUrl=self._detail_url_for_object(object_id),
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
            detailUrl=self._detail_url_for_object(object_id),
            factText="；".join(facts),
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[source],
            related_artifacts=related,
        )

    def _query_artifacts_by_dynasty_entity(self, dynasty: str) -> Optional[RetrievalResult]:
        """
        功能：查询某朝代的代表性文物。
        输入：朝代实体，如“明朝”“清”
        输出：代表性文物列表，不依赖当前 object_id。
        """
        normalized_dynasty = dynasty.strip()
        if not normalized_dynasty:
            return None
        dynasty_keyword = (
            normalized_dynasty.removesuffix("时期")
            .removesuffix("朝代")
            .removesuffix("朝")
            .removesuffix("代")
        ) or normalized_dynasty
        cypher = """
            MATCH (d:Dynasty)<-[:BELONGS_TO]-(a:Artifact)
            WHERE any(name IN [d.name_zh, d.name] WHERE
                name IS NOT NULL
                AND name <> ''
                AND (
                    name CONTAINS $dynasty
                    OR name CONTAINS $keyword
                    OR $dynasty CONTAINS name
                    OR $keyword CONTAINS name
                )
            )
            RETURN a.object_id AS object_id, a.title_zh AS title
            LIMIT 5
        """
        records = self._run_cypher_multi(
            cypher,
            dynasty=normalized_dynasty,
            keyword=dynasty_keyword,
        )
        if not records:
            return None

        facts = [f"{normalized_dynasty}相关代表性文物："]
        related = []
        seen: set[str] = set()
        for rec in records:
            oid = rec.get("object_id")
            if not oid or str(oid) in seen:
                continue
            seen.add(str(oid))
            title = rec.get("title") or str(oid)
            facts.append(f"- {title} ({oid})")
            artifact = self._artifact_detail_for_object(str(oid))
            related.append(RelatedArtifact(
                objectId=str(oid),
                title=str(title),
                reason=f"{normalized_dynasty}代表性文物",
                imageUrl=artifact.image_url if artifact else None,
            ))
        if not related:
            return None

        source = AnswerSource(
            sourceType=SourceType.NEO4J,
            sourceName="知识图谱·朝代代表文物",
            detailUrl=None,
            factText="；".join(facts),
            confidence=0.9,
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[source],
            related_artifacts=related,
            raw={"dataset": "neo4j", "dynasty": normalized_dynasty},
        )

    def _query_related_artifacts(self, object_id: str) -> Optional[RetrievalResult]:
        """
        功能：相关文物推荐（同作者优先，同朝代其次，同类型补充）
        输入：当前文物的 object_id
        输出：推荐文物列表
        """
        related = self._query_related_from_graph(object_id)
        related = self._append_mysql_type_related(object_id, related)
        if not related:
            return None
        related = related[:5]
        facts = [f"按同作者、同朝代或同类型规则，推荐 {len(related)} 件相关文物。"]
        facts.extend(
            f"- {item.title} ({item.object_id})：{item.reason or '相关文物'}"
            for item in related
        )
        return RetrievalResult(
            status=AnswerStatus.ANSWERED,
            facts=facts,
            sources=[
                AnswerSource(
                    sourceType=SourceType.NEO4J,
                    sourceName="知识图谱·相关文物推荐",
                    detailUrl=self._detail_url_for_object(object_id),
                    factText="；".join(facts),
                    confidence=0.85,
                )
            ],
            related_artifacts=related,
        )

    # =================== 3. 统计类复杂问答 ===================
    def _query_statistics_count(self, object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]:
        """
        统计类问答：某博物馆收藏文物数量。
        必须从 intent.entities 中获取博物馆名（成员4填充），缺少则返回 None。
        """
        museum_name = None
        if hasattr(intent, 'entities') and intent.entities:
            museum_name = intent.entities.get('museum')   # 只使用约定的键名 "museum"
        if not museum_name:
            # 缺少博物馆名，无法回答
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
        必须从 intent.entities 中获取类型名（成员4填充），缺少则返回 None。
        """
        artifact_type = None
        if hasattr(intent, 'entities') and intent.entities:
            artifact_type = intent.entities.get('artifact_type')   # 只使用约定的键名 "artifact_type"
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
        if not city:
            location = self._museum_location_for_name(str(museum) if museum else None)
            city = location.get("city") if location else None
        cnt = record.get("cnt", 0)
        location_text = f"（{city}）" if city else ""
        fact_text = f"收藏 {artifact_type} 最多的博物馆是 {museum}{location_text}，共 {cnt} 件"
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
                    MATCH (m:Museum)
                    WHERE m.name = $name OR m.name CONTAINS $name
                    RETURN m.name AS museum, m.city AS city
                    LIMIT 1
                """
                record = self._run_cypher(cypher, name=museum_name)
                museum = record.get("museum") if record else museum_name
                city = record.get("city") if record else None
                if not city:
                    location = self._museum_location_for_name(str(museum_name))
                    city = location.get("city") if location else None
                    museum = location.get("name") if location and location.get("name") else museum
                if city:
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
        # 方式2：通过文物 object_id 查询博物馆城市
        if object_id:
            cypher = """
                MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
                RETURN m.name AS museum, m.city AS city
                LIMIT 1
            """
            record = self._run_cypher(cypher, oid=object_id)
            if record:
                museum = record.get("museum")
                city = record.get("city")
                if not city:
                    location = self._museum_location_for_name(str(museum) if museum else None)
                    city = location.get("city") if location else None
                if not city:
                    return None
                fact_text = f"{museum} 位于 {city}"
                source = AnswerSource(
                    sourceType=SourceType.NEO4J,
                    sourceName="知识图谱·多跳",
                    detailUrl=self._detail_url_for_object(object_id),
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

    def _museum_location_for_name(self, museum_name: str | None) -> dict[str, str | None] | None:
        if self._artifact_repository is None or not museum_name:
            return None
        try:
            return self._artifact_repository.find_museum_by_name(museum_name)
        except Exception as exc:
            logger.warning("Failed to backfill museum location from MySQL: %s", exc)
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

    def _query_related_from_graph(self, object_id: str) -> list[RelatedArtifact]:
        cypher = """
            MATCH (a:Artifact {object_id: $oid})
            OPTIONAL MATCH (a)-[:CREATED_BY]->(:Artist)<-[:CREATED_BY]-(author_other:Artifact)
            WHERE author_other.object_id <> $oid
            OPTIONAL MATCH (a)-[:BELONGS_TO]->(:Dynasty)<-[:BELONGS_TO]-(dynasty_other:Artifact)
            WHERE dynasty_other.object_id <> $oid
            WITH collect({
                object_id: author_other.object_id,
                title: author_other.title_zh,
                reason: '同作者'
            }) + collect({
                object_id: dynasty_other.object_id,
                title: dynasty_other.title_zh,
                reason: '同朝代'
            }) AS rows
            UNWIND rows AS row
            WITH row
            WHERE row.object_id IS NOT NULL
            RETURN row.object_id AS object_id, row.title AS title, row.reason AS reason
            LIMIT 10
        """
        records = self._run_cypher_multi(cypher, oid=object_id)
        related: list[RelatedArtifact] = []
        seen: set[str] = set()
        for rec in records:
            oid = rec.get("object_id")
            if not oid or str(oid) in seen:
                continue
            seen.add(str(oid))
            artifact = self._artifact_detail_for_object(str(oid))
            related.append(
                RelatedArtifact(
                    objectId=str(oid),
                    title=str(rec.get("title") or (artifact.title if artifact else oid)),
                    reason=str(rec.get("reason") or "图谱关系相关"),
                    imageUrl=artifact.image_url if artifact else None,
                )
            )
        return related

    def _append_mysql_type_related(
        self,
        object_id: str,
        related: list[RelatedArtifact],
    ) -> list[RelatedArtifact]:
        if self._artifact_repository is None or len(related) >= 5:
            return related
        artifact = self._artifact_repository.find_by_object_id(object_id)
        if artifact is None or not artifact.type:
            return related

        seen = {item.object_id for item in related}
        for item in self._artifact_repository.find_related_by_type(
            object_id,
            artifact.type,
            limit=5,
        ):
            if item.object_id in seen:
                continue
            seen.add(item.object_id)
            related.append(
                RelatedArtifact(
                    objectId=item.object_id,
                    title=item.title,
                    reason=f"同类型 {artifact.type}",
                    imageUrl=item.image_url,
                )
            )
            if len(related) >= 5:
                break
        return related

    def _artifact_detail_for_object(self, object_id: str | None) -> ArtifactDetail | None:
        if self._artifact_repository is None or not object_id:
            return None
        try:
            return self._artifact_repository.find_by_object_id(object_id)
        except Exception:
            return None

    def _detail_url_for_object(self, object_id: str | None) -> str | None:
        artifact = self._artifact_detail_for_object(object_id)
        return artifact.detail_url if artifact else None

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
        """演示数据，仅供 DEMO_001 使用"""
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
    mysql_dsn = get_mysql_dsn()
    if not mysql_dsn:
        return KnowledgeRetriever()
    try:
        client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
    except ValueError:
        return KnowledgeRetriever()
    return KnowledgeRetriever(artifact_repository=ArtifactRepository(client))


knowledge_retriever = _build_default_retriever()
