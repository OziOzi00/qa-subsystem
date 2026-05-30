# 知识问答子系统 — 测试用例

| 版本 | 日期 | 编制人 | 审核 |
|---|---|---|---|
| v0.1 | 2026-05-25 | 成员 6 | 组长 |

---

## T1 健康检查

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-HEALTH-001 |
| **模块** | 系统基础 |
| **接口** | `GET /api/health` |
| **测试名称** | 健康检查正常返回 |
| **前置条件** | 后端服务已启动 |
| **测试步骤** | 1. 发送 GET /api/health |
| **预期结果** | 返回 200，`status` 为 `"ok"`，`databaseConfigured` 为布尔值 |
| **备注** | 无需认证 |

## T2 问答主接口

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ASK-001 |
| **模块** | 问答核心 |
| **接口** | `POST /api/qa/ask` |
| **测试名称** | 基本问答请求 |
| **前置条件** | 后端服务已启动 |
| **测试步骤** | 1. 发送 POST /api/qa/ask，body: `{"question": "演示文物收藏在哪里？", "objectId": "DEMO_001"}` |
| **预期结果** | 返回 200，`status` 为 `"answered"`，`answer` 不为空，`qaLogId` 为合法 UUID |
| **备注** | |

| **用例编号** | TC-ASK-002 |
| **模块** | 问答核心 |
| **接口** | `POST /api/qa/ask` |
| **测试名称** | 问题为空返回校验错误 |
| **前置条件** | 后端服务已启动 |
| **测试步骤** | 1. 发送 POST /api/qa/ask，body: `{"question": ""}` |
| **预期结果** | 返回 422，包含字段校验错误 |
| **备注** | |

| **用例编号** | TC-ASK-003 |
| **模块** | 问答核心 |
| **接口** | `POST /api/qa/ask` |
| **测试名称** | 不支持的问题类型 |
| **前置条件** | 后端服务已启动 |
| **测试步骤** | 1. 发送 POST /api/qa/ask，body: `{"question": "今天天气怎么样？"}` |
| **预期结果** | 返回 200，`status` 为 `"unsupported"` |
| **备注** | |

## T3 用户反馈

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-FB-001 |
| **模块** | 反馈机制 |
| **接口** | `POST /api/qa/feedback` |
| **测试名称** | 提交有帮助反馈 |
| **前置条件** | 存在有效的 qaLogId |
| **测试步骤** | 1. POST /api/qa/feedback，body: `{"qaLogId": "<uuid>", "feedbackType": "helpful"}` |
| **预期结果** | 返回 200，`feedbackId` > 0，`reviewTaskCreated` 为 `false` |
| **备注** | |

| **用例编号** | TC-FB-002 |
| **模块** | 反馈机制 |
| **接口** | `POST /api/qa/feedback` |
| **测试名称** | 提交不准确反馈（自动生成审核任务） |
| **前置条件** | 存在有效的 qaLogId |
| **测试步骤** | 1. POST /api/qa/feedback，body: `{"qaLogId": "<uuid>", "userId": 9, "feedbackType": "inaccurate", "comment": "答案不正确"}` |
| **预期结果** | 返回 200，`reviewTaskCreated` 为 `true` |
| **备注** | 自动在 qa_review_task 生成一条 pending 记录 |

| **用例编号** | TC-FB-003 |
| **模块** | 反馈机制 |
| **接口** | `POST /api/qa/feedback` |
| **测试名称** | 反馈类型无效 |
| **前置条件** | 存在有效的 qaLogId |
| **测试步骤** | 1. POST /api/qa/feedback，body: `{"qaLogId": "<uuid>", "feedbackType": "invalid"}` |
| **预期结果** | 返回 422 |
| **备注** | feedbackType 仅允许 `helpful` / `inaccurate` |

| **用例编号** | TC-FB-004 |
| **模块** | 反馈机制 |
| **接口** | `POST /api/qa/feedback` |
| **测试名称** | 缺少必填字段 |
| **前置条件** | 后端服务已启动 |
| **测试步骤** | 1. POST /api/qa/feedback，body: `{}` |
| **预期结果** | 返回 422 |
| **备注** | qaLogId 和 feedbackType 均为必填 |

## T4 后台管理 — 查询问答日志

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ADM-LOG-001 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/logs` |
| **测试名称** | 默认分页查询 |
| **前置条件** | qa_log 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/logs?page=1&pageSize=10 |
| **预期结果** | 返回 200，包含 `items`、`total`、`page`、`pageSize`、`totalPages` |
| **备注** | |

| **用例编号** | TC-ADM-LOG-002 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/logs` |
| **测试名称** | 按意图筛选 |
| **前置条件** | qa_log 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/logs?intent=artifact_museum |
| **预期结果** | 返回 200，items 中 intent 均为 `artifact_museum` |
| **备注** | |

| **用例编号** | TC-ADM-LOG-003 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/logs` |
| **测试名称** | 关键词搜索 |
| **前置条件** | qa_log 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/logs?keyword=演示 |
| **预期结果** | 返回 200，items 的 question 或 answer 包含"演示" |
| **备注** | |

| **用例编号** | TC-ADM-LOG-004 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/logs` |
| **测试名称** | 时间范围筛选 |
| **前置条件** | qa_log 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/logs?startTime=2026-01-01&endTime=2026-12-31 |
| **预期结果** | 返回 200，created_at 在指定范围内 |
| **备注** | |

## T5 后台管理 — 查询反馈

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ADM-FB-001 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/feedback` |
| **测试名称** | 默认分页查询反馈 |
| **前置条件** | qa_feedback 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/feedback?page=1&pageSize=10 |
| **预期结果** | 返回 200，分页结构正确 |
| **备注** | |

| **用例编号** | TC-ADM-FB-002 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/feedback` |
| **测试名称** | 按反馈类型筛选 |
| **前置条件** | qa_feedback 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/feedback?feedbackType=inaccurate |
| **预期结果** | 返回 200，items 的 feedback_type 均为 `inaccurate` |
| **备注** | |

## T6 后台管理 — 查询失败问题

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ADM-FQ-001 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/failed-questions` |
| **测试名称** | 默认分页查询失败问题 |
| **前置条件** | qa_failed_question 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/failed-questions?page=1&pageSize=10 |
| **预期结果** | 返回 200，分页结构正确 |
| **备注** | |

## T7 后台管理 — 查询审核任务

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ADM-RT-001 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/review-tasks` |
| **测试名称** | 默认分页查询审核任务 |
| **前置条件** | qa_review_task 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/review-tasks?page=1&pageSize=10 |
| **预期结果** | 返回 200，分页结构正确 |
| **备注** | |

| **用例编号** | TC-ADM-RT-002 |
| **模块** | 后台管理 |
| **接口** | `GET /api/admin/qa/review-tasks` |
| **测试名称** | 按任务状态筛选 |
| **前置条件** | qa_review_task 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/review-tasks?taskStatus=pending |
| **预期结果** | 返回 200，items 的 task_status 均为 `pending` |
| **备注** | |

## T8 后台管理 — 处理审核任务

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-ADM-RV-001 |
| **模块** | 后台管理 |
| **接口** | `POST /api/admin/qa/review-tasks/{id}/review` |
| **测试名称** | 审核通过 |
| **前置条件** | 存在 pending 状态的审核任务，审核员 ID 在 admin_users 中存在 |
| **测试步骤** | 1. POST /api/admin/qa/review-tasks/1/review，body: `{"reviewResult": "approved", "reviewComment": "确认反馈有效", "reviewerId": 1}` |
| **预期结果** | 返回 200，`message` 为"审核结果已提交。" |
| **备注** | 审核后 task_status 变为 `done`，review_result 设为 `approved` |

| **用例编号** | TC-ADM-RV-002 |
| **模块** | 后台管理 |
| **接口** | `POST /api/admin/qa/review-tasks/{id}/review` |
| **测试名称** | 审核不存在的任务 |
| **前置条件** | 无 |
| **测试步骤** | 1. POST /api/admin/qa/review-tasks/99999/review，body: `{"reviewResult": "approved", "reviewerId": 1}` |
| **预期结果** | 返回 404，`detail` 为"审核任务不存在。" |
| **备注** | |

| **用例编号** | TC-ADM-RV-003 |
| **模块** | 后台管理 |
| **接口** | `POST /api/admin/qa/review-tasks/{id}/review` |
| **测试名称** | 审核结果为 rejected |
| **前置条件** | 存在 pending 状态的审核任务 |
| **测试步骤** | 1. POST /api/admin/qa/review-tasks/{id}/review，body: `{"reviewResult": "rejected", "reviewComment": "反馈无效", "reviewerId": 1}` |
| **预期结果** | 返回 200，审核任务状态更新为 rejected |
| **备注** | |

## T9 统计接口

| 字段 | 内容 |
|---|---|
| **用例编号** | TC-STAT-001 |
| **模块** | 统计 |
| **接口** | `GET /api/admin/qa/statistics/failure-types` |
| **测试名称** | 高频失败类型统计 |
| **前置条件** | qa_failed_question 表有数据 |
| **测试步骤** | 1. GET /api/admin/qa/statistics/failure-types |
| **预期结果** | 返回 200，数组按 count 降序排列 |
| **备注** | |

| **用例编号** | TC-STAT-002 |
| **模块** | 统计 |
| **接口** | `GET /api/admin/qa/statistics/inaccurate-types` |
| **测试名称** | 高频不准确类型统计 |
| **前置条件** | qa_feedback 表有 inaccurate 数据 |
| **测试步骤** | 1. GET /api/admin/qa/statistics/inaccurate-types |
| **预期结果** | 返回 200，按 intent 分组统计降序 |
| **备注** | |

---

## 测试环境

| 项目 | 值 |
|---|---|
| 后端服务 | http://127.0.0.1:8000 |
| MySQL | mysql6.sqlpub.com:3311/seitem |
| Neo4j | bolt://39.106.206.182:7687 |
| Python | 3.12.3 |
| FastAPI | 0.111.0 |
