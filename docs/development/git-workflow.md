# 知识问答子系统 Git 协作与模块接入规范

版本：v0.1  
适用对象：知识问答子系统 6 名成员  
目标：保证第 14 周前可独立运行 Demo，第 16 周前能稳定对接 Web、App、知识图谱和后台管理子系统。

## 1. 协作原则

1. `main` 分支保持可运行状态。
2. 每个成员在自己的功能分支开发，通过 Pull Request 合并。
3. 不直接修改他人负责模块，确需修改时在 PR 描述中说明原因。
4. `/api/qa/ask` 的请求和响应格式以 [qa-api.md](../api/qa-api.md) 为准。
5. `objectId` 是跨 MySQL、Neo4j、Web/App、日志和反馈的统一文物标识，不得自行改名或另建平行字段。
6. 对暂无数据的问题必须返回“暂无相关数据”或 `no_data` 状态，不能生成没有依据的答案。
7. 事实内容和补充描述必须分开：事实放入 `factContent`，模板或大模型补充放入 `supplementalContent`。

## 2. 分支命名

分支命名格式：

```text
feature/member-{编号}-{模块}
fix/member-{编号}-{问题}
docs/member-{编号}-{文档}
```

示例：

```text
feature/member-2-mysql-access
feature/member-3-neo4j-query
feature/member-4-intent-context
feature/member-5-vue-qa-page
feature/member-6-feedback-api
docs/member-6-test-report
fix/member-3-cypher-period-query
```

组长分支可使用：

```text
feature/leader-qa-orchestration
fix/leader-api-contract
docs/leader-integration-plan
```

## 3. 提交信息

提交信息格式：

```text
类型(模块): 简短说明
```

常用类型：

| 类型 | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修复问题 |
| `docs` | 文档 |
| `test` | 测试 |
| `refactor` | 不改变行为的重构 |
| `chore` | 配置、依赖、脚本等 |

示例：

```text
feat(mysql): add artifact detail query methods
feat(neo4j): add same dynasty artifact query
feat(intent): support 11 simple QA intents
feat(frontend): add source display panel
fix(api): keep ask response field names stable
docs(test): add QA smoke test cases
```

## 4. 模块边界

### 4.1 组长负责模块

主要路径：

```text
backend/app/main.py
backend/app/api/
backend/app/schemas/
backend/app/models/qa_pipeline.py
backend/app/services/qa_service.py
backend/app/services/object_resolver.py
docs/api/
```

职责：

1. `/api/qa/ask` 主流程编排。
2. 统一请求和响应格式。
3. `objectId` 解析优先级。
4. 后端模块集成。
5. 其他成员 PR 审核。

其他成员如需修改上述文件，应先说明修改原因，避免破坏统一接口。

### 4.2 成员 2：MySQL 与日志模块

建议路径：

```text
backend/app/db/
backend/app/repositories/mysql/
backend/app/services/mysql_*.py
backend/app/services/qa_logger.py
docs/database/
scripts/sql/
```

接入点：

1. 在 `knowledge_retriever.py` 中接入文物详情、材质、类型、介绍、尺寸、作者生平等查询。
2. 在 `qa_logger.py` 中实现 `qa_log`、`qa_source_record`、`qa_failed_question` 写入。
3. 提供 `objectId` 到 MySQL `artifacts` 表记录的查询方法。

注意：

1. 新增 7 张 `qa_` 表时，SQL 必须放入 `scripts/sql/` 或 `docs/database/`。
2. 不重复创建公共基础表。
3. 写入来源记录时应能追溯到原始详情页链接。

### 4.3 成员 3：Neo4j 与复杂问答模块

建议路径：

```text
backend/app/repositories/neo4j/
backend/app/services/neo4j_*.py
docs/design/
docs/database/
```

接入点：

1. 在 `knowledge_retriever.py` 中接入收藏地、年代、作者、同作者作品、同朝代文物、相关文物推荐。
2. 为统计类和简单多跳复杂问答提供查询方法。
3. 输出 Cypher 查询模板和图谱 schema 说明。

注意：

1. Neo4j 节点中的 `Artifact.object_id` 必须与 MySQL `artifacts.object_id` 对齐。
2. 查询结果必须能转换为 `sources` 和 `factContent`。
3. 图谱无结果时返回 `no_data`，不能让答案生成模块猜测。

### 4.4 成员 4：意图识别、多轮上下文与答案生成

主要路径：

```text
backend/app/services/intent_recognizer.py
backend/app/services/answer_generator.py
backend/app/services/session_context.py
docs/requirements/
docs/design/
```

接入点：

1. 扩展 11 类简单问答意图识别。
2. 实现文物名称识别，并配合成员 2 匹配 `objectId`。
3. 实现最近 5 轮上下文、代词指代和话题切换。
4. 完善回答模板和暂无数据兜底话术。

注意：

1. 不能把无数据问题改写成看似确定的答案。
2. 多候选文物必须返回候选列表让用户选择。
3. 大模型补充内容必须放入 `supplementalContent`。

### 4.5 成员 5：Vue 前端问答页面

建议路径：

```text
frontend/
docs/api/
```

接入点：

1. 调用 `/api/qa/ask`。
2. 从 URL 读取 `objectId`，例如 `/qa?objectId=MET_12345`。
3. 展示 `answer`、`sources`、`factContent`、`supplementalContent`、`relatedArtifacts`。
4. 展示候选文物列表。
5. 调用 `/api/qa/feedback`。

注意：

1. 不要在前端自行拼接事实答案。
2. `no_data` 状态直接展示后端提示。
3. 子系统独立检查时必须提供手动输入或选择演示文物入口。

### 4.6 成员 6：反馈审核、后台接口与测试文档

建议路径：

```text
backend/app/api/v1/feedback.py
backend/app/api/v1/admin_qa.py
backend/app/services/feedback_service.py
docs/test/
docs/meeting/
```

接入点：

1. 维护 `/api/qa/feedback`。
2. 维护后台管理接口和统计接口。
3. 对“不准确”反馈生成 `qa_review_task`。
4. 编写测试用例、测试报告、用户手册。

注意：

1. `feedbackType=inaccurate` 必须生成审核任务。
2. 后台接口修改审核状态时应记录处理结果。
3. 测试用例必须覆盖 11 类简单问答、暂无数据、来源展示和反馈。

## 5. 开发流程

1. 从最新 `main` 创建自己的分支。

```powershell
git checkout main
git pull
git checkout -b feature/member-2-mysql-access
```

2. 在负责模块内开发。
3. 本地运行最小检查。

后端检查：

```powershell
cd backend
python -m compileall app
```

如果改动了接口，启动服务检查：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端检查由成员 5 根据实际 Vue 项目脚本补充，例如：

```powershell
npm install
npm run dev
npm run build
```

4. 更新相关文档。
5. 提交并推送分支。

```powershell
git add .
git commit -m "feat(mysql): add artifact detail query methods"
git push -u origin feature/member-2-mysql-access
```

6. 在 GitHub 创建 Pull Request。
7. 组长审核通过后合并。

## 6. PR 描述模板

创建 PR 时建议填写：

```text
## 本次改动

- 

## 影响范围

- 

## 自测结果

- [ ] python -m compileall app
- [ ] /api/health 可访问
- [ ] /api/qa/ask 基础问题可返回
- [ ] 已更新相关文档

## 是否修改接口

- [ ] 否
- [ ] 是，已同步更新 docs/api/qa-api.md

## 需要组长重点审核

- 
```

## 7. 合并规则

1. 不允许直接推送到 `main`。
2. PR 至少由组长审核一次。
3. 修改 `/api/qa/ask` schema、`objectId` 规则、数据库表结构、公共配置时，必须在 PR 描述中单独说明。
4. 第 14 周检查前，任何影响 Demo 启动的修改必须先在本地跑通。
5. 第 16 周集成阶段，优先保证接口稳定，非必要不做大规模重构。

## 8. 常见冲突处理

1. 如果多人修改同一文件，优先按模块边界拆回各自负责文件。
2. 如果必须修改主流程文件 `qa_service.py`，先在群里说明原因。
3. 如果接口字段需要变更，先改文档，再改代码，再通知前端和 App 对接成员。
4. 如果数据库字段与公共数据库不一致，成员 2 先整理差异文档，再决定兼容方案。
5. 如果 Neo4j schema 与预期不一致，成员 3 提供实际 schema 示例，组长再调整主流程接入。

## 9. 第 14 周前集成优先级

优先完成：

1. `/api/qa/ask` 可以回答主要基础问题。
2. MySQL 和 Neo4j 至少各有一批真实数据查询接入。
3. 前端页面可以输入问题、展示答案和来源。
4. `no_data`、多候选、反馈入口可演示。
5. Demo 启动步骤清楚。

暂缓：

1. 完整开放闲聊。
2. 大规模复杂推理。
3. 非必要 UI 动效。
4. 不影响检查的重构。
