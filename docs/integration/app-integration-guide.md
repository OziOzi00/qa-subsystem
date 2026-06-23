# 知识问答子系统 App 端对接说明

| 版本 | 日期 | 适用对象 |
|---|---|---|
| v1.0 | 2026-06-09 | 掌上博物馆 App 子系统 |

## 1. 对接方式


App 端主要使用两个接口：

```text
POST /api/qa/ask
POST /api/qa/feedback
```

本地联调基础地址示例：

```text
http://127.0.0.1:8000
```

正式集成时，接口基础地址以总项目后端服务或统一网关配置为准。

## 2. 提问接口

### 2.1 接口地址

```text
POST /api/qa/ask
```

### 2.2 推荐请求体

```json
{
  "question": "这件文物的材质是什么？",
  "objectId": "当前文物objectId",
  "sessionId": "App端会话ID",
  "conversationId": "App对话ID，可选",
  "userId": 1001,
  "sourceClient": "app"
}
```

### 2.3 字段说明

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `question` | 必填 | 用户输入的问题；如果 App 使用语音输入，语音识别后的文本也放在该字段 |
| `objectId` | 推荐传 | 当前文物的统一标识；从文物详情页进入问答时必须尽量传入 |
| `sessionId` | 推荐传 | App 端生成并维护的会话 ID，用于多轮上下文 |
| `conversationId` | 可选 | 如果 App 自己已有对话 ID，可以传入；没有可不传 |
| `userId` | 可选 | 登录用户 ID；如果 App 能拿到公共 `users.id`，建议传入 |
| `sourceClient` | 推荐传 | 固定传 `"app"`，方便后台统计来源 |

### 2.4 接入要求

1. `question` 必填。
2. 从 App 文物详情页进入问答时，请传当前文物的 `objectId`。
3. `objectId` 需要和公共 MySQL 的 `artifacts.object_id`、Neo4j 的 `Artifact.object_id` 保持一致。
4. 多轮追问时，同一轮对话保持同一个 `sessionId`。
5. 用户点击“新会话”、切换文物或重新开始问答时，可以生成新的 `sessionId`。
6. `sourceClient` 固定传 `"app"`。
7. `userId` 可选；登录后能拿到公共 `users.id` 就传，未登录可以不传。

## 3. 提问响应字段

`/api/qa/ask` 会返回统一响应体，App 端重点使用以下字段：

| 字段 | App 端用途 |
|---|---|
| `qaLogId` | 本次问答日志 ID，提交反馈时必须使用 |
| `status` | 回答状态，用于决定页面展示逻辑 |
| `intent` | 系统识别出的问题类型，可用于调试或埋点 |
| `answer` | 主回答，建议用于页面展示和语音播报 |
| `factContent` | 事实内容，来自 MySQL 或 Neo4j |
| `supplementalContent` | 补充说明，来自模板或大语言模型 |
| `resolvedObject` | 当前解析出的文物对象 |
| `resolvedObject.candidates` | 多候选文物列表 |
| `sources` | 答案来源和原始详情页链接 |
| `relatedArtifacts` | 相关文物推荐 |
| `needFeedback` | 是否展示反馈按钮 |

### 3.1 响应示例

```json
{
  "qaLogId": "7c5a7a82-2ac0-4bd3-8a01-8d55e8e6d3b0",
  "sessionId": "app-session-001",
  "status": "answered",
  "intent": "artifact_material",
  "answer": "这件文物的材质为瓷。",
  "factContent": "这件文物的材质为瓷。",
  "supplementalContent": "该回答由系统根据 MySQL 或 Neo4j 中的已确认事实生成。",
  "resolvedObject": {
    "objectId": "1",
    "title": "罐子",
    "resolveSource": "request_object_id",
    "candidates": []
  },
  "sources": [
    {
      "sourceType": "mysql",
      "sourceName": "公共 MySQL 文物基础表",
      "detailUrl": "https://example.com/detail/1",
      "factText": "材质：瓷",
      "confidence": 0.95
    }
  ],
  "relatedArtifacts": [],
  "needFeedback": true
}
```

## 4. status 处理规则

App 端需要根据 `status` 控制页面展示。

| status | 含义 | App 端处理建议 |
|---|---|---|
| `answered` | 已成功回答 | 展示答案、事实内容、补充说明、来源、推荐文物和反馈按钮 |
| `no_data` | 知识库暂无相关数据 | 展示暂无相关数据，不要自行补造答案 |
| `need_clarification` | 需要用户补充信息或选择候选文物 | 展示 `resolvedObject.candidates`，让用户选择 |
| `unsupported` | 问题类型暂不支持 | 展示系统支持范围提示 |
| `error` | 系统处理异常 | 展示错误提示，可让用户稍后重试 |

特别说明：

```text
当 status=need_clarification 时，请展示 candidates 让用户选择文物，不要默认取第一条候选。
```

## 5. 多候选文物处理

当用户输入的文物名称对应多个文物时，例如：

```text
介绍一下花瓶
```

问答接口会返回：

```text
status = need_clarification
resolvedObject.candidates = 候选文物列表
```

候选文物字段通常包括：

| 字段 | 说明 |
|---|---|
| `objectId` | 候选文物统一标识 |
| `title` | 候选文物名称 |
| `imageUrl` | 文物图片 |
| `museumName` | 馆藏博物馆 |
| `dynastyName` | 朝代 |
| `artifactType` | 文物类型 |
| `material` | 材质 |
| `dimensions` | 尺寸 |
| `detailUrl` | 原始详情页链接 |

App 端处理流程：

1. 展示候选文物卡片。
2. 用户选择其中一件文物。
3. App 将选中的 `objectId` 带入下一次 `/api/qa/ask` 请求。

示例：

```json
{
  "question": "介绍一下花瓶",
  "objectId": "5",
  "sessionId": "app-session-001",
  "sourceClient": "app"
}
```

## 6. 多轮对话

如果 App 要支持如下连续追问：

```text
这件文物的材质是什么？
它的尺寸是多少？
它收藏在哪里？
```

请在同一轮问答中持续传同一个 `sessionId`。后端会根据 `sessionId` 保存最近 5 轮上下文，并理解“它”“该文物”等指代。

建议规则：

1. 用户打开一次问答页面时，App 生成一个 `sessionId`。
2. 同一轮对话中持续使用该 `sessionId`。
3. 用户点击“新会话”时生成新的 `sessionId`。
4. 用户从新的文物详情页进入问答时，建议传新的 `objectId`，也可以生成新的 `sessionId`。

## 7. 语音输入与语音播报

语音输入和语音播报由 App 端负责。

建议分工：

| 能力 | 负责方 |
|---|---|
| 语音转文字 | App 端 |
| 文本问答理解与回答生成 | 知识问答子系统 |
| 答案语音播报 | App 端 |

接入建议：

1. App 将语音识别结果作为 `question` 发送给 `/api/qa/ask`。
2. 问答子系统返回 `answer`、`factContent`、`supplementalContent` 和 `sources`。
3. App 语音播报建议使用 `answer` 字段。
4. `factContent`、`supplementalContent` 和 `sources` 建议在页面中展示。

## 8. 反馈接口

### 8.1 接口地址

```text
POST /api/qa/feedback
```

### 8.2 请求体示例

用户认为回答有帮助：

```json
{
  "qaLogId": "上一条回答返回的qaLogId",
  "feedbackType": "helpful",
  "userId": 1001,
  "sourceClient": "app"
}
```

用户认为回答不准确：

```json
{
  "qaLogId": "上一条回答返回的qaLogId",
  "feedbackType": "inaccurate",
  "comment": "用户认为答案不准确",
  "userId": 1001,
  "sourceClient": "app"
}
```

### 8.3 字段说明

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `qaLogId` | 必填 | `/api/qa/ask` 上一条回答返回的日志 ID |
| `feedbackType` | 必填 | 只能是 `helpful` 或 `inaccurate` |
| `comment` | 可选 | 用户补充说明 |
| `userId` | 可选 | 登录用户 ID |
| `sourceClient` | 推荐传 | 固定传 `"app"` |

说明：

```text
如果 feedbackType=inaccurate，问答后端会自动生成审核任务，后续由后台管理系统处理。
```

## 9. 推荐 App 联调用例

### 9.1 从文物详情页进入

```json
{
  "question": "这件文物的材质是什么？",
  "objectId": "1",
  "sessionId": "app-session-001",
  "sourceClient": "app"
}
```

预期：返回 `status=answered`，并包含 `answer`、`factContent` 和 `sources`。

### 9.2 多轮追问

第一次：

```json
{
  "question": "这件文物的材质是什么？",
  "objectId": "1",
  "sessionId": "app-session-002",
  "sourceClient": "app"
}
```

第二次：

```json
{
  "question": "它的尺寸是多少？",
  "sessionId": "app-session-002",
  "sourceClient": "app"
}
```

预期：第二次问题中的“它”指代第一次的文物。

### 9.3 文物名称自动识别

```json
{
  "question": "介绍一下犀牛角杯",
  "sessionId": "app-session-003",
  "sourceClient": "app"
}
```

预期：系统自动识别唯一文物并回答。

### 9.4 多候选文物

```json
{
  "question": "介绍一下花瓶",
  "sessionId": "app-session-004",
  "sourceClient": "app"
}
```

预期：返回 `status=need_clarification` 和 `resolvedObject.candidates`。

### 9.5 反馈提交

```json
{
  "qaLogId": "上一条回答返回的qaLogId",
  "feedbackType": "helpful",
  "sourceClient": "app"
}
```

预期：反馈记录成功。

## 10. 需要 App 组确认

为了正式集成，请 App 组确认以下三点：

1. App 文物详情页需要能拿到与公共 MySQL / Neo4j 一致的 `objectId`。
2. App 最好在同一轮问答中维护稳定的 `sessionId`。
3. 目前暂时默认App 调用问答接口是直连问答服务。

## 11. 联系与变更说明

如果 App 端需要新增字段、调整展示结构或扩展语音播报内容，请先与知识问答子系统确认接口契约。集成阶段原则上保持 `/api/qa/ask` 和 `/api/qa/feedback` 字段稳定，避免影响 Web、App 和后台管理同时对接。
