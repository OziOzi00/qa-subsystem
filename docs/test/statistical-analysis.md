# 知识问答子系统 — 高频失败/不准确问题统计分析报告

| 版本 | 日期 | 编制人 |
|---|---|---|
| v0.1 | 2026-05-25 | 成员 6 |
| v0.2 | 2026-06-01 | 组长 |

---

## 1. 概述

本报告基于知识问答子系统中的 `qa_failed_question` 和 `qa_feedback` 表数据，对高频失败问题类型和高频不准确反馈进行统计分析，以发现问答系统的薄弱环节，指导后续优化方向。

### 1.1 数据来源

| 统计项 | 数据表 | 统计口径 |
|---|---|---|
| 高频失败问题类型 | `qa_failed_question.failure_type` | 按 `failure_type` 分组计数 |
| 高频不准确问题类型 | `qa_feedback` + `qa_log` | 筛选 `feedback_type = 'inaccurate'`，按原始问题的 `intent` 分组计数 |

### 1.2 API 接口

- `GET /api/admin/qa/statistics/failure-types`
- `GET /api/admin/qa/statistics/inaccurate-types`

---

## 2. 当前数据状态

> 截至 2026-06-01，系统已经完成反馈、审核任务和统计接口链路。当前公共库中的数据主要来自开发联调和演示测试，不代表真实用户生产数据。

### 2.1 高频失败问题类型统计

| failure_type | 出现次数 | 占比 | 建议优先级 |
|---|---|---|---|
| `no_data` / `unsupported` / `need_clarification` 等 | 以统计接口实时结果为准 | — | 按出现频率排序 |

**说明：** 失败问题已由 `qa_logger` 写入 `qa_failed_question`，后台可通过 `GET /api/admin/qa/statistics/failure-types` 实时查看各失败类型分布。由于当前测试数据量很小，文档不固定写死统计数字，最终演示以前应以接口返回结果为准。

### 2.2 高频不准确问题类型统计

| intent（原始问题意图） | 出现次数 | 占比 | 建议优先级 |
|---|---|---|---|
| 各问答意图 | 以统计接口实时结果为准 | — | 按出现频率排序 |

**说明：** `inaccurate` 类型反馈已可写入 `qa_feedback`，并自动生成 `qa_review_task`。后台可通过 `GET /api/admin/qa/statistics/inaccurate-types` 查看不准确反馈对应的高频意图。

> **注：** 测试期间已成功验证统计接口的完整链路（反馈提交 → 审核任务生成 → 统计数据可查询），确认数据流正确。

---

## 3. 预期常见失败类型（上线后参考）

根据系统设计，以下为预期的常见失败类型：

| failure_type | 含义 | 可能原因 |
|---|---|---|
| `intent_not_recognized` | 意图无法识别 | 用户问题不在 11 类支持范围内，或问法表达不清晰 |
| `no_data_found` | 知识库无相关数据 | 该文物或关系尚未录入数据库 |
| `object_not_resolved` | 文物对象无法确定 | 问题中未提及文物名，且无上下文或传入 object_id |
| `ambiguous_entity` | 识别到多个候选文物 | 用户使用了过于通用的名称 |
| `database_error` | 数据库查询异常 | MySQL 或 Neo4j 连接故障 |
| `timeout` | 查询超时 | 复杂查询或数据库负载过高 |

当前代码中实际写入的失败类型主要包括：

| failure_type | 触发场景 |
|---|---|
| `no_data` | MySQL / Neo4j 无检索结果 |
| `need_clarification` | 缺少文物对象或需要用户选择候选 |
| `unsupported` | 意图不在当前支持范围内 |
| `retrieval_error` | 检索阶段异常 |
| `generation_error` | 回答生成阶段异常 |

## 4. 使用建议

### 4.1 后台管理人员

1. **定期查看**两个统计接口（建议每周），识别高频失败/不准确类型
2. 对于集中出现的同一失败类型，优先排查数据完整性或意图识别规则
3. 对于高频不准确反馈，通过审核任务流程闭环处理

### 4.2 开发团队

1. 成员 4 可根据失败问题分布调整意图识别规则和问法模板
2. 成员 2 和成员 3 可根据分布补充 MySQL 和 Neo4j 数据
3. 成员 6 的审核任务机制为质量改进提供流程支撑

---

## 5. 附录

### 5.1 接口使用示例

```powershell
# 查询高频失败类型
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/admin/qa/statistics/failure-types

# 查询高频不准确类型
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/admin/qa/statistics/inaccurate-types
```

### 5.2 数据字典

**qa_failed_question.failure_type** 取值：

| 值 | 含义 |
|---|---|
| `intent_not_recognized` | 意图无法识别 |
| `no_data_found` | 暂无相关数据 |
| `object_not_resolved` | 无法确定文物对象 |
| `ambiguous_entity` | 识别到多个候选 |
| `database_error` | 数据库查询异常 |
| `timeout` | 查询超时 |
| `retrieval_error` | 检索阶段异常 |
| `generation_error` | 回答生成阶段异常 |
