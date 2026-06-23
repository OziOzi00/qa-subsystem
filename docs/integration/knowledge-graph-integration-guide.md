# 知识问答子系统与知识图谱构建子系统集成说明

| 版本 | 日期 | 适用对象 |
|---|---|---|
| v1.0 | 2026-06-15 | 知识图谱构建子系统、知识问答子系统、系统集成汇报 |

## 1. 集成目标

知识图谱构建子系统负责构建并维护 Neo4j 图数据库，知识问答子系统负责把图谱中的实体关系转化为用户可理解的问答结果。

当前集成关系如下：

```text
知识图谱构建子系统
构建 Artifact / Museum / Dynasty / Artist 等节点及其关系
        ↓
Neo4j 图数据库
保存文物、博物馆、朝代、作者之间的图谱关系
        ↓
知识问答子系统
通过 Cypher 查询图谱事实，并组合 MySQL 数据生成可信回答
        ↓
App / 前端 / 后台
展示答案、来源、推荐文物和问答日志
```

该集成已在子系统单独检查阶段完成基础联通，并在后续问答主流程中持续使用。

## 2. 对接方式

知识问答子系统不直接接收知识图谱子系统的前端请求，而是通过 Neo4j Python Driver 连接图数据库。

后端配置项如下：

```text
NEO4J_URI=bolt://<host>:7687
NEO4J_USER=<username>
NEO4J_PASSWORD=<password>
```

说明：

1. 真实账号和密码只写入本地或部署环境的 `backend/.env`，不得提交到 GitHub。
2. 知识问答子系统启动时会读取上述配置并初始化 Neo4j 连接。
3. 如果未配置 Neo4j 或连接失败，图谱类问题会返回暂无数据或降级结果，不会编造图谱事实。

## 3. 统一标识约定

双方集成的核心字段是 `objectId` / `object_id`。

| 系统位置 | 字段 | 说明 |
|---|---|---|
| 问答接口 | `objectId` | App / 前端调用 `/api/qa/ask` 时传入的文物标识 |
| MySQL 公共表 | `artifacts.object_id` | 公共数据库中的文物唯一标识 |
| Neo4j 图谱 | `Artifact.object_id` | 图谱中 Artifact 节点的文物唯一标识 |
| 问答日志 | `qa_log.object_id` | 本次问答关联的文物标识 |
| 反馈审核 | `qa_feedback` / `qa_review_task` 关联日志 | 通过问答日志追踪原问题和原文物 |

集成要求：

```text
Neo4j 中 Artifact.object_id 必须与公共 MySQL 中 artifacts.object_id 保持一致。
```

只有这样，问答系统才能在同一次回答中同时使用：

```text
Neo4j 图谱关系
+ MySQL 文物详情
+ 问答日志和反馈记录
```

## 4. 当前使用的图谱节点与关系

当前知识问答子系统主要依赖以下图谱结构：

| 节点 / 关系 | 用途 |
|---|---|
| `Artifact` | 文物节点，必须包含 `object_id`，建议包含中文标题、类型等基础属性 |
| `Museum` | 博物馆节点，用于收藏地、馆藏统计和城市查询 |
| `Dynasty` | 朝代节点，用于文物年代、同朝代文物、朝代代表文物查询 |
| `Artist` | 作者节点，用于书画作者和同作者作品查询 |
| `(:Artifact)-[:COLLECTED_BY]->(:Museum)` | 文物收藏博物馆 |
| `(:Artifact)-[:BELONGS_TO]->(:Dynasty)` | 文物所属朝代 |
| `(:Artifact)-[:CREATED_BY]->(:Artist)` | 文物作者 |

如后续知识图谱子系统扩展人物、地点、主题、工艺等节点，问答系统可以在现有 `KnowledgeRetriever` 中继续扩展 Cypher 查询模板。

## 5. 已集成的图谱问答能力

当前知识问答子系统已经通过 Neo4j 支撑以下功能：

| 问答能力 | 示例问题 | 图谱作用 |
|---|---|---|
| 文物收藏地 | 这件文物收藏在哪里？ | 根据 `objectId` 查询 `Artifact -> Museum` |
| 文物年代 | 这件文物属于哪个朝代？ | 根据 `objectId` 查询 `Artifact -> Dynasty` |
| 书画作者 | 这件文物的作者是谁？ | 根据 `objectId` 查询 `Artifact -> Artist` |
| 同一作者作品 | 同一作者还有哪些作品？ | 先查作者，再反查同作者文物 |
| 同一朝代文物 | 清朝有哪些代表性文物？ | 根据朝代实体或当前文物朝代反查文物 |
| 相关文物推荐 | 推荐相关文物 | 通过同作者、同朝代等关系推荐 |
| 统计类问答 | 某博物馆收藏多少件中国文物？ | 根据博物馆实体统计文物数量 |
| 多跳问答 | 某博物馆位于哪个城市？ | 查询博物馆属性或通过文物关联到博物馆 |
| 类型统计 | 收藏某类型文物最多的博物馆是哪个？ | 统计 `Artifact.type -> Museum` 关系 |

这些功能已经接入 `/api/qa/ask` 主流程。用户不需要直接了解 Cypher 查询，只需在 App 或前端提出自然语言问题。

## 6. 问答主流程中的图谱调用位置

图谱集成位于知识问答后端的知识检索阶段：

```text
POST /api/qa/ask
        ↓
意图识别 IntentRecognizer
        ↓
文物对象解析 ObjectResolver
        ↓
KnowledgeRetriever
        ├─ 查询 Neo4j：收藏地、年代、作者、推荐、统计、多跳
        └─ 查询 MySQL：材质、类型、介绍、尺寸、详情链接等
        ↓
AnswerGenerator / LLM 补充说明
        ↓
写入 qa_log / qa_source_record
        ↓
返回 answer、factContent、supplementalContent、sources
```

其中 Neo4j 返回的是事实依据，最终会进入：

| 响应字段 | 含义 |
|---|---|
| `factContent` | 来自 Neo4j / MySQL 的事实内容 |
| `sources` | 数据来源，Neo4j 结果会标记为 `sourceType=neo4j` |
| `relatedArtifacts` | 同作者、同朝代或相关文物推荐 |
| `supplementalContent` | 模板或 LLM 根据事实生成的补充说明，不替代图谱事实 |

## 7. 答案来源与可信度处理

为避免大语言模型编造图谱中不存在的事实，系统采用如下规则：

1. 收藏地、年代、作者、推荐和统计等事实必须优先来自 Neo4j 或 MySQL。
2. Neo4j 查询结果会写入 `sources`，前端可以展示“知识图谱”来源。
3. 对于 Neo4j 查询到的文物，系统会尽量回查 MySQL 的原始详情页链接，用于补充 `detailUrl`。
4. 如果 Neo4j 无结果，系统返回“暂无相关数据”或降级到 MySQL 可用字段，不由 LLM 虚构。
5. LLM 只用于 `supplementalContent`，负责基于事实进行补充说明。

## 8. 对知识图谱子系统的数据要求

为了保证问答效果，知识图谱子系统需要尽量满足以下数据要求：

1. `Artifact.object_id` 与 MySQL `artifacts.object_id` 一致。
2. 常用节点名称尽量稳定，例如博物馆名、朝代名、作者名。
3. `Museum` 节点建议包含城市字段，便于回答“某博物馆位于哪个城市”。
4. `Artifact` 节点建议保留类型字段，便于支持“收藏某类型文物最多的博物馆”。
5. 关系方向保持一致：

```text
(:Artifact)-[:COLLECTED_BY]->(:Museum)
(:Artifact)-[:BELONGS_TO]->(:Dynasty)
(:Artifact)-[:CREATED_BY]->(:Artist)
```

如果图谱 schema 后续调整，需要同步通知知识问答子系统更新 Cypher 模板。

## 9. 当前集成边界

当前已经完成：

```text
Neo4j 连接
Cypher 查询模板
图谱关系问答
统计类问答基础版
相关文物推荐基础版
Neo4j 来源标注
Neo4j + MySQL 详情链接补充
```

当前暂未作为核心实现：

```text
复杂历史人物路径查询
唐宋瓷器风格比较等开放比较类问答
基于向量检索的图谱语义搜索
图谱 schema 自动适配
```

上述内容属于后续增强方向，不影响当前系统集成检查的核心链路。

## 10. 集成检查建议展示

系统集成汇报时建议展示以下流程：

```text
知识图谱子系统提供 Neo4j 图谱
        ↓
知识问答子系统读取 Artifact / Museum / Dynasty / Artist 关系
        ↓
App 端传入 question + objectId
        ↓
问答后端查询 Neo4j 并生成带来源回答
        ↓
后台管理查看问答日志和来源记录
```

建议演示问题：

```text
这件文物收藏在哪里？
这件文物属于哪个朝代？
这件文物的作者是谁？
同一作者还有哪些作品？
清朝有哪些代表性文物？
The Metropolitan Museum of Art 收藏了多少件中国文物？
收藏容器最多的博物馆是哪个？
```

汇报说明口径：

```text
知识图谱构建子系统负责提供结构化关系数据；
知识问答子系统负责把图谱关系转化为自然语言回答；
后台管理子系统负责查看问答日志、反馈和审核任务；
App 子系统负责作为用户侧问答入口。
```
