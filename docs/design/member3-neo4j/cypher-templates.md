# Cypher 查询模板（成员3所有查询）

说明：以下模板中的 `$oid` 表示文物 object_id，`$name` 表示博物馆名称，`$type` 表示文物类型。所有查询在代码中通过 `_run_cypher` 或 `_run_cypher_multi` 执行。

## 1. 文物收藏地（intent: artifact_museum）

    MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
    RETURN m.name AS museum_name, m.city AS city
    LIMIT 1

返回：博物馆名称和城市，若城市不存在则只返回名称。

## 2. 文物年代（intent: artifact_period）

    MATCH (a:Artifact {object_id: $oid})-[:BELONGS_TO]->(d:Dynasty)
    RETURN d.name_zh AS dynasty
    LIMIT 1

返回：朝代名称（如“唐代”）。

## 3. 书画作者（intent: artifact_artist）

    MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)
    RETURN art.name_zh AS artist
    LIMIT 1

返回：作者名称。

## 4. 同一作者作品（intent: same_artist_artifacts）

第一步：获取作者名

    MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)
    RETURN art.name_zh AS artist
    LIMIT 1

第二步：查询该作者的其他文物

    MATCH (art:Artist {name_zh: $artist})-[:CREATED_BY]-(other:Artifact)
    WHERE other.object_id <> $oid
    RETURN other.object_id AS object_id, other.title_zh AS title
    LIMIT 5

返回：最多5件其他文物的 object_id 和 title。

## 5. 同一朝代文物（intent: same_dynasty_artifacts）

第一步：获取朝代名

    MATCH (a:Artifact {object_id: $oid})-[:BELONGS_TO]->(d:Dynasty)
    RETURN d.name_zh AS dynasty
    LIMIT 1

第二步：查询同朝代的其他文物

    MATCH (d:Dynasty {name_zh: $dynasty})-[:BELONGS_TO]-(other:Artifact)
    WHERE other.object_id <> $oid
    RETURN other.object_id AS object_id, other.title_zh AS title
    LIMIT 5

## 6. 相关文物推荐（intent: related_artifacts）

    MATCH (a:Artifact {object_id: $oid})-[:CREATED_BY]->(art:Artist)<-[:CREATED_BY]-(other:Artifact)
    WHERE other.object_id <> $oid
    RETURN other.object_id AS object_id, other.title_zh AS title, '同作者' as reason
    LIMIT 5

返回：推荐列表，理由为“同作者”。未来可扩展同朝代、同类型。

## 7. 统计博物馆文物数量（intent: statistics_count）

输入：博物馆名称（来自 intent.entities["museum"]，若缺少则返回无数据）

    MATCH (m:Museum)-[:COLLECTED_BY]-(a:Artifact)
    WHERE m.name CONTAINS $name
    RETURN count(a) AS count

返回：该博物馆收藏的文物总数。

## 8. 收藏某类型最多的博物馆（intent: statistics_top_museum）

输入：文物类型（来自 intent.entities["artifact_type"]，若缺少则返回无数据）

    MATCH (a:Artifact {type: $type})-[:COLLECTED_BY]->(m:Museum)
    RETURN m.name AS museum, m.city AS city, count(a) AS cnt
    ORDER BY cnt DESC
    LIMIT 1

返回：收藏该类型文物最多的博物馆名称、城市及数量。

## 9. 博物馆城市（多跳，intent: museum_city）

方式A：直接通过博物馆名称查询（如果 entities 中有 museum）

    MATCH (m:Museum {name: $name})
    RETURN m.city AS city

方式B：通过文物 object_id 查询

    MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
    RETURN m.name AS museum, m.city AS city
    LIMIT 1

返回：博物馆所在城市。

## 10. 同博物馆同朝代文物（多跳扩展示例，intent: multi_hop_same_museum_dynasty）

    MATCH (a:Artifact {object_id: $oid})-[:COLLECTED_BY]->(m:Museum)
    MATCH (a)-[:BELONGS_TO]->(d:Dynasty)
    MATCH (other:Artifact)-[:COLLECTED_BY]->(m)
    WHERE other <> a AND (other)-[:BELONGS_TO]->(d)
    RETURN other.object_id AS object_id, other.title_zh AS title
    LIMIT 5

返回：与当前文物同博物馆且同朝代的其他文物列表。

## 无数据与错误处理

- 所有查询若没有匹配记录，`_run_cypher` 返回 `None`，上层转为 `AnswerStatus.NO_DATA`。
- Cypher 语法错误或连接问题会记录日志并返回 `None`，不会抛出异常影响主流程。