# 知识问答子系统 qa_ 表设计说明

本文档整理知识问答子系统新增的 7 张 `qa_` 业务表。设计依据包括：

- 问答接口统一使用 `objectId`，数据库内部统一使用 `object_id`。
- 公共 MySQL 已存在 `artifacts`、`museums`、`dynasties`、`artists`、`artifact_artist`、`artifact_images`、`users`、`admin_users` 等基础表。
- 问答组不重复建设文物、用户、博物馆、作者等基础表，只新增问答业务表。
- 当前公共库中 `artifacts.object_id` 不是唯一索引，且样例数据存在空值，因此 `qa_` 表通过 `artifact_id` 建外键，通过 `object_id` 建普通索引，避免依赖不稳定的外键。

## 1. 总体设计约定

| 项目 | 设计 |
|---|---|
| 数据库 | 公共 MySQL 数据库 `seitem` |
| 字符集 | `utf8mb4` |
| 排序规则 | `utf8mb4_0900_ai_ci` |
| 存储引擎 | `InnoDB` |
| 主键类型 | `BIGINT UNSIGNED AUTO_INCREMENT` |
| 对外问答日志 ID | `qa_log.qa_log_uuid`，对应接口字段 `qaLogId` |
| 文物关联 | 同时保留 `artifact_id` 和 `object_id` |
| 普通用户关联 | 通过 `user_id` 关联公共表 `users.id`，字段类型为 `INT UNSIGNED` |
| 后台管理员关联 | 通过 `assigned_admin_id`、`reviewer_admin_id` 关联 `admin_users.id`，字段类型为 `INT` |
| 时间字段 | 业务发生时间使用 `DATETIME`，SQL 中明确写 `DEFAULT CURRENT_TIMESTAMP` 或 `ON UPDATE CURRENT_TIMESTAMP` |

## 2. 表关系概览

```text
users.id
  ├── qa_session.user_id
  ├── qa_log.user_id
  ├── qa_feedback.user_id
  ├── qa_failed_question.user_id
  └── qa_failed_question.handled_by

admin_users.id
  ├── qa_review_task.assigned_admin_id
  └── qa_review_task.reviewer_admin_id

artifacts.id
  ├── qa_session.current_artifact_id
  ├── qa_log.artifact_id
  ├── qa_source_record.artifact_id
  └── qa_failed_question.artifact_id

qa_session.id
  └── qa_log.session_pk

qa_log.id
  ├── qa_source_record.qa_log_id
  ├── qa_feedback.qa_log_id
  ├── qa_review_task.qa_log_id
  └── qa_failed_question.qa_log_id

qa_feedback.id
  └── qa_review_task.feedback_id
```

## 3. `qa_session` - 问答会话上下文表

用于保存多轮问答上下文，支持最近 5 轮上下文、当前文物对象和客户端来源。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 会话记录内部主键 | 仅数据库内部使用 |
| `session_id` | `VARCHAR(100)` | 非空，唯一 | 接口层会话 ID | 对应 API `sessionId` |
| `conversation_id` | `VARCHAR(100)` | 可空 | App 或其他客户端对话 ID | 对应 API `conversationId` |
| `user_id` | `INT UNSIGNED` | 可空，外键 | 用户 ID | 关联 `users.id`，未登录用户可为空 |
| `current_artifact_id` | `INT UNSIGNED` | 可空，外键 | 当前上下文文物内部 ID | 关联 `artifacts.id` |
| `current_object_id` | `VARCHAR(100)` | 可空，索引 | 当前上下文文物统一标识 | 对应数据库和 Neo4j 的 `object_id` |
| `last_intent` | `VARCHAR(80)` | 可空 | 最近一次识别到的意图 | 如 `artifact_material` |
| `recent_context_json` | `JSON` | 可空 | 最近对话上下文 | 建议保存最近 5 轮问答摘要 |
| `source_client` | `VARCHAR(50)` | 可空 | 调用来源 | 如 `web`、`app`、`demo` |
| `status` | `VARCHAR(20)` | 非空，默认 `active` | 会话状态 | 建议值：`active`、`closed`、`expired` |
| `last_active_at` | `DATETIME` | 非空 | 最近活跃时间 | 每次问答后更新 |
| `created_at` | `DATETIME` | 非空 | 创建时间 | 默认当前时间 |
| `updated_at` | `DATETIME` | 非空 | 更新时间 | 自动随更新刷新 |

主键：`id`

外键：

- `user_id` -> `users(id)`
- `current_artifact_id` -> `artifacts(id)`

主要索引：

- `uk_qa_session_session_id(session_id)`
- `idx_qa_session_user(user_id)`
- `idx_qa_session_object(current_object_id)`
- `idx_qa_session_last_active(last_active_at)`

`recent_context_json` 建议使用统一 JSON 数组格式，示例：

```json
[
  {
    "qaLogId": "5f5ef3f4-3c72-41f1-b48f-9e20e01c7e2a",
    "question": "它是什么材质？",
    "intent": "artifact_material",
    "objectId": "MET_12345",
    "answerSummary": "材质为 porcelain",
    "createdAt": "2026-05-24 10:00:00"
  }
]
```

## 4. `qa_log` - 问答主日志表

用于保存每一次用户提问、系统回答、识别意图、解析对象、回答状态和调试数据。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 问答日志内部主键 | 供业务表外键使用 |
| `qa_log_uuid` | `CHAR(36)` | 非空，唯一 | 对外问答日志 ID | 对应 API `qaLogId` |
| `session_pk` | `BIGINT UNSIGNED` | 可空，外键 | 会话表内部主键 | 关联 `qa_session.id` |
| `session_id` | `VARCHAR(100)` | 可空 | 接口层会话 ID | 冗余保存，便于查询 |
| `conversation_id` | `VARCHAR(100)` | 可空 | 客户端对话 ID | 对应 API `conversationId` |
| `user_id` | `INT UNSIGNED` | 可空，外键 | 提问用户 ID | 未登录可为空 |
| `request_object_id` | `VARCHAR(100)` | 可空，索引 | 请求原始传入的文物标识 | 记录请求体或 URL 中的 `objectId`，用于排查解析优先级 |
| `question` | `TEXT` | 非空 | 用户原始问题 | 对应 API `question` |
| `normalized_question` | `VARCHAR(1000)` | 可空 | 规范化后的问题 | 去空格、同义词归一等处理结果 |
| `intent` | `VARCHAR(80)` | 可空，索引 | 识别意图编码 | 如 `artifact_museum` |
| `intent_confidence` | `DECIMAL(5,4)` | 可空 | 意图识别置信度 | 取值建议 0 到 1 |
| `intent_detail_json` | `JSON` | 可空 | 意图识别详情 | 保存 `matchedKeywords`、`entities`、`confidence` 等调试信息 |
| `status` | `VARCHAR(30)` | 非空，索引 | 回答状态 | 对应 `answered`、`no_data`、`need_clarification`、`unsupported`、`error` |
| `answer` | `TEXT` | 可空 | 返回给用户的答案 | 对应 API `answer` |
| `fact_content` | `TEXT` | 可空 | 事实内容 | 来自 MySQL、Neo4j 或确认数据源 |
| `supplemental_content` | `TEXT` | 可空 | 补充描述 | 来自模板或大模型的补充性描述 |
| `artifact_id` | `INT UNSIGNED` | 可空，外键 | 关联文物内部 ID | 关联 `artifacts.id` |
| `object_id` | `VARCHAR(100)` | 可空，索引 | 关联文物统一标识 | 对应接口 `objectId` 和 Neo4j `object_id` |
| `resolve_source` | `VARCHAR(50)` | 可空 | 文物解析来源 | 如 `question_entity`、`request_object_id`、`session_context` |
| `candidates_json` | `JSON` | 可空 | 多候选文物列表 | `need_clarification` 时保存候选项 |
| `source_client` | `VARCHAR(50)` | 可空 | 调用来源 | 如 `web`、`app`、`demo` |
| `retrieval_raw_json` | `JSON` | 可空 | 检索原始调试数据 | 保存 MySQL/Neo4j 检索摘要，不保存敏感信息 |
| `error_message` | `TEXT` | 可空 | 错误信息 | `error` 状态时使用 |
| `latency_ms` | `INT UNSIGNED` | 可空 | 本次问答耗时毫秒数 | 便于性能统计 |
| `created_at` | `DATETIME` | 非空，索引 | 创建时间 | 问答发生时间 |

主键：`id`

唯一键：

- `uk_qa_log_uuid(qa_log_uuid)`

外键：

- `session_pk` -> `qa_session(id)`
- `user_id` -> `users(id)`
- `artifact_id` -> `artifacts(id)`

主要索引：

- `idx_qa_log_session(session_id)`
- `idx_qa_log_user_created(user_id, created_at)`
- `idx_qa_log_request_object(request_object_id)`
- `idx_qa_log_object(object_id)`
- `idx_qa_log_intent_status(intent, status)`
- `idx_qa_log_created(created_at)`

`request_object_id` 保存用户请求中原始传入的 `objectId`，`object_id` 保存系统最终解析后采用的文物标识，`resolve_source` 保存采用原因。这样可以排查“请求传入对象、问题文本识别对象、最终使用对象”不一致的问题。

`intent_detail_json` 示例：

```json
{
  "matchedKeywords": ["多少件"],
  "entities": {
    "museum": "大英博物馆"
  },
  "confidence": 0.92
}
```

## 5. `qa_source_record` - 答案来源记录表

用于保存每条回答用到的数据来源，支撑前端来源展示和后台追溯。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 来源记录主键 | 数据库内部使用 |
| `qa_log_id` | `BIGINT UNSIGNED` | 非空，外键 | 问答日志 ID | 关联 `qa_log.id` |
| `source_type` | `VARCHAR(30)` | 非空，索引 | 来源类型 | 对应 `mysql`、`neo4j`、`llm`、`template` |
| `source_name` | `VARCHAR(200)` | 非空 | 来源名称 | 如博物馆名称、Neo4j 知识图谱、模板名称 |
| `source_table` | `VARCHAR(100)` | 可空 | MySQL 来源表 | 如 `artifacts`、`artists` |
| `source_record_id` | `VARCHAR(100)` | 可空 | 来源记录 ID | 可保存 MySQL 主键或 Neo4j 节点 ID |
| `artifact_id` | `INT UNSIGNED` | 可空，外键 | 关联文物内部 ID | 关联 `artifacts.id` |
| `object_id` | `VARCHAR(100)` | 可空，索引 | 关联文物统一标识 | 保留给 Neo4j 和 API 对齐 |
| `detail_url` | `VARCHAR(500)` | 可空 | 原始详情页链接 | 来源展示使用 |
| `fact_text` | `TEXT` | 可空 | 来源事实文本 | 对应 API `sources[].factText` |
| `source_payload_json` | `JSON` | 可空 | 来源原始摘要 | 保存查询字段、节点关系等结构化信息 |
| `confidence` | `DECIMAL(5,4)` | 可空 | 来源置信度 | 取值建议 0 到 1 |
| `created_at` | `DATETIME` | 非空 | 创建时间 | 默认当前时间 |

主键：`id`

外键：

- `qa_log_id` -> `qa_log(id)`
- `artifact_id` -> `artifacts(id)`

主要索引：

- `idx_qa_source_log(qa_log_id)`
- `idx_qa_source_type(source_type)`
- `idx_qa_source_object(object_id)`

## 6. `qa_feedback` - 用户反馈表

用于保存用户对回答的反馈，支持“有帮助 / 不准确”机制。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 反馈记录主键 | 对应反馈接口返回的 `feedbackId` |
| `qa_log_id` | `BIGINT UNSIGNED` | 非空，外键 | 问答日志 ID | 关联 `qa_log.id` |
| `user_id` | `INT UNSIGNED` | 可空，外键 | 反馈用户 ID | 未登录用户可为空 |
| `feedback_type` | `VARCHAR(30)` | 非空，索引 | 反馈类型 | 建议值：`helpful`、`inaccurate` |
| `comment` | `TEXT` | 可空 | 用户补充说明 | 如“收藏博物馆不正确” |
| `source_client` | `VARCHAR(50)` | 可空 | 调用来源 | 如 `web`、`app`、`demo` |
| `created_at` | `DATETIME` | 非空，索引 | 创建时间 | 默认当前时间 |

主键：`id`

外键：

- `qa_log_id` -> `qa_log(id)`
- `user_id` -> `users(id)`

主要索引：

- `idx_qa_feedback_log(qa_log_id)`
- `idx_qa_feedback_user(user_id)`
- `uk_qa_feedback_log_user_type(qa_log_id, user_id, feedback_type)`
- `idx_qa_feedback_type_created(feedback_type, created_at)`

重复反馈处理：

- 数据库增加 `uk_qa_feedback_log_user_type(qa_log_id, user_id, feedback_type)`，限制同一登录用户对同一条回答重复提交同类反馈。
- 匿名用户的 `user_id` 可能为 `NULL`，MySQL 唯一约束允许多条 `NULL` 组合，因此接口层仍需要结合会话、客户端或限流逻辑限制重复提交。

## 7. `qa_review_task` - 人工审核任务表

用于保存“不准确”反馈生成的审核任务，供后台管理系统查看和处理。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 审核任务主键 | 后台接口路径可使用该 ID |
| `feedback_id` | `BIGINT UNSIGNED` | 非空，外键 | 反馈记录 ID | 关联 `qa_feedback.id` |
| `qa_log_id` | `BIGINT UNSIGNED` | 非空，外键 | 问答日志 ID | 冗余保存，便于查询 |
| `task_status` | `VARCHAR(30)` | 非空，索引 | 任务状态 | 建议值：`pending`、`processing`、`done`、`closed` |
| `review_result` | `VARCHAR(30)` | 可空 | 审核结果 | 对应 `approved`、`rejected`、`fixed` |
| `priority` | `TINYINT UNSIGNED` | 非空，默认 1 | 优先级 | 建议 1 低、2 中、3 高 |
| `assigned_admin_id` | `INT` | 可空，外键 | 分配给的管理员 ID | 关联 `admin_users.id` |
| `reviewer_admin_id` | `INT` | 可空，外键 | 实际审核管理员 ID | 关联 `admin_users.id` |
| `review_comment` | `TEXT` | 可空 | 审核意见 | 后台提交审核结果时填写 |
| `corrected_answer` | `TEXT` | 可空 | 修正后的答案 | `fixed` 时可填写 |
| `created_at` | `DATETIME` | 非空，索引 | 创建时间 | 反馈为 `inaccurate` 时生成 |
| `updated_at` | `DATETIME` | 非空 | 更新时间 | 自动随更新刷新 |
| `reviewed_at` | `DATETIME` | 可空 | 审核完成时间 | 提交审核结果时填写 |

主键：`id`

外键：

- `feedback_id` -> `qa_feedback(id)`
- `qa_log_id` -> `qa_log(id)`
- `assigned_admin_id` -> `admin_users(id)`
- `reviewer_admin_id` -> `admin_users(id)`

主要索引：

- `uk_qa_review_feedback(feedback_id)`
- `idx_qa_review_log(qa_log_id)`
- `idx_qa_review_status_created(task_status, created_at)`
- `idx_qa_review_assigned_admin(assigned_admin_id)`
- `idx_qa_review_reviewer_admin(reviewer_admin_id)`

`feedback_id` 使用唯一约束，保证一条“不准确”反馈原则上只生成一个审核任务，避免重复建任务。

## 8. `qa_failed_question` - 失败问题记录表

用于保存无法回答、暂无数据、需要澄清、暂不支持和系统错误等问题。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 失败问题主键 | 后台统计使用 |
| `qa_log_id` | `BIGINT UNSIGNED` | 可空，外键 | 问答日志 ID | 关联 `qa_log.id`，日志写入失败时可为空 |
| `session_id` | `VARCHAR(100)` | 可空，索引 | 会话 ID | 便于追溯上下文 |
| `user_id` | `INT UNSIGNED` | 可空，外键 | 用户 ID | 未登录可为空 |
| `question` | `TEXT` | 非空 | 原始问题 | 用户输入 |
| `normalized_question` | `VARCHAR(1000)` | 可空 | 规范化问题 | 便于聚合分析 |
| `question_hash` | `CHAR(64)` | 可空，索引 | 问题哈希 | 建议使用 SHA-256 统计重复问题 |
| `intent` | `VARCHAR(80)` | 可空，索引 | 识别意图 | 可能为空 |
| `failure_type` | `VARCHAR(40)` | 非空，索引 | 失败类型 | 建议值：`no_data`、`need_clarification`、`unsupported`、`retrieval_error`、`generation_error` |
| `artifact_id` | `INT UNSIGNED` | 可空，外键 | 关联文物内部 ID | 关联 `artifacts.id` |
| `object_id` | `VARCHAR(100)` | 可空，索引 | 关联文物统一标识 | 便于定位某文物高频缺失数据 |
| `error_detail` | `TEXT` | 可空 | 错误详情 | 记录异常或无数据原因 |
| `status` | `VARCHAR(30)` | 非空，默认 `open` | 处理状态 | 建议值：`open`、`ignored`、`resolved` |
| `handled_by` | `INT UNSIGNED` | 可空，外键 | 处理人 ID | 关联 `users.id` |
| `handled_at` | `DATETIME` | 可空 | 处理时间 | 问题关闭时填写 |
| `created_at` | `DATETIME` | 非空，索引 | 创建时间 | 默认当前时间 |

主键：`id`

外键：

- `qa_log_id` -> `qa_log(id)`
- `user_id` -> `users(id)`
- `artifact_id` -> `artifacts(id)`
- `handled_by` -> `users(id)`

主要索引：

- `idx_qa_failed_log(qa_log_id)`
- `idx_qa_failed_hash(question_hash)`
- `idx_qa_failed_type_created(failure_type, created_at)`
- `idx_qa_failed_object(object_id)`
- `idx_qa_failed_status(status)`

`failure_type` 与 API `status` 的建议映射：

| `failure_type` | API `status` | 说明 |
|---|---|---|
| `no_data` | `no_data` | MySQL、Neo4j 或补充数据中查不到事实 |
| `need_clarification` | `need_clarification` | 多候选文物、缺少必要实体、上下文不足 |
| `unsupported` | `unsupported` | 问题类型暂不支持 |
| `retrieval_error` | `error` | MySQL、Neo4j 或外部检索异常 |
| `generation_error` | `error` | 模板或大模型生成阶段异常 |

## 9. `qa_intent_template` - 意图与回答模板表

用于保存意图编码、常见问法、查询模板、回答模板和暂无数据兜底模板。

| 字段 | 类型 | 约束 | 含义 | 备注 |
|---|---|---|---|---|
| `id` | `BIGINT UNSIGNED` | 主键，自增 | 模板主键 | 数据库内部使用 |
| `intent_code` | `VARCHAR(80)` | 非空，唯一 | 意图编码 | 如 `artifact_material` |
| `intent_name` | `VARCHAR(100)` | 非空 | 意图中文名称 | 如“文物材质” |
| `description` | `TEXT` | 可空 | 意图说明 | 说明适用问题范围 |
| `data_source` | `VARCHAR(50)` | 非空 | 主要数据源 | 建议值：`mysql`、`neo4j`、`mixed`、`template` |
| `question_patterns_json` | `JSON` | 可空 | 常见问法模板 | 如“这件文物是什么材质” |
| `mysql_query_template` | `TEXT` | 可空 | MySQL 查询模板 | 仅作配置参考、文档记录或后台查看，不直接动态执行 |
| `neo4j_query_template` | `TEXT` | 可空 | Neo4j 查询模板 | 仅作配置参考、文档记录或后台查看，不直接动态执行 |
| `answer_template` | `TEXT` | 可空 | 回答模板 | 生成 `answer` 使用 |
| `no_data_template` | `TEXT` | 可空 | 暂无数据模板 | 必须明确“暂无相关数据” |
| `enabled` | `TINYINT(1)` | 非空，默认 1 | 是否启用 | 1 启用，0 停用 |
| `version` | `VARCHAR(30)` | 非空，默认 `v1` | 模板版本 | 便于后续迭代 |
| `created_at` | `DATETIME` | 非空 | 创建时间 | 默认当前时间 |
| `updated_at` | `DATETIME` | 非空 | 更新时间 | 自动随更新刷新 |

主键：`id`

唯一键：

- `uk_qa_intent_code(intent_code)`

主要索引：

- `idx_qa_intent_enabled(enabled)`
- `idx_qa_intent_source(data_source)`

安全说明：真实查询优先走代码中固定的参数化查询方法。不要把数据库中保存的 `mysql_query_template` 或 `neo4j_query_template` 无校验拼接后直接执行，避免注入风险和维护风险。

## 10. 建表与落库建议

1. 先在测试库执行 `scripts/sql/create_qa_tables.sql`，确认无报错后再在公共库执行。
2. 如果公共库已有同名 `qa_` 表，先备份并对比字段差异，不要直接覆盖。
3. 代码接入时，`/api/qa/ask` 返回的 `qaLogId` 应取 `qa_log.qa_log_uuid`。
4. 来源落库时，将响应中的 `sources` 逐条写入 `qa_source_record`。
5. 当状态为 `no_data`、`need_clarification`、`unsupported` 或 `error` 时，应同步写入 `qa_failed_question`。
6. 当反馈类型为 `inaccurate` 时，应写入 `qa_feedback` 后生成 `qa_review_task`。
7. 查询公共 `artifacts` 表时必须处理空值：`detail_url` 为空时来源链接返回 `null`，`dimensions`、`material` 等事实字段为空时回答“暂无相关数据”，`object_id` 为空字符串时不能用于 Neo4j 关联。
