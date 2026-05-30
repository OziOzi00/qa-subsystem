# 后端环境配置与联调说明

本文档用于后端、前端和演示同学配置知识问答子系统运行环境。真实密码只允许写入本地 `backend/.env`，不要提交到 Git。

## 1. 本地环境文件

从示例文件复制：

```powershell
Copy-Item backend/.env.example backend/.env
```

需要配置的变量：

```env
PROJECT_NAME=Knowledge QA Subsystem
API_VERSION=0.1.0
API_PREFIX=/api
ENVIRONMENT=development
BACKEND_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

MYSQL_DSN=mysql+pymysql://<username>:<password>@mysql6.sqlpub.com:3311/seitem?charset=utf8mb4
NEO4J_URI=bolt://<neo4j-host>:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<password>
```

注意：Neo4j Python driver 使用 `bolt://` 或 `neo4j://` 协议。若拿到的地址写成 `http://host:7687/`，实际用于代码时应整理为 `bolt://host:7687`。

## 2. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问：

- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/api/health

## 3. 数据库联调状态

当前代码依赖：

- MySQL：公共库 `seitem`，业务表为 7 张 `qa_` 表。
- Neo4j：图谱查询通过 `NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD` 连接。

已验证事项：

- MySQL 可以连接；
- `qa_session`、`qa_log`、`qa_source_record`、`qa_feedback`、`qa_review_task`、`qa_failed_question`、`qa_intent_template` 已存在；
- Neo4j 可以通过 Bolt 协议连接并执行 `RETURN 1`；
- 真实写入链路可完成问答日志、反馈和后台查询。

## 4. 无配置时的降级

- 未配置 MySQL：`/api/qa/ask` 仍可使用 demo 数据；反馈和后台接口返回 503。
- 未配置 Neo4j：图谱和统计类问题返回 `no_data`，不会编造答案。
- 未指定文物且当前意图需要文物：返回 `need_clarification`。

## 5. 安全约定

- 不提交 `backend/.env`。
- 不在 README、接口文档、测试报告中写真实密码。
- 临时联调数据建议使用 `sourceClient=smoke-test`，方便后续筛选。
