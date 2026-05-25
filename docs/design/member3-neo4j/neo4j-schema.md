# Neo4j 图谱结构分析（基于知识图谱组导入脚本）

## 节点标签（Labels）及其属性

### Artifact（文物）
- object_id（字符串，唯一标识，与 MySQL artifacts.object_id 完全一致）
- title_zh（字符串，中文名称）
- title_en（字符串，英文名称）
- material（字符串，材质）
- type（字符串，类型，如瓷器、书画等）
- image_url（字符串，图片链接）

唯一约束：`CONSTRAINT artifact_id_unique FOR (a:Artifact) REQUIRE a.object_id IS UNIQUE`

### Museum（博物馆）
- id（整数，唯一标识）
- name（字符串，博物馆名称，如“大英博物馆”）
- city（字符串，所在城市，如“伦敦”）

唯一约束：`CONSTRAINT museum_id_unique FOR (m:Museum) REQUIRE m.id IS UNIQUE`

### Dynasty（朝代）
- id（整数，唯一标识）
- name_zh（字符串，朝代中文名，如“唐代”）

唯一约束：`CONSTRAINT dynasty_id_unique FOR (d:Dynasty) REQUIRE d.id IS UNIQUE`

### Artist（艺术家）
- id（整数，唯一标识）
- name_zh（字符串，艺术家中文名）

唯一约束：`CONSTRAINT artist_id_unique FOR (art:Artist) REQUIRE art.id IS UNIQUE`

## 关系类型（Relationship Types）

- `(:Artifact)-[:COLLECTED_BY]->(:Museum)`  
  表示文物被某博物馆收藏。导入时通过 artifacts.csv 中的 museum_id 和 museum_name 建立。

- `(:Artifact)-[:BELONGS_TO]->(:Dynasty)`  
  表示文物属于某个朝代。导入时通过 artifacts.csv 中的 dynasty_id 和 dynasty_name 建立，仅当 dynasty_id 非空时创建。

- `(:Artifact)-[:CREATED_BY]->(:Artist)`  
  表示文物由某艺术家创作（主要适用于书画类）。导入时通过单独的 artifact_artist_relation.csv 建立，可附加 role 属性（如“绘制”、“题跋”）。

## 图谱与 MySQL 的关联

- 同一件文物在两个数据源中通过 `object_id` 对齐。
- MySQL 存储文物的详细描述信息（介绍、尺寸、详情页链接等），Neo4j 存储实体间的关系（收藏、年代、作者）。
- 问答时，若需要文物的材质、类型、尺寸等，由成员2查询 MySQL；若需要博物馆、朝代、作者及关系，由成员3查询 Neo4j。

## 查询注意事项

- 所有查询必须使用 `object_id` 作为文物入口（统计和多跳问答除外，可直接使用博物馆名或类型名）。
- 无数据时返回空或 None，不允许编造答案。
- 返回的事实内容放入 `factContent`，补充描述放入 `supplementalContent`。