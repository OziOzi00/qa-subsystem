# Neo4j 查询方法说明（成员3实现）

本文件列出 `knowledge_retriever.py` 中每个查询方法的名称、输入、输出及对应意图。所有方法均返回 `RetrievalResult` 或 `None`。

## 基础查询（依赖 object_id）

### 1. `_query_museum(object_id: str) -> Optional[RetrievalResult]`
- 意图：`artifact_museum`
- 功能：查询文物收藏博物馆及城市
- 输出：事实文本 `"{object_id} 收藏于 {museum}（{city}）"`，来源类型 `neo4j`

### 2. `_query_dynasty(object_id: str) -> Optional[RetrievalResult]`
- 意图：`artifact_period`
- 功能：查询文物朝代
- 输出：`"{object_id} 的年代为 {dynasty}"`

### 3. `_query_artist(object_id: str) -> Optional[RetrievalResult]`
- 意图：`artifact_artist`
- 功能：查询书画作者
- 输出：`"{object_id} 的作者是 {artist}"`

### 4. `_query_artifacts_by_artist(object_id: str) -> Optional[RetrievalResult]`
- 意图：`same_artist_artifacts`
- 功能：查询同一作者的其他作品
- 输出：facts 列表包含作者信息和作品列表，sources 包含来源，related_artifacts 填充推荐文物

### 5. `_query_artifacts_by_dynasty(object_id: str) -> Optional[RetrievalResult]`
- 意图：`same_dynasty_artifacts`
- 功能：查询同一朝代的其他文物
- 输出：facts 和 related_artifacts 列表

### 6. `_query_related_artifacts(object_id: str) -> Optional[RetrievalResult]`
- 意图：`related_artifacts`
- 功能：相关文物推荐（基于同作者）
- 输出：related_artifacts 列表，facts 为简单统计

## 统计类复杂问答（使用 intent.entities）

### 7. `_query_statistics_count(object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]`
- 意图：`statistics_count`
- 输入：博物馆名（从 intent.entities["museum"] 读取，若缺少则返回 None）
- 功能：统计某博物馆收藏文物总数
- 输出：`"博物馆 {name} 收藏了 {count} 件文物"`

### 8. `_query_top_museum_by_type(object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]`
- 意图：`statistics_top_museum`
- 输入：文物类型（从 intent.entities["artifact_type"] 读取，若缺少则返回 None）
- 功能：查找收藏该类型文物最多的博物馆
- 输出：`"收藏 {type} 最多的博物馆是 {museum}（{city}），共 {cnt} 件"`

## 多跳关系问答

### 9. `_query_museum_city(object_id: Optional[str], intent: IntentResult) -> Optional[RetrievalResult]`
- 意图：`museum_city`
- 功能：查询博物馆所在城市（支持直接传博物馆名或通过文物 ID）
- 输出：`"{museum} 位于 {city}"`

### 10. `_query_multi_hop_same_museum_dynasty(object_id: str) -> Optional[RetrievalResult]`
- 意图：`multi_hop_same_museum_dynasty`（扩展示例）
- 功能：查询与当前文物同一博物馆且同一朝代的其他文物
- 输出：related_artifacts 列表，facts 为统计信息

## 辅助方法

- `_run_cypher(cypher, **params)`: 执行单条记录查询，返回字典或 None。
- `_run_cypher_multi(cypher, **params)`: 执行多条记录查询，返回字典列表。
- `_retrieve_demo(intent)`: 为 DEMO_001 提供假数据，用于前端联调，不依赖真实 Neo4j。

## 协作说明

- 成员4需在识别 `statistics_count`、`statistics_top_museum`、`museum_city` 意图时，将抽取的博物馆名或类型名填入 `IntentResult.entities`，键名分别为 `"museum"` 和 `"artifact_type"`。
- 若成员4未填充必要实体，查询将返回无数据（NO_DATA）。成员4需保证在 statistics_count、statistics_top_museum 意图中正确填充 entities。
- 所有无数据情况返回 `AnswerStatus.NO_DATA`，前端展示“暂无相关数据”，不编造答案。
