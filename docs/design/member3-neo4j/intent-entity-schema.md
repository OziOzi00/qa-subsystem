# 给成员4：意图识别模块与 Neo4j 查询模块的协作说明

## 一、为什么要增加 `IntentResult.entities` 字段？

当前系统中，所有基于文物的查询（收藏地、年代、作者等）都通过 `object_id` 完成，这没问题。但是**统计类问答**（例如“大英博物馆收藏了多少件文物？”）和**多跳关系问答**（例如“这件文物的博物馆在哪个城市？”）**不涉及具体文物**，而是需要**博物馆名称、文物类型、朝代名称**等实体。

- `object_id` 字段只能存放文物标识，不能用来传博物馆名。
- 你的意图识别模块负责从用户问题中抽取关键信息，而这些实体正好是提取的内容。

因此我们在 `IntentResult` 中增加了 `entities` 字典字段，用于传递这些实体。

> 这个字段我已在 `backend/app/models/qa_pipeline.py` 中修改，你可以直接使用（可以看一下我修改文档中的第二点）。

## 二、你需要做什么？

### 2.1 识别需要实体的意图

以下意图需要你从问题中抽取实体，并填入 `IntentResult.entities`：

| 意图 (`intent`) | 需要抽取的实体 | 实体键名（固定） | 示例问题 | 示例实体值 |
|----------------|----------------|------------------|----------|-------------|
| `statistics_count` | 博物馆名称 | `"museum"` | “大英博物馆收藏了多少件文物？” | `"大英博物馆"` |
| `statistics_top_museum` | 文物类型 | `"artifact_type"` | “收藏瓷器最多的博物馆是哪个？” | `"瓷器"` |
| `museum_city` | 博物馆名称 | `"museum"` | “这件文物的博物馆在哪个城市？”（如果问题中没有明确博物馆名，可由上下文得到） | `"大英博物馆"` |

**注意**：

- 如果问题中直接给出了博物馆名（如“大英博物馆”），直接抽取。
- 如果问题中是“这件文物的博物馆”，你不需要抽取（因为上下文中的 `object_id` 会提供），但也可以留空，我的代码会通过文物ID查询博物馆城市。

### 2.2 如何填充 `entities`

在识别出上述意图后，在创建 `IntentResult` 对象时，增加 `entities` 参数。

**示例1：统计博物馆文物数量**

```python
intent_result = IntentResult(
    intent="statistics_count",
    confidence=0.92,
    matched_keywords=["收藏", "多少"],
    needs_object=False,                     # 不需要文物对象
    entities={"museum": "大英博物馆"}       # 键名必须为 "museum"
)
```

**示例2：统计某类型最多的博物馆**

```python
intent_result = IntentResult(
    intent="statistics_top_museum",
    confidence=0.88,
    matched_keywords=["最多", "博物馆"],
    needs_object=False,
    entities={"artifact_type": "瓷器"}      # 键名必须为 "artifact_type"
)
```

**示例3：博物馆城市（通过实体直接查询）**

```python
intent_result = IntentResult(
    intent="museum_city",
    confidence=0.85,
    matched_keywords=["哪个城市", "位于"],
    needs_object=False,                     # 可以不需要文物对象
    entities={"museum": "大英博物馆"}
)
```

### 2.3 如果无法抽取到实体怎么办？

如果用户问的是“收藏瓷器最多的博物馆是哪个？”但你没有抽取出 `"瓷器"`，那么 `entities` 会是空字典。我的代码将直接返回无数据（NO_DATA），因此请尽量提高实体抽取准确率。

## 三、你需要修改哪些文件？

- **你只需要修改你的意图识别模块**（通常在 `backend/app/services/intent_recognizer.py` 或类似位置）。
- **不需要修改我的 `knowledge_retriever.py`**，我已经适配了 `entities` 字段。
- 如果组长没有合并模型文件，请提醒他合并 `qa_pipeline.py`（已经加好了 `entities` 字段）。

## 四、测试方法

当你完成实体抽取后，可以配合我的 Neo4j 查询模块进行测试（前提是 Neo4j 中已有真实数据）。例如：

**请求**（可以用 Swagger 或 curl）：
```json
{
  "question": "大英博物馆收藏了多少件文物？"
}
```

**预期我的代码行为**：
- 你的意图识别返回 `IntentResult(intent="statistics_count", entities={"museum": "大英博物馆"})`
- 我的 `_query_statistics_count` 会读取 `entities["museum"]`，执行 Cypher 统计。
- 返回类似 `"博物馆 大英博物馆 收藏了 123 件文物"` 的事实。

如果 Neo4j 中还没有数据，你会得到 `status: "no_data"`，这是正常的。

## 五、常见问题

**Q：`entities` 字典里可以放多个实体吗？**  
A：可以，例如某些复杂问题需要朝代+类型。但目前我们只约定上述几个键名。如果未来有新需求，可以扩展。

**Q：如果问题中既有文物名又有博物馆名怎么办？**  
A：对于统计类意图，通常不需要文物名。你可以正常抽取博物馆名，同时 `needs_object=False`，我的代码就不会去管 `object_id`。

**Q：我是否需要处理多轮对话中的实体继承？**  
A：暂时不需要。统计和多跳问题通常独立成问，不会依赖历史上下文。如果未来需要，再协商。

**Q：如果用户问的是“这个博物馆收藏了多少件文物？”但没有具体名称？**  
A：这需要结合会话上下文中的博物馆信息，或者提示用户提供博物馆名。当前版本可以先作为 `no_data` 处理。

## 六、总结

- **你需要做**：针对 `statistics_count`, `statistics_top_museum`, `museum_city` 这三个意图，从问题中抽取对应的博物馆名或类型名，填入 `IntentResult.entities`。
- **你需要保证**：键名使用 `"museum"`, `"artifact_type"`等（详见上表）。
- **你不需要**：修改我的代码，也无需关心 Neo4j 查询细节。

