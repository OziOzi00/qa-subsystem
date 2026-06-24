# 知识问答子系统

本仓库是《软件工程》课程设计“海外藏中国文物知识管理与服务平台”中的知识问答子系统。系统围绕海外藏中国文物，提供基于公共 MySQL、Neo4j 知识图谱和 FastAPI 后端的文物知识问答能力，并已完成子系统开发、组内集成和与其他子系统的阶段性集成对接。

系统的核心原则是：事实内容必须来自可追溯的数据源；大语言模型只用于补充性描述；当知识库中没有相关数据时，明确返回“暂无相关数据”或提示用户补充信息，不生成无依据答案。

## 当前完成状态

截至课程系统集成检查阶段，本子系统已完成以下内容：

- FastAPI 后端基础框架与统一 API 路由。
- `/api/qa/ask` 问答主接口。
- `/api/qa/feedback` 用户反馈接口。
- `/api/admin/qa/*` 后台管理接口。
- 11 类简单问答。
- 复杂问答基础版。
- 多轮上下文基础版。
- `objectId` 统一文物标识解析。
- MySQL 文物属性查询、问答日志、来源记录、反馈、失败问题和审核任务写入。
- Neo4j 图谱关系查询、统计类查询和相关文物推荐。
- 轻量 RAG：MySQL / Neo4j 检索事实，LLM 或模板生成补充说明。
- `answer`、`factContent`、`supplementalContent` 和 `sources` 分区返回。
- Vue 问答前端页面。
- 多候选文物澄清与选择。
- 用户“有帮助 / 不准确”反馈。
- 后台日志、反馈、失败问题、审核任务和统计结果查询。
- 与掌上博物馆 App 子系统、知识图谱构建子系统、后台管理子系统完成集成对接。
- 用户手册、测试报告、接口文档、集成文档、会议纪要和 AI 答辩提交材料整理。

## 功能范围

### 简单问答

系统已覆盖 11 类简单问答：

- 文物收藏地
- 文物年代
- 文物材质
- 文物类型
- 文物介绍
- 书画作者
- 作者生平
- 同一作者作品
- 同一朝代文物
- 文物尺寸与规格
- 相关文物推荐

### 复杂问答基础版

当前已支持的复杂问答包括：

- 某博物馆收藏多少件中国文物。
- 某朝代有哪些代表性文物。
- 收藏某类型文物最多的博物馆及所在城市。
- 博物馆所在城市查询。
- 基于文物、朝代、作者、博物馆关系的基础多跳查询。

比较类问答、历史人物路径查询和开放式文化导览属于后续增强方向，当前不作为本阶段核心交付。

### 答案可信度设计

接口返回时将内容拆分为：

- `answer`：给用户展示的主回答。
- `factContent`：来自 MySQL 或 Neo4j 的事实内容。
- `supplementalContent`：模板或 LLM 生成的补充说明。
- `sources`：答案来源，包括来源类型、来源名称、事实文本和原始详情页链接。

LLM 不作为事实来源。当知识检索没有返回事实时，系统不会让 LLM 自由生成答案。

## 技术架构

```text
Web / App / 独立问答前端
        ↓
FastAPI 后端 /api/qa/ask
        ↓
意图识别
        ↓
objectId 解析与多轮上下文
        ↓
MySQL 文物属性查询 + Neo4j 图谱关系查询
        ↓
答案生成 + 来源标注 + 日志记录
        ↓
前端展示答案、事实、补充说明、来源和推荐文物
        ↓
用户反馈 /api/qa/feedback
        ↓
后台管理查看日志、反馈、失败问题、审核任务和统计结果
```

技术栈：

| 层次 | 技术 |
| --- | --- |
| 后端 | Python, FastAPI |
| 前端 | Vue, Vite, Axios |
| 业务数据库 | MySQL |
| 图数据库 | Neo4j |
| 图查询语言 | Cypher |
| 生成增强 | OpenAI-compatible LLM API，可配置关闭 |
| 接口风格 | RESTful API |
| 协作平台 | GitHub |

## objectId 统一标识

`objectId` 是本子系统跨 Web / App、MySQL、Neo4j、问答日志和用户反馈的统一文物标识。

实际解析优先级为：

1. 用户问题中明确识别出的唯一文物名称。
2. 请求体或 URL 传入的 `objectId`。
3. 用户问题中存在多个候选文物时，返回候选列表让用户选择。
4. `sessionId` 或 `conversationId` 对应的当前上下文文物。
5. 无法确定文物时，提示用户补充文物名称或从文物详情页进入问答页面。

其中，请求传入的 `objectId` 优先于旧会话上下文，因为 Web / App 从文物详情页跳转时代表用户当前正在查看的文物。

## 目录结构

```text
qa-subsystem/
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # API 路由
│   │   ├── core/             # 配置
│   │   ├── db/               # 数据库连接
│   │   ├── models/           # 主流程内部模型
│   │   ├── repositories/     # MySQL 数据访问
│   │   ├── schemas/          # 请求与响应模型
│   │   └── services/         # 问答主流程与业务服务
│   ├── tests/                # 后端自动化测试
│   ├── .env.example          # 环境变量示例
│   ├── README.md             # 后端运行说明
│   └── requirements.txt      # 后端依赖
├── frontend/                 # Vue 问答前端
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docs/
│   ├── api/                  # API 文档
│   ├── database/             # 数据库设计文档
│   ├── design/               # 模块设计文档
│   ├── development/          # Git 协作与 PR 审核规范
│   ├── integration/          # 与其他子系统集成文档和流程图
│   ├── meeting/              # 会议纪要
│   ├── project-plan/         # 项目管理计划
│   ├── test/                 # 测试用例与测试报告
│   └── user-manual.md        # 用户使用手册
├── scripts/
│   └── sql/                  # 建表 SQL
└── submission/               # 本地 AI 答辩提交整理包，已被 gitignore 忽略
```

## 快速启动

### 1. 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `backend/.env` 中填写本地数据库、Neo4j 和 LLM 配置。注意：`.env` 包含密钥，不能提交到 GitHub。

启动服务：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

访问：

- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

### 2. 启动前端

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

访问：

```text
http://127.0.0.1:5173/qa?objectId=1
```

如果后端地址不是 `http://localhost:8000`，可通过 `VITE_API_TARGET` 指定代理目标。

## 主要接口

### 问答接口

```text
POST /api/qa/ask
```

核心请求字段：

- `question`：用户问题。
- `objectId`：当前文物标识，可为空。
- `sessionId`：当前会话标识，用于多轮上下文。
- `userId`：可选，用户 ID。
- `sourceClient`：调用来源，如 `web`、`app`、`demo`。

核心响应字段：

- `qaLogId`：本轮问答日志 ID。
- `status`：回答状态，如 `answered`、`no_data`、`need_clarification`、`unsupported`。
- `intent`：识别到的问题意图。
- `answer`：主回答。
- `factContent`：事实内容。
- `supplementalContent`：补充说明。
- `resolvedObject`：解析出的文物对象。
- `sources`：答案来源。
- `relatedArtifacts`：相关文物推荐。

### 反馈接口

```text
POST /api/qa/feedback
```

用于记录“有帮助 / 不准确”反馈。不准确反馈会自动生成审核任务。

### 后台管理接口

```text
GET  /api/admin/qa/logs
GET  /api/admin/qa/feedback
GET  /api/admin/qa/failed-questions
GET  /api/admin/qa/review-tasks
POST /api/admin/qa/review-tasks/{id}/review
GET  /api/admin/qa/statistics/failure-types
GET  /api/admin/qa/statistics/inaccurate-types
```

完整接口说明见 [docs/api/qa-api.md](docs/api/qa-api.md)。

## 与其他子系统集成

本子系统已完成以下集成对接：

### 掌上博物馆 App 子系统

App 端通过文物详情页获取当前 `objectId`，调用 `/api/qa/ask` 获取问答结果，并调用 `/api/qa/feedback` 回传用户反馈。App 不需要直接访问 MySQL 或 Neo4j。

集成文档见 [docs/integration/app-integration-guide.md](docs/integration/app-integration-guide.md)。

### 知识图谱构建子系统

知识图谱构建子系统负责提供 Neo4j 图谱节点和关系。本系统通过 Neo4j Driver 查询 `Artifact`、`Museum`、`Dynasty`、`Artist` 等节点关系。

关键约定：

```text
Neo4j Artifact.object_id = MySQL artifacts.object_id = API objectId
```

集成文档见 [docs/integration/knowledge-graph-integration-guide.md](docs/integration/knowledge-graph-integration-guide.md)。

### 后台管理子系统

后台管理子系统通过 `/api/admin/qa/*` 接口查看问答日志、用户反馈、失败问题、审核任务和统计结果，并可处理“不准确”反馈生成的审核任务。

集成文档见 [docs/integration/admin-integration-guide.md](docs/integration/admin-integration-guide.md)。

## 团队分工

| 人员 | 角色 | 主要职责 |
| --- | --- | --- |
| 组长 | 后端主流程与系统集成 | FastAPI 框架、`/api/qa/ask`、统一响应、`objectId` 解析、模块集成、PR 审核、跨系统对接 |
| 成员 2 | MySQL 数据库与数据访问 | 7 张 `qa_` 表、MySQL 查询、日志、来源、失败问题记录 |
| 成员 3 | Neo4j 图谱查询与复杂问答 | Cypher 查询、收藏地、年代、作者、推荐、统计和多跳基础版 |
| 成员 4 | 意图识别、多轮上下文与答案生成 | 11 类意图、实体识别、回答模板、暂无数据兜底、多轮上下文 |
| 成员 5 | Vue 前端问答页面 | 问答页面、来源展示、推荐展示、反馈按钮、URL 接收 `objectId` |
| 成员 6 | 反馈审核、后台接口与测试文档 | `/api/qa/feedback`、审核任务、后台接口、统计接口、测试报告、用户手册 |

## 测试与质量验证

后端自动化测试：

```powershell
cd backend
python -m pytest tests
```

当前测试覆盖：

- 意图识别。
- 文物名称匹配和多候选澄清。
- `objectId` 解析优先级。
- MySQL 数据访问。
- Neo4j 查询回退。
- 知识检索。
- 答案生成。
- 日志记录。
- 反馈和后台管理服务。

前端构建检查：

```powershell
cd frontend
npm run build
```

最新验证结果：

```text
后端：38 passed
前端：build successful
```

详细测试说明见：

- [docs/test/test-cases.md](docs/test/test-cases.md)
- [docs/test/test-report.md](docs/test/test-report.md)

## 文档入口

| 文档 | 路径 |
| --- | --- |
| API 文档 | [docs/api/qa-api.md](docs/api/qa-api.md) |
| 用户使用手册 | [docs/user-manual.md](docs/user-manual.md) |
| 测试报告 | [docs/test/test-report.md](docs/test/test-report.md) |
| 项目管理计划 v0.4 | [docs/project-plan/知识问答子系统项目管理计划-v0.4.md](docs/project-plan/知识问答子系统项目管理计划-v0.4.md) |
| App 集成文档 | [docs/integration/app-integration-guide.md](docs/integration/app-integration-guide.md) |
| 知识图谱集成文档 | [docs/integration/knowledge-graph-integration-guide.md](docs/integration/knowledge-graph-integration-guide.md) |
| 后台管理集成文档 | [docs/integration/admin-integration-guide.md](docs/integration/admin-integration-guide.md) |
| Git 协作规范 | [docs/development/git-workflow.md](docs/development/git-workflow.md) |
| PR 审核清单 | [docs/development/review-checklist.md](docs/development/review-checklist.md) |
| 后端运行说明 | [backend/README.md](backend/README.md) |

## 安全与提交注意事项

- 不提交 `backend/.env`。
- 不提交真实数据库密码、Neo4j 密码和 LLM API Key。
- 不提交 `node_modules/`、`frontend/dist/`、`.venv/`、缓存目录和日志文件。
- AI 答辩平台提交包位于本地 `submission/` 目录，该目录已被 `.gitignore` 忽略。
- 对外共享接口时，应只提供接口地址、字段说明和测试用例，不提供密钥。

## 项目质量原则

1. 无事实不编造。
2. 事实内容与补充说明分开展示。
3. 每条可回答问题尽量提供来源。
4. MySQL 负责结构化属性，Neo4j 负责关系知识。
5. `objectId` 作为跨端、跨库、跨日志的统一文物标识。
6. `main` 分支保持可运行。
7. 跨子系统集成优先保持接口契约稳定。
