# 知识问答子系统后台管理对接说明

| 版本 | 日期 | 适用对象 |
|---|---|---|
| v1.0 | 2026-06-09 | 后台管理子系统 |

## 1. 对接目标

调用知识问答子系统提供的后台接口，完成问答业务数据的查看、审核和统计展示。

当前对接关系如下：

```text
知识问答子系统负责：
记录问答日志、用户反馈、失败问题和审核任务，并提供后台查询 / 处理接口。

后台管理子系统负责：
制作后台页面，展示问答日志、反馈、失败问题、审核任务和统计结果，并提供管理员操作入口。
```



## 2. 已提供接口

后台管理子系统可调用以下接口：

```text
GET /api/admin/qa/logs
GET /api/admin/qa/feedback
GET /api/admin/qa/failed-questions
GET /api/admin/qa/review-tasks
POST /api/admin/qa/review-tasks/{id}/review
GET /api/admin/qa/statistics/failure-types
GET /api/admin/qa/statistics/inaccurate-types
```

本地联调基础地址示例：

```text
http://127.0.0.1:8000
```

正式集成时，接口基础地址以总项目后端服务、统一网关或问答后端部署地址为准。

## 3. 接口说明

### 3.1 查询问答日志

```text
GET /api/admin/qa/logs
```

常用参数：

| 参数 | 说明 |
|---|---|
| `page` | 页码，默认 1 |
| `pageSize` | 每页数量，默认 20 |
| `status` | 按回答状态筛选 |
| `intent` | 按意图类型筛选 |
| `keyword` | 按问题或回答关键词搜索 |
| `startTime` | 起始时间 |
| `endTime` | 结束时间 |

主要返回字段：

| 字段 | 说明 |
|---|---|
| `id` | 问答日志表内部 ID |
| `qa_log_uuid` | 对外问答日志 ID，对应前端反馈使用的 `qaLogId` |
| `session_id` | 会话 ID |
| `user_id` | 用户 ID，可为空 |
| `question` | 用户问题 |
| `intent` | 识别出的问答意图 |
| `status` | 回答状态 |
| `answer` | 系统回答 |
| `object_id` | 关联文物 `objectId` |
| `resolve_source` | 文物对象解析来源 |
| `source_client` | 调用来源，如 `web`、`app`、`demo` |
| `latency_ms` | 处理耗时 |
| `created_at` | 创建时间 |

### 3.2 查询用户反馈

```text
GET /api/admin/qa/feedback
```

常用参数：

| 参数 | 说明 |
|---|---|
| `page` | 页码 |
| `pageSize` | 每页数量 |
| `feedbackType` | 反馈类型：`helpful` 或 `inaccurate` |
| `keyword` | 按反馈说明搜索 |

主要返回字段：

| 字段 | 说明 |
|---|---|
| `id` | 反馈记录 ID |
| `qa_log_id` | 关联问答日志内部 ID |
| `user_id` | 反馈用户 ID，可为空 |
| `feedback_type` | 反馈类型 |
| `comment` | 用户补充说明 |
| `source_client` | 来源端 |
| `created_at` | 创建时间 |

说明：

```text
用户提交 inaccurate 反馈时，问答子系统会自动生成审核任务。
```

### 3.3 查询失败问题

```text
GET /api/admin/qa/failed-questions
```

常用参数：

| 参数 | 说明 |
|---|---|
| `page` | 页码 |
| `pageSize` | 每页数量 |
| `failureType` | 失败类型 |
| `status` | 回答状态 |
| `intent` | 意图类型 |
| `keyword` | 按问题关键词搜索 |

主要返回字段：

| 字段 | 说明 |
|---|---|
| `id` | 失败问题记录 ID |
| `qa_log_id` | 关联问答日志内部 ID |
| `session_id` | 会话 ID |
| `user_id` | 用户 ID，可为空 |
| `question` | 用户问题 |
| `intent` | 识别出的意图 |
| `failure_type` | 失败类型 |
| `object_id` | 关联文物 |
| `error_detail` | 错误或失败说明 |
| `status` | 处理状态 |
| `created_at` | 创建时间 |

### 3.4 查询审核任务

```text
GET /api/admin/qa/review-tasks
```

常用参数：

| 参数 | 说明 |
|---|---|
| `page` | 页码 |
| `pageSize` | 每页数量 |
| `taskStatus` | 审核任务状态，如 `pending`、`done` |
| `reviewResult` | 审核结果，如 `approved`、`rejected`、`fixed` |

主要返回字段：

| 字段 | 说明 |
|---|---|
| `id` | 审核任务 ID |
| `feedback_id` | 关联反馈 ID |
| `qa_log_id` | 关联问答日志内部 ID |
| `task_status` | 任务状态 |
| `review_result` | 审核结果 |
| `priority` | 优先级 |
| `assigned_admin_id` | 分配管理员 ID |
| `reviewer_admin_id` | 实际审核管理员 ID |
| `review_comment` | 审核意见 |
| `corrected_answer` | 修正答案，可为空 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |
| `reviewed_at` | 审核时间 |

### 3.5 处理审核任务

```text
POST /api/admin/qa/review-tasks/{id}/review
```

请求体：

```json
{
  "reviewResult": "rejected",
  "reviewComment": "已核查，当前回答与知识库事实一致。",
  "reviewerId": 1
}
```

字段说明：

| 字段 | 是否必填 | 说明 |
|---|---|---|
| `reviewResult` | 必填 | 审核结果，只支持 `approved`、`rejected`、`fixed` |
| `reviewComment` | 可选 | 管理员审核意见 |
| `reviewerId` | 必填 | 后台管理员 ID，建议对应 `admin_users.id` |

`reviewResult` 含义：

| 值 | 含义 |
|---|---|
| `approved` | 用户反馈有效，回答确实有问题 |
| `rejected` | 用户反馈无效，回答没有问题 |
| `fixed` | 问题已修复或数据已补充 |

处理成功后，任务状态会更新为：

```text
task_status = done
```

### 3.6 高频失败问题统计

```text
GET /api/admin/qa/statistics/failure-types
```

返回示例：

```json
[
  {
    "failureType": "no_data_found",
    "count": 5
  },
  {
    "failureType": "object_not_resolved",
    "count": 3
  }
]
```

### 3.7 高频不准确问题统计

```text
GET /api/admin/qa/statistics/inaccurate-types
```

返回示例：

```json
[
  {
    "intent": "artifact_material",
    "count": 4
  },
  {
    "intent": "artifact_museum",
    "count": 2
  }
]
```

## 4. 对接原则

1. 问答业务数据由知识问答子系统维护。
2. 后台管理系统原则上通过 `/api/admin/qa/*` 接口查询和处理问答业务数据。
3. 不建议后台管理系统直接修改 `qa_` 表，尤其是不建议直接修改 `qa_review_task` 的审核状态。
4. 审核任务处理建议调用：

```text
POST /api/admin/qa/review-tasks/{id}/review
```

5. 管理员操作日志如果总项目有统一要求，建议由后台管理子系统在自己的操作日志机制中记录。

## 5. 当前需要后台组确认的事项

为了正式集成，请后台管理子系统确认以下事项：

1. 后台建议通过 `/api/admin/qa/*` 接口对接，而不是直接修改 `qa_` 表。
2. 后台登录管理员 ID 是否对应公共 `admin_users.id`，即审核接口中的 `reviewerId` 应该传哪个字段。
3. 权限校验由后台管理系统统一负责，还是需要知识问答后端接口接入统一 token 校验。
4. 当前日志列表接口字段是否够用；如果需要查看单条问答的完整来源、事实内容、补充说明，后续可能需要新增问答详情接口。
5. 当前审核任务列表字段是否够用；如果需要在列表中直接展示原问题、原回答和反馈评论，后续可能需要调整审核任务接口返回结构。

## 6. 当前暂时无法确认的事项

以下内容需要根据后台管理子系统的页面设计和总项目集成方案进一步确定：

1. 是否需要新增“单条问答详情接口”。
2. 是否需要新增“单条审核任务详情接口”。
3. 审核任务列表是否需要联表返回原问题、原回答和用户反馈内容。
4. 后台权限鉴权是由后台系统页面层处理，还是由问答后端接口统一校验。
5. 正式集成时接口是直连知识问答后端，还是通过总后端 / 网关转发。

## 7. 联系与变更说明

集成阶段原则上保持现有 `/api/admin/qa/*` 接口稳定。如果后台管理子系统需要新增字段、详情接口或权限校验，请先与知识问答子系统确认接口契约，避免影响 Web、App 和后台多端同时对接。
