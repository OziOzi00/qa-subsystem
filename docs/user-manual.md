# 知识问答子系统 — 用户手册（成员 6 模块）

| 版本 | 日期 | 编制人 |
|---|---|---|
| v0.1 | 2026-05-25 | 成员 6 |

---

## 1. 概述

本文档介绍知识问答子系统中成员 6 负责的模块：**用户反馈机制**、**审核任务管理**和**后台数据查询**的接口使用说明。

### 1.1 功能清单

| 功能 | 接口 | 说明 |
|---|---|---|
| 提交反馈 | `POST /api/qa/feedback` | 用户提交"有帮助/不准确"反馈 |
| 查询日志 | `GET /api/admin/qa/logs` | 查看问答日志列表 |
| 查询反馈 | `GET /api/admin/qa/feedback` | 查看用户反馈记录 |
| 查询失败问题 | `GET /api/admin/qa/failed-questions` | 查看系统无法回答的问题 |
| 查询审核任务 | `GET /api/admin/qa/review-tasks` | 查看待审核任务 |
| 处理审核 | `POST /api/admin/qa/review-tasks/{id}/review` | 对审核任务做出裁决 |
| 失败类型统计 | `GET /api/admin/qa/statistics/failure-types` | 查看高频失败问题类型分布 |
| 不准确类型统计 | `GET /api/admin/qa/statistics/inaccurate-types` | 查看高频不准确问题类型分布 |

### 1.2 基础地址

```text
http://127.0.0.1:8000/api
```

正式部署后由团队统一替换为服务器地址。

---

## 2. 用户反馈接口

### 2.1 提交"有帮助"反馈

当用户认为回答准确有用时调用。

**请求：**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/qa/feedback `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"qaLogId":"5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a","feedbackType":"helpful","sourceClient":"web"}'
```

**响应示例：**

```json
{
  "feedbackId": 1,
  "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
  "reviewTaskCreated": false,
  "message": "反馈已记录。"
}
```

### 2.2 提交"不准确"反馈

当用户认为回答不准确时调用。系统会自动生成一条审核任务。

**请求：**

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/qa/feedback `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"qaLogId":"5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a","userId":1001,"feedbackType":"inaccurate","comment":"收藏博物馆名称有误。","sourceClient":"web"}'
```

**响应示例：**

```json
{
  "feedbackId": 2,
  "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
  "reviewTaskCreated": true,
  "message": "反馈已记录。"
}
```

### 2.3 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `qaLogId` | string | 是 | 问答日志 UUID，来自 `/api/qa/ask` 响应的 `qaLogId` |
| `userId` | number | 否 | 登录用户 ID（不传则匿名） |
| `feedbackType` | string | 是 | `helpful`（有帮助）或 `inaccurate`（不准确） |
| `comment` | string | 否 | 用户补充说明 |
| `sourceClient` | string | 否 | 调用来源：`web` / `app` / `demo` |

### 2.4 注意事项

- `inaccurate` 反馈会自动在 `qa_review_task` 表生成一条 `pending` 状态的审核任务
- `userId` 如果传入，必须在 `users` 表中存在（否则违反外键约束）
- 未登录用户可以不传 `userId`，系统会记录为 NULL

---

## 3. 后台管理接口

### 3.1 通用查询参数

所有列表查询接口支持以下通用参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `page` | number | 1 | 页码，从 1 开始 |
| `pageSize` | number | 20 | 每页数量，最大 100 |
| `status` | string | — | 状态筛选 |
| `keyword` | string | — | 关键词搜索 |
| `startTime` | string | — | 开始时间（ISO 格式） |
| `endTime` | string | — | 结束时间（ISO 格式） |

### 3.2 通用响应格式

```json
{
  "items": [ ... ],
  "total": 50,
  "page": 1,
  "pageSize": 20,
  "totalPages": 3
}
```

### 3.3 查询问答日志

```powershell
# 基本分页
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/logs?page=1&pageSize=20"

# 按意图筛选
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/logs?intent=artifact_museum"

# 按关键词搜索
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/logs?keyword=瓷器"

# 按时间范围筛选
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/logs?startTime=2026-01-01&endTime=2026-05-25"
```

### 3.4 查询用户反馈

```powershell
# 全部反馈
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/feedback?page=1&pageSize=20"

# 只看不准确反馈
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/feedback?feedbackType=inaccurate"
```

### 3.5 查询失败问题

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/failed-questions?page=1&pageSize=20"
```

### 3.6 查询审核任务

```powershell
# 全部审核任务
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/review-tasks?page=1&pageSize=20"

# 只看待处理任务
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/review-tasks?taskStatus=pending"
```

### 3.7 处理审核任务

**请求：**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/review-tasks/1/review" `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"reviewResult":"approved","reviewComment":"已确认，待补充数据。","reviewerId":2001}'
```

**`reviewResult` 取值：**

| 值 | 含义 |
|---|---|
| `approved` | 确认反馈有效，回答确实有问题 |
| `rejected` | 反馈无效，回答正确 |
| `fixed` | 已修正数据，问题已解决 |

### 3.8 注意事项

- `reviewerId` 必须在 `admin_users` 表中存在
- 审核后任务状态从 `pending` 变为 `done`
- 审核结果不可撤回（如需修改需在数据库中手动处理）

---

## 4. 统计接口

### 4.1 高频失败问题类型统计

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/statistics/failure-types"
```

响应示例：

```json
[
  { "failureType": "no_data_found", "count": 42 },
  { "failureType": "intent_not_recognized", "count": 15 }
]
```

按出现次数降序排列。

### 4.2 高频不准确问题类型统计

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/admin/qa/statistics/inaccurate-types"
```

响应示例：

```json
[
  { "intent": "artifact_museum", "count": 8 },
  { "intent": "artifact_period", "count": 3 }
]
```

按出现次数降序排列。

---

## 5. 错误处理

| HTTP 状态码 | 含义 | 常见原因 |
|---|---|---|
| 200 | 成功 | |
| 400 | 请求体解析错误 | JSON 格式错误 |
| 404 | 资源不存在 | 审核任务 ID 不正确 |
| 422 | 请求体验证失败 | 缺少必填字段、字段类型错误 |
| 500 | 服务器内部错误 | 数据库连接异常等 |

---

## 6. 常见问题

**Q: 提交反馈时返回 500 错误怎么办？**

A: 检查是否违反了数据库外键约束。`qaLogId` 必须是有效的 UUID，`userId` 如果在 `users` 表中不存在则传入 NULL。

**Q: 为什么我提交了 inaccurate 反馈，但审核任务列表是空的？**

A: 审核任务列表需要按 `taskStatus` 参数筛选，默认只返回全部状态。如果是刚提交的反馈，任务状态为 `pending`，可用 `?taskStatus=pending` 查询。

**Q: 统计接口返回空数组怎么办？**

A: 统计数据来自业务数据的积累，首次部署时无数据属于正常现象。待系统运行一段时间后数据会自动积累。
