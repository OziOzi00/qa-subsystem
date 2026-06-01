# 知识问答子系统 Pull Request 审核清单

版本：v0.1  
主要使用者：组长  
目标：保证队友分支合并后不破坏第 14 周 Demo 和第 16 周集成。

## 1. 通用检查

- [ ] PR 分支命名符合规范。
- [ ] PR 描述说明了本次改动、影响范围和自测结果。
- [ ] 没有提交 `.env`、本地数据库密码、缓存、虚拟环境等文件。
- [ ] 没有无关格式化或大面积重构。
- [ ] 没有覆盖他人模块的改动，或已说明必要原因。
- [ ] 新增接口、字段、数据库表时已更新对应文档。

## 2. API 契约检查

- [ ] `/api/qa/ask` 请求字段与 [qa-api.md](../api/qa-api.md) 一致。
- [ ] 响应字段仍包含 `qaLogId`、`status`、`intent`、`answer`、`resolvedObject`、`sources`。
- [ ] `objectId` 字段命名没有被改成其他形式。
- [ ] `status` 只使用约定值：`answered`、`no_data`、`need_clarification`、`unsupported`、`error`。
- [ ] `no_data` 场景不会生成无依据答案。
- [ ] 多候选文物返回 `resolvedObject.candidates`，而不是随机选一个。
- [ ] 来源信息可追溯，至少包含 `sourceType` 和 `sourceName`，有原始链接时包含 `detailUrl`。

## 3. 后端模块检查

### 3.1 组长主流程

- [ ] `qa_service.py` 仍保持“意图识别 -> objectId 解析 -> 检索 -> 答案生成 -> 日志 -> 响应”的主流程。
- [ ] 新模块通过服务接口接入，没有在路由层堆业务逻辑。
- [ ] 异常不会直接暴露数据库密码、连接串等敏感信息。

### 3.2 成员 2 MySQL 与日志

- [ ] 查询公共基础表时使用 `object_id` 做主要关联。
- [ ] 没有重复创建文物、用户、博物馆等公共基础表。
- [ ] `qa_log` 能记录问题、答案、状态、意图和时间。
- [ ] `qa_source_record` 能记录答案来源。
- [ ] `qa_failed_question` 能记录无法回答、无数据或识别失败问题。
- [ ] SQL 文件包含字段说明或配套数据库文档。

### 3.3 成员 3 Neo4j 查询

- [ ] Cypher 查询与实际图谱 schema 匹配。
- [ ] `Artifact.object_id` 与 MySQL `artifacts.object_id` 对齐。
- [ ] 查询结果能转成 `factContent`、`sources` 或 `relatedArtifacts`。
- [ ] 无查询结果时返回 `no_data`。
- [ ] 复杂问答基础版没有牺牲基础问答稳定性。

### 3.4 成员 4 意图与答案

- [ ] 覆盖 11 类简单问答意图。
- [ ] 常见问法不会被明显误判。
- [ ] 多轮上下文最多保留最近 5 轮。
- [ ] “它”“该文物”等代词指代使用当前上下文。
- [ ] 用户切换文物时上下文会更新。
- [ ] 回答生成区分事实内容和补充描述；启用 LLM 时只生成 `supplementalContent`，不编造事实。
- [ ] 暂无数据话术明确，不含猜测性描述。

### 3.5 成员 5 前端页面

- [ ] 可以从 URL 读取 `objectId`。
- [ ] 可以独立演示时手动输入或选择演示文物。
- [ ] 可以展示答案、来源、原始链接、推荐文物。
- [ ] 可以展示多候选文物并让用户选择。
- [ ] 可以提交“有帮助 / 不准确”反馈。
- [ ] 页面在后端返回 `no_data` 或 `need_clarification` 时不会崩溃。

### 3.6 成员 6 反馈、后台与测试

- [ ] `/api/qa/feedback` 校验 `qaLogId`。
- [ ] `helpful` 和 `inaccurate` 都能写入反馈表。
- [ ] `inaccurate` 会生成审核任务。
- [ ] 后台查询接口支持分页或基本筛选。
- [ ] 测试用例覆盖基础问答、暂无数据、来源展示、反馈和审核任务。
- [ ] 用户手册包含子系统独立演示步骤。

## 4. 文档检查

- [ ] API 改动同步更新 `docs/api/qa-api.md`。
- [ ] 数据库改动同步更新 `docs/database/`。
- [ ] 架构或流程改动同步更新 `docs/design/`。
- [ ] 测试相关内容同步更新 `docs/test/`。
- [ ] 会议或阶段材料同步放入 `docs/meeting/`。

## 5. 本地检查命令

后端至少运行：

```powershell
cd backend
python -m compileall app
```

如果 PR 修改了接口或主流程，建议再运行：

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

并手动访问：

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

前端至少运行：

```powershell
cd frontend
npm run build
```

如需调试其他后端端口，可临时指定代理目标：

```powershell
$env:VITE_API_TARGET="http://127.0.0.1:8001"
npm run dev -- --host 127.0.0.1 --port 5173
```

## 6. 不建议合并的情况

- [ ] 破坏 `/api/qa/ask` 统一响应格式。
- [ ] 无数据时生成了编造答案。
- [ ] 改动了 `objectId` 关联规则但未说明原因。
- [ ] 引入真实数据库账号、密码或私有连接串。
- [ ] 后端无法启动或基础编译检查不通过。
- [ ] 大量修改他人模块且没有沟通说明。
- [ ] 前端依赖后端未实现字段，且没有兼容处理。
- [ ] LLM 或数据库密钥被写入仓库文件。

## 7. 第 14 周前审核重点

1. 是否能支撑可独立运行 Demo。
2. 是否能展示答案来源和原始链接。
3. 是否能在无数据时稳定返回 `no_data`。
4. 是否保留 Web / App 通过 `objectId` 对接的能力。
5. 是否会影响其他成员继续并行开发。

## 8. 第 16 周前审核重点

1. 与 Web、App、后台、知识图谱组的接口是否稳定。
2. 数据库和图数据库的 `objectId` 是否一致。
3. 日志、反馈、审核任务是否能追溯。
4. 文档和演示材料是否与实际系统一致。
5. 是否避免在集成阶段引入非必要大改。
