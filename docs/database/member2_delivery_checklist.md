# 成员 2 MySQL 数据库与数据访问交付清单

本文档用于课程设计交付检查，逐项对应成员 2 的最终交付物。

## 1. 7 张 `qa_` 表建表 SQL

交付文件：

- `scripts/sql/create_qa_tables.sql`

包含表：

- `qa_session`
- `qa_log`
- `qa_source_record`
- `qa_feedback`
- `qa_review_task`
- `qa_failed_question`
- `qa_intent_template`

说明：

- SQL 只创建 `qa_` 业务表，不修改公共基础表。
- 已按公共库字段类型处理：`users.id` 使用 `INT UNSIGNED`，`admin_users.id` 使用 `INT`。
- `artifact_id` 建外键关联 `artifacts.id`，`object_id` 只建普通索引。

## 2. 数据库设计文档

交付文件：

- `docs/database/qa_tables_design.md`

覆盖内容：

- 每张表的用途。
- 每个字段的类型、含义、约束和备注。
- 主键、外键、唯一约束和主要索引。
- `qa_failed_question.failure_type` 与 API `status` 的映射。
- `qa_session.recent_context_json` 示例。
- `qa_intent_template` 中 SQL / Cypher 模板不能直接动态执行的安全说明。

## 3. MySQL 连接与查询代码

交付代码：

- `backend/app/db/mysql.py`

主要对象：

- `MySQLConfig.from_dsn(dsn)`：解析 `mysql+pymysql://...` 连接串。
- `get_mysql_dsn()`：优先读取环境变量 `MYSQL_DSN`，否则读取 `.env` 或 `backend/.env`。
- `MySQLClient.fetch_one(sql, params)`：查询单条记录。
- `MySQLClient.fetch_all(sql, params)`：查询多条记录。
- `MySQLClient.execute(sql, params)`：执行写入语句并提交事务。

测试文件：

- `backend/tests/test_mysql_client.py`

## 4. 文物详情查询方法

交付代码：

- `backend/app/repositories/mysql/artifact_repository.py`

主要方法：

- `ArtifactRepository.find_by_object_id(object_id)`：按 `artifacts.object_id` 查询文物详情，并补充博物馆、朝代、作者信息。
- `ArtifactRepository.search_candidates(question)`：从问题文本中匹配文物候选，用于配合 `objectId` 解析。

处理规则：

- `object_id` 为空字符串时不查询、不用于 Neo4j 对齐。
- `detail_url`、`image_url` 等空字符串统一转为 `None`。
- `material`、`dimensions` 等事实字段为空时，由检索层返回 `no_data`。

测试文件：

- `backend/tests/test_artifact_repository.py`
- `backend/tests/test_artifact_matcher_mysql.py`

## 5. 问答日志写入方法

交付代码：

- `backend/app/repositories/mysql/qa_log_repository.py`
- `backend/app/services/qa_logger.py`

主要方法：

- `QALogRepository.insert_log(payload)`：写入 `qa_log`。
- `QALogger.record(context)`：生成 `qa_log_uuid`，写入问答日志，并把 `qa_log_uuid` 作为接口 `qaLogId` 返回。

写入字段包括：

- 用户问题、答案、状态、意图、置信度。
- `request_object_id`、最终 `object_id`、`resolve_source`。
- `intent_detail_json`、`retrieval_raw_json`。
- `fact_content`、`supplemental_content`。

测试文件：

- `backend/tests/test_qa_logger.py`

## 6. 答案来源写入方法

交付代码：

- `backend/app/repositories/mysql/qa_log_repository.py`
- `backend/app/services/qa_logger.py`

主要方法：

- `QALogRepository.insert_source(qa_log_id, source)`：写入 `qa_source_record`。
- `QALogger.record(context)`：写入日志后，将本次回答的 `sources` 逐条写入来源记录表。

来源生成位置：

- `backend/app/services/knowledge_retriever.py`

MySQL 来源返回规则：

- `sourceType = mysql`
- `sourceName = 公共 MySQL 文物基础表`
- `detailUrl` 使用文物详情页链接，空值返回 `None`
- `factText` 保存本次回答依据的事实文本

测试文件：

- `backend/tests/test_knowledge_retriever_mysql.py`
- `backend/tests/test_qa_logger.py`

## 7. 失败问题写入方法

交付代码：

- `backend/app/repositories/mysql/qa_log_repository.py`
- `backend/app/services/qa_logger.py`

主要方法：

- `QALogRepository.insert_failed_question(payload)`：写入 `qa_failed_question`。
- `QALogger.record_failed_if_needed(context)`：对失败类回答自动记录失败问题。

写入条件：

- `no_data`
- `need_clarification`
- `unsupported`
- `error`

失败类型映射：

- API `no_data` -> `failure_type = no_data`
- API `need_clarification` -> `failure_type = need_clarification`
- API `unsupported` -> `failure_type = unsupported`
- 检索阶段 `error` -> `failure_type = retrieval_error`
- 其他生成阶段错误 -> `failure_type = generation_error`

测试文件：

- `backend/tests/test_qa_logger.py`

## 8. 总体验证命令

在仓库根目录执行：

```bash
PYTHONPATH=backend pytest backend/tests -q
python3 -m compileall backend/app
```

当前测试设计说明：

- 单元测试使用 fake DB client，不连接公共 MySQL，不写共享数据库。
- 真实公共库的 `qa_` 表已经由 `scripts/sql/create_qa_tables.sql` 创建。
- 后端运行时如需接入公共 MySQL，在环境变量、`.env` 或 `backend/.env` 中配置 `MYSQL_DSN`。
