# 知识问答子系统

本仓库是《软件工程》课程设计“海外藏中国文物知识管理与服务平台”中的知识问答子系统。

子系统目标是基于公共 MySQL 数据库、Neo4j 知识图谱和 FastAPI 后端服务，为 Web 端、掌上博物馆 App 和独立演示页面提供自然语言文物知识问答能力。系统回答必须有事实依据和来源说明；当知识库中没有相关数据时，应明确返回“暂无相关数据”，不能生成不可靠答案。

## 功能范围

第 14 周子系统检查前优先完成：

- `/api/qa/ask` 问答主接口
- 11 类简单问答：收藏地、年代、材质、类型、介绍、作者、作者生平、同作者作品、同朝代文物、尺寸规格、相关文物推荐
- `objectId` 统一关联逻辑
- 答案来源和原始详情页链接展示
- 事实内容 `factContent` 与补充描述 `supplementalContent` 区分
- 可配置轻量 RAG：MySQL / Neo4j 检索事实，LLM 生成补充描述，未配置时模板回退
- 暂无数据兜底回答
- 多轮上下文基础版
- 复杂问答基础版
- 用户反馈机制基础版
- Vue 问答页面独立演示

第 16 周系统集成阶段对接：

- Web 端：通过 `/qa?objectId=...` 跳转到问答页面
- App 端：调用问答 API，负责语音输入和语音播报
- 后台管理：查看问答日志、反馈、失败问题和审核任务
- 知识图谱组：提供 Neo4j 图谱 schema 和连接信息

## 技术路线

```text
Vue 问答页面 / Web / App
        ↓
FastAPI 后端 /api/qa/ask
        ↓
意图识别 + objectId 解析 + 多轮上下文
        ↓
MySQL 文物详情查询 + Neo4j 图谱关系查询
        ↓
答案生成 + 来源记录 + 问答日志 + 用户反馈
```

技术栈：

| 层次 | 技术 |
|---|---|
| 后端 | Python、FastAPI |
| 前端 | Vue |
| 业务数据库 | MySQL |
| 图数据库 | Neo4j |
| 图查询语言 | Cypher |
| 接口风格 | RESTful API |
| 协作平台 | GitHub |

当前项目已集成 FastAPI 后端、Vue 前端、公共 MySQL、Neo4j、反馈后台接口和轻量 RAG 补充生成能力。`DEMO_001` / `DEMO_002` 仍保留用于无数据库环境下的演示和联调。

## 目录结构

```text
qa-subsystem/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由入口
│   │   ├── core/             # 配置
│   │   ├── models/           # 主流程内部模型
│   │   ├── schemas/          # 请求响应模型
│   │   └── services/         # 问答主流程和各模块服务
│   ├── .env.example          # 后端环境变量示例
│   ├── README.md             # 后端启动说明
│   └── requirements.txt      # 后端依赖
├── frontend/                 # Vue 问答前端
├── data/                     # 样例数据或演示数据
├── docs/
│   ├── api/                  # API 文档
│   ├── database/             # 数据库设计文档
│   ├── development/          # Git 协作与 PR 审核规范
│   ├── design/               # 系统设计文档
│   ├── meeting/              # 会议纪要
│   ├── project-plan/         # 项目管理计划
│   ├── requirements/         # 需求规格说明
│   ├── technical-route/      # 技术路线文档
│   └── test/                 # 测试用例与测试报告
└── scripts/
    └── sql/                  # 建表 SQL
```

## 快速启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

启动后访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 演示请求

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/qa/ask `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"question":"演示文物收藏在哪里？","objectId":"DEMO_001","sourceClient":"demo"}'
```

典型响应会包含：

- `qaLogId`：本次问答日志 ID
- `status`：回答状态，如 `answered`、`no_data`、`need_clarification`
- `intent`：识别出的问答意图
- `answer`：自然语言答案
- `resolvedObject`：本次问题关联的文物
- `sources`：答案来源
- `relatedArtifacts`：相关文物推荐

完整接口说明见 [docs/api/qa-api.md](docs/api/qa-api.md)。

## objectId 规则

`objectId` 是本子系统与 Web / App、MySQL、Neo4j、问答日志和反馈记录之间的统一文物标识。

解析优先级：

1. 问题中明确识别出的唯一文物名称。
2. 请求体或 URL 传入的 `objectId`。
3. `sessionId` 或 `conversationId` 对应的当前上下文文物。
4. 多个候选文物时返回候选列表让用户选择。
5. 无法确定文物时提示用户补充文物名称或从详情页进入。

请求传入的 `objectId` 优先于旧会话上下文，因为 Web / App 从文物详情页跳转时代表用户当前正在查看的文物。

## 团队分工

| 人员 | 角色 | 主要职责 |
|---|---|---|
| 组长 | 后端主流程与系统集成 | FastAPI 框架、`/api/qa/ask`、统一响应、`objectId` 解析、模块集成、PR 审核 |
| 成员 2 | MySQL 数据库与数据访问 | 7 张 `qa_` 表、MySQL 查询、日志、来源、失败问题 |
| 成员 3 | Neo4j 图谱查询与复杂问答 | Cypher 查询、收藏地、年代、作者、推荐、统计和多跳基础版 |
| 成员 4 | 意图识别、多轮上下文与答案生成 | 11 类意图、文物名称识别、回答模板、暂无数据兜底、多轮上下文 |
| 成员 5 | Vue 前端问答页面 | 问答页面、来源展示、推荐展示、反馈按钮、URL 接收 `objectId` |
| 成员 6 | 反馈审核、后台接口与测试文档 | `/api/qa/feedback`、审核任务、后台接口、统计接口、测试报告、用户手册 |

详细协作规范见：

- [docs/development/git-workflow.md](docs/development/git-workflow.md)
- [docs/development/review-checklist.md](docs/development/review-checklist.md)

## 当前开发状态

已完成：

- FastAPI 后端基础框架
- `/api/health`
- `/api/qa/ask` 主接口
- 主流程编排
- `objectId` 解析逻辑
- MySQL 文物基础信息查询、问答日志、来源记录和失败问题记录
- Neo4j 图谱查询、统计类问答和简单多跳问答基础版
- 11 类简单问答意图识别、实体抽取和最近 5 轮上下文基础版
- 可配置轻量 RAG，未配置 LLM 时模板回退
- `/api/qa/feedback`、审核任务和后台管理接口
- Vue 问答页面、来源展示、推荐展示和反馈按钮
- 演示数据 `DEMO_001` / `DEMO_002`
- API 文档
- Git 协作和 PR 审核规范
- pytest 自动化测试和前端构建检查

待增强：

- 获取 LLM API Key 后验证真实大模型补充生成
- 多轮上下文持久化到 `qa_session`
- 根据最终知识图谱数据继续完善演示样例
- 第 16 周配合 Web / App / 后台管理系统做整体集成

## 文档入口

| 文档 | 路径 |
|---|---|
| 项目管理计划 | [docs/project-plan/知识问答子系统项目管理计划-v0.4.md](docs/project-plan/知识问答子系统项目管理计划-v0.4.md) |
| API 文档 | [docs/api/qa-api.md](docs/api/qa-api.md) |
| Git 协作规范 | [docs/development/git-workflow.md](docs/development/git-workflow.md) |
| PR 审核清单 | [docs/development/review-checklist.md](docs/development/review-checklist.md) |
| 后端启动说明 | [backend/README.md](backend/README.md) |

## 开发检查

后端改动后至少运行：

```powershell
cd backend
python -m compileall app
```

如果修改了接口或主流程，还应启动服务并检查：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

然后访问：

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

## 质量要求

1. 不编造知识库中不存在的文物事实。
2. 每条可回答问题都应尽量返回来源。
3. 数据来源、事实内容和补充描述必须区分展示。
4. `main` 分支保持可运行。
5. 队友通过 PR 合并，组长负责审核接口契约和集成风险。
