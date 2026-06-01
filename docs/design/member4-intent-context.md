# 成员4：意图识别、多轮上下文与答案生成说明

本文档说明当前主线中成员4相关模块的交付范围，覆盖 11 类简单问答、复杂问答基础版实体抽取、最近 5 轮上下文记录、回答模板兜底和轻量 RAG 补充生成。

## 1. 意图编码

当前 `IntentRecognizer` 支持以下 11 类简单问答：

| 意图编码 | 含义 | 是否需要 object_id |
|---|---|---|
| `artifact_museum` | 文物收藏地 | 是 |
| `artifact_period` | 文物年代 / 朝代 | 是 |
| `artifact_material` | 文物材质 | 是 |
| `artifact_type` | 文物类型 | 是 |
| `artifact_description` | 文物介绍 | 是 |
| `artifact_artist` | 书画作者 | 是 |
| `artist_biography` | 作者生平 | 是 |
| `same_artist_artifacts` | 同一作者作品 | 是 |
| `same_dynasty_artifacts` | 同一朝代文物 | 是 |
| `artifact_dimensions` | 文物尺寸与规格 | 是 |
| `related_artifacts` | 相关文物推荐 | 是 |

同时支持复杂问答基础版：

| 意图编码 | 含义 | 实体字段 |
|---|---|---|
| `statistics_count` | 某博物馆收藏多少件文物 | `entities["museum"]` |
| `statistics_top_museum` | 收藏某类型文物最多的博物馆 | `entities["artifact_type"]` |
| `museum_city` | 博物馆所在城市 / 文物所在博物馆城市 | `entities["museum"]` 或当前 `object_id` |
| `same_dynasty_artifacts` | 某朝代代表性文物 | `entities["dynasty"]` 或当前 `object_id` |

## 2. 实体抽取约定

`IntentResult.entities` 统一使用 `dict[str, Any]`。当前约定键名：

- `museum`：博物馆名称，例如 `大英博物馆`。
- `artifact_type`：文物类型，例如 `瓷器`。
- `dynasty`：朝代或时期，例如 `明朝`。

统计类问题不强制从文物出发，可直接通过实体进入 Neo4j 查询。涉及“该文物 / 这件文物 / 它”的问题仍需要当前上下文中的 `object_id`。

## 3. 多轮上下文规则

主流程仍遵循组长确定的 object_id 优先级：

1. 问题中明确识别到唯一文物名称；
2. 请求参数 / URL 中传入的 `objectId`；
3. 会话上下文中的当前 `object_id`；
4. 多候选时返回候选列表；
5. 无法确定时提示用户补充文物名称或选择文物。

`SessionContextStore` 额外记录最近 5 轮问答摘要，并在接口 `debug.recentContext` 中返回，便于联调和演示。

## 4. 回答生成

`AnswerGenerator` 根据检索结果生成自然语言回答：

- `answered`：优先使用检索事实中的第一条作为回答，并把全部事实放入 `factContent`。
- `no_data`：按意图返回明确的“暂无某类数据”兜底话术。
- `need_clarification`：提示补充文物名称或从候选文物中选择。
- `unsupported`：提示当前问题暂未匹配到已支持类型。

事实内容与补充说明分离：

- `factContent` 保存 MySQL / Neo4j 检索得到的事实。
- `supplementalContent` 保存模板兜底说明或 LLM 基于检索事实生成的补充描述。
- LLM 只允许基于 facts 进行语言组织，不作为事实来源编造新内容。
- 未配置 LLM 或调用失败时，系统自动返回模板兜底补充说明。
