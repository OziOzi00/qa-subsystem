# 知识问答子系统 API 文档

版本：v0.1  
适用阶段：第 14 周子系统运行检查前后端联调、第 16 周系统集成准备

## 1. 接口设计目标

知识问答子系统为 Web 端、掌上博物馆 App 和后台管理子系统提供统一问答能力。

核心目标：

1. 用户使用自然语言提问文物相关问题。
2. 后端根据问题意图和 `objectId` 查询 MySQL 或 Neo4j。
3. 返回自然语言答案、事实依据、来源说明和原始详情页链接。
4. 对暂无数据的问题明确返回“暂无相关数据”，不生成不可靠答案。
5. 支持前端展示候选文物、相关文物推荐和用户反馈入口。

基础地址：

```text
http://127.0.0.1:8000
```

正式部署后由团队统一替换为服务器地址。

## 2. 通用约定

### 2.1 数据格式

请求和响应均使用 JSON。

请求头：

```http
Content-Type: application/json
```

### 2.2 objectId 关联约定

`objectId` 是知识问答子系统与 Web / App、MySQL、Neo4j、问答日志和反馈记录之间的统一文物标识。

解析优先级：

1. 问题中明确识别出的唯一文物名称。
2. 请求体或 URL 传入的 `objectId`，例如 `/qa?objectId=MET_12345`。
3. `sessionId` 或 `conversationId` 对应的当前上下文文物。
4. 如果识别到多个候选文物，返回候选列表让用户选择。
5. 如果无法确定文物对象，提示用户补充文物名称或从文物详情页进入。

说明：请求传入的 `objectId` 优先于旧会话上下文，因为 Web / App 从文物详情页跳转时代表用户当前正在查看的文物。

### 2.3 回答状态

| 状态 | 含义 | 前端建议 |
|---|---|---|
| `answered` | 已成功回答 | 展示答案、来源、反馈按钮 |
| `no_data` | 数据库或图谱中暂无相关数据 | 展示“暂无相关数据”，可展示反馈按钮 |
| `need_clarification` | 需要用户补充文物或选择候选 | 展示提示语和候选列表 |
| `unsupported` | 问题类型暂不支持 | 展示系统能力范围提示 |
| `error` | 系统处理异常 | 展示通用错误提示 |

### 2.4 来源类型

| sourceType | 含义 |
|---|---|
| `mysql` | 来源于公共 MySQL 文物基础表或问答业务表 |
| `neo4j` | 来源于 Neo4j 知识图谱 |
| `llm` | 来源于大语言模型补充描述 |
| `template` | 来源于模板或演示数据 |

前端展示时应区分 `factContent` 和 `supplementalContent`：

- `factContent`：来自 MySQL / Neo4j / 已确认数据源的事实内容。
- `supplementalContent`：模板或可配置大语言模型生成的补充性描述。

当前后端支持轻量 RAG：先从 MySQL / Neo4j 检索事实，再在配置 LLM 时把事实作为上下文生成补充说明。未配置 LLM 或调用失败时，系统会自动回退到模板补充说明，事实性答案仍以 MySQL / Neo4j 检索结果为准。

## 3. 健康检查

### GET `/api/health`

用于检查后端服务是否启动，以及是否配置数据库连接。

响应示例：

```json
{
  "status": "ok",
  "service": "Knowledge QA Subsystem",
  "version": "0.1.0",
  "environment": "development",
  "databaseConfigured": false
}
```

字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `status` | string | 服务状态，正常为 `ok` |
| `service` | string | 服务名称 |
| `version` | string | 后端版本 |
| `environment` | string | 当前运行环境 |
| `databaseConfigured` | boolean | 是否已配置 MySQL 和 Neo4j 连接 |

## 4. 用户提问

### POST `/api/qa/ask`

问答主接口。Web 端、App 端和子系统独立演示页面都通过该接口提问。

### 4.1 请求体

```json
{
  "question": "这件文物收藏在哪里？",
  "objectId": "DEMO_001",
  "sessionId": "session-001",
  "conversationId": "conversation-001",
  "userId": 1001,
  "sourceClient": "web"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---:|---|---|
| `question` | string | 是 | 用户自然语言问题，长度 1-1000 |
| `objectId` | string | 否 | 当前文物唯一标识，Web / App 从详情页进入时建议传入 |
| `sessionId` | string | 否 | 问答会话 ID，用于多轮上下文 |
| `conversationId` | string | 否 | 对话 ID，可与 `sessionId` 二选一 |
| `userId` | number | 否 | 登录用户 ID，未登录可为空 |
| `sourceClient` | string | 否 | 调用来源，如 `web`、`app`、`demo` |

最小请求：

```json
{
  "question": "演示文物的材质是什么？"
}
```

### 4.2 成功回答响应

```json
{
  "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
  "sessionId": "session-001",
  "status": "answered",
  "intent": "artifact_museum",
  "answer": "演示文物 DEMO_001 现藏于克利夫兰艺术博物馆。",
  "factContent": "演示文物 DEMO_001 现藏于克利夫兰艺术博物馆。",
  "supplementalContent": "该回答由系统根据 MySQL 或 Neo4j 中的已确认事实生成；当前未启用大语言模型补充生成，已使用模板兜底。",
  "resolvedObject": {
    "objectId": "DEMO_001",
    "title": "演示文物",
    "resolveSource": "request_object_id",
    "candidates": []
  },
  "sources": [
    {
      "sourceType": "template",
      "sourceName": "QA Demo Dataset",
      "detailUrl": "https://www.clevelandart.org/art/collection/search",
      "factText": "演示数据用于验证知识问答子系统主流程。",
      "confidence": 0.8
    }
  ],
  "relatedArtifacts": [],
  "createdAt": "2026-05-21T12:00:00.000000",
  "needFeedback": true,
  "debug": {
    "intentConfidence": 0.75,
    "matchedKeywords": ["收藏"],
    "retrievalRaw": {
      "dataset": "demo"
    }
  }
}
```

响应字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `qaLogId` | string | 本次问答日志 ID，提交反馈时使用 |
| `sessionId` | string/null | 当前会话 ID |
| `status` | string | 回答状态，见 2.3 |
| `intent` | string/null | 识别出的意图类型 |
| `answer` | string | 用户可直接阅读的答案 |
| `factContent` | string/null | 事实性内容 |
| `supplementalContent` | string/null | 模板或大模型补充描述 |
| `resolvedObject` | object | 本次问题最终关联的文物 |
| `sources` | array | 答案来源列表 |
| `relatedArtifacts` | array | 相关文物推荐结果 |
| `createdAt` | string | 回答生成时间 |
| `needFeedback` | boolean | 是否建议展示反馈按钮 |
| `debug` | object/null | 调试信息，正式部署可关闭或忽略 |

### 4.3 resolvedObject 字段

```json
{
  "objectId": "DEMO_001",
  "title": "演示文物",
  "resolveSource": "question_entity",
  "candidates": [
    {
      "objectId": "DEMO_001",
      "title": "演示文物",
      "matchedName": "演示文物",
      "confidence": 0.95
    }
  ]
}
```

`resolveSource` 取值：

| 值 | 含义 |
|---|---|
| `question_entity` | 从问题文本中识别到唯一文物 |
| `ambiguous_question_entity` | 从问题文本中识别到多个候选文物 |
| `request_object_id` | 使用请求传入的 `objectId` |
| `session_context` | 使用会话上下文中的当前文物 |
| `not_required_for_intent` | 当前问题不需要单个文物对象 |
| `unresolved` | 无法确定文物对象 |

### 4.4 多候选响应

当问题中出现多个可能文物时，系统不会擅自选择，而是返回候选列表。

```json
{
  "status": "need_clarification",
  "intent": "artifact_material",
  "answer": "识别到多个可能的文物对象：演示文物、相关演示文物。请从候选列表中选择一件文物后继续提问。",
  "resolvedObject": {
    "objectId": null,
    "title": null,
    "resolveSource": "ambiguous_question_entity",
    "candidates": [
      {
        "objectId": "DEMO_001",
        "title": "演示文物",
        "matchedName": "演示文物",
        "confidence": 0.95
      },
      {
        "objectId": "DEMO_002",
        "title": "相关演示文物",
        "matchedName": "相关演示文物",
        "confidence": 0.95
      }
    ]
  }
}
```

前端建议：把 `candidates` 渲染为可点击列表。用户选择后，再次调用 `/api/qa/ask`，并把选择的 `objectId` 放入请求体。

### 4.5 暂无数据响应

```json
{
  "status": "no_data",
  "intent": "artifact_material",
  "answer": "暂无相关数据。",
  "factContent": null,
  "supplementalContent": null,
  "sources": []
}
```

前端建议：展示答案文本即可，不要自行补编答案。

### 4.6 相关文物推荐响应

```json
{
  "status": "answered",
  "intent": "related_artifacts",
  "answer": "按同类型和同朝代规则，找到 1 件相关演示文物。",
  "relatedArtifacts": [
    {
      "objectId": "DEMO_002",
      "title": "相关演示文物",
      "reason": "同类型、同朝代演示推荐",
      "imageUrl": null
    }
  ]
}
```

前端建议：展示相关文物卡片，点击后可跳转到文物详情页或重新打开问答页。

### 4.7 支持的意图类型

必做 11 类简单问答：

| intent | 问答类型 | 主要数据源 |
|---|---|---|
| `artifact_museum` | 文物收藏地 | Neo4j + MySQL |
| `artifact_period` | 文物年代 | Neo4j + MySQL |
| `artifact_material` | 文物材质 | MySQL |
| `artifact_type` | 文物类型 | MySQL |
| `artifact_description` | 文物介绍 | MySQL |
| `artifact_artist` | 书画作者 | Neo4j + MySQL |
| `artist_biography` | 作者生平 | MySQL |
| `same_artist_artifacts` | 同一作者作品 | Neo4j |
| `same_dynasty_artifacts` | 同一朝代文物 | Neo4j |
| `artifact_dimensions` | 文物尺寸与规格 | MySQL |
| `related_artifacts` | 相关文物推荐 | Neo4j + MySQL |

选做基础版：

| intent | 问答类型 | 主要数据源 |
|---|---|---|
| `statistics_count` | 统计类问答 | Neo4j / MySQL |
| `statistics_top_museum` | 收藏某类型最多的博物馆 | Neo4j |
| `museum_city` | 多跳关系中的博物馆城市 | Neo4j + MySQL |

## 5. 用户反馈接口

### POST `/api/qa/feedback`

该接口用于记录用户“有帮助 / 不准确”反馈。`inaccurate` 会自动生成审核任务。

请求示例：

```json
{
  "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
  "userId": 1001,
  "feedbackType": "inaccurate",
  "comment": "答案里的收藏博物馆不正确。"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---:|---|---|
| `qaLogId` | string | 是 | `/api/qa/ask` 返回的问答日志 ID |
| `userId` | number | 否 | 登录用户 ID |
| `feedbackType` | string | 是 | `helpful` 或 `inaccurate` |
| `comment` | string | 否 | 用户补充说明 |

响应示例：

```json
{
  "feedbackId": 1,
  "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
  "reviewTaskCreated": true,
  "message": "反馈已记录。"
}
```

说明：

- `helpful` 写入 `qa_feedback`。
- `inaccurate` 写入 `qa_feedback`，并生成 `qa_review_task`。

## 6. 后台管理接口

以下接口用于后台管理组查看问答日志、反馈、失败问题、审核任务和统计结果。

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/admin/qa/logs` | 查询问答日志 |
| GET | `/api/admin/qa/feedback` | 查询用户反馈 |
| GET | `/api/admin/qa/failed-questions` | 查询失败问题 |
| GET | `/api/admin/qa/review-tasks` | 查询审核任务 |
| POST | `/api/admin/qa/review-tasks/{id}/review` | 提交审核结果 |
| GET | `/api/admin/qa/statistics/failure-types` | 统计高频失败问题类型 |
| GET | `/api/admin/qa/statistics/inaccurate-types` | 统计高频不准确问题类型 |

### 6.1 查询参数建议

列表查询接口建议支持：

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | number | 页码，从 1 开始 |
| `pageSize` | number | 每页数量 |
| `status` | string | 状态筛选 |
| `intent` | string | 意图类型筛选 |
| `keyword` | string | 问题或答案关键字 |
| `startTime` | string | 开始时间 |
| `endTime` | string | 结束时间 |

### 6.2 审核任务处理请求

```json
{
  "reviewResult": "approved",
  "reviewComment": "已确认答案存在问题，待补充知识图谱数据。",
  "reviewerId": 2001
}
```

`reviewResult` 建议取值：

| 值 | 含义 |
|---|---|
| `approved` | 确认反馈有效 |
| `rejected` | 反馈无效 |
| `fixed` | 已修正或已补充数据 |

## 7. 前端和其他子系统联调说明

### 7.1 Web 组跳转

Web 端文物详情页可跳转到：

```text
/qa?objectId=MET_12345
```

Vue 问答页面读取 URL 中的 `objectId`，调用 `/api/qa/ask` 时放入请求体。

### 7.2 App 组调用

App 端负责：

1. 语音转文字。
2. 调用 `/api/qa/ask`。
3. 展示 `answer`、`sources` 和 `relatedArtifacts`。
4. 如需语音播报，播报 `answer`。
5. 用户点击反馈按钮时调用 `/api/qa/feedback`。

### 7.3 后台管理组调用

后台管理组原则上通过第 6 节接口访问问答业务数据。若集成时间不足，可只读查询 `qa_` 表，但审核状态修改等写操作建议通过 API 完成。

## 8. 当前演示数据

后端基础框架内置以下演示对象，供前端和接口联调使用：

| objectId | title | 用途 |
|---|---|---|
| `DEMO_001` | 演示文物 | 可回答收藏地、年代、材质、类型、介绍、尺寸、相关文物等 |
| `DEMO_002` | 相关演示文物 | 用于候选选择和相关文物推荐 |

示例请求：

```json
{
  "question": "演示文物收藏在哪里？",
  "objectId": "DEMO_001",
  "sourceClient": "demo"
}
```

## 9. 实现注意事项

1. `qaLogId` 来自 `qa_log` 实际记录，反馈接口依赖该字段。
2. `sources` 中使用过的数据会同步写入 `qa_source_record`。
3. Neo4j 图谱查询结果应保留可追溯的节点、关系和来源。
4. 当前最近 5 轮上下文为基础版，后续可持久化到 `qa_session`。
5. 前端展示时不应混淆事实内容和补充描述。
6. `inaccurate` 反馈必须生成审核任务。
7. 配置 LLM 后，模型只生成 `supplementalContent`，不能作为事实来源编造新事实。
