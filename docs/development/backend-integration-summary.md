# 知识问答后端集成说明

本文档总结当前后端主线的模块边界、调用流程和后续联调重点，方便成员五前端接入和最终答辩说明。

## 1. 当前主线状态

后端主线已完成以下能力：

- FastAPI 基础框架；
- `/api/qa/ask` 问答主接口；
- 统一请求 / 响应模型；
- `object_id` 解析和会话上下文；
- MySQL 文物基础信息查询、日志、来源、失败问题记录；
- Neo4j 图谱查询和复杂问答基础版；
- 意图识别、实体抽取、最近 5 轮上下文、回答模板；
- 可配置轻量 RAG 补充生成，未配置 LLM 时模板回退；
- 用户反馈、审核任务、后台管理接口；
- pytest 自动化测试和接口联调用例。

## 2. 主流程

```text
用户输入问题
→ /api/qa/ask
→ IntentRecognizer 识别意图和实体
→ ObjectResolver 解析 object_id
→ KnowledgeRetriever 查询 MySQL / Neo4j
→ AnswerGenerator 生成回答，并在配置 LLM 时生成 RAG 补充说明
→ QALogger 写入 qa_log / qa_source_record / qa_failed_question
→ 返回答案、来源、推荐文物、debug 信息
```

用户反馈流程：

```text
前端读取 qaLogId
→ POST /api/qa/feedback
→ 写入 qa_feedback
→ 若 feedbackType=inaccurate，则生成 qa_review_task
→ 后台接口查看和处理审核任务
```

## 3. object_id 优先级

当前主线明确采用以下优先级：

1. 问题中明确识别出的唯一文物名称；
2. 请求体或 URL 传入的 `objectId`；
3. `sessionId` / `conversationId` 中保存的当前文物；
4. 多候选时返回候选列表；
5. 无法确定时返回补充文物名称提示。

这里将 URL / 请求参数中的 `objectId` 放在旧会话上下文之前，是为了适配 Web / App 从文物详情页跳转问答页的真实语境。

## 4. 模块边界

| 模块 | 文件 | 职责 |
|---|---|---|
| 主流程 | `app/services/qa_service.py` | 编排意图、对象解析、检索、生成、日志 |
| 意图识别 | `app/services/intent_recognizer.py` | 11 类简单问答、复杂问答实体抽取 |
| 对象解析 | `app/services/object_resolver.py` | `objectId` 优先级和候选文物处理 |
| 上下文 | `app/services/session_context.py` | 当前文物和最近 5 轮问答 |
| MySQL | `app/db/mysql.py`, `app/repositories/mysql/*` | 公共库查询和 qa_ 表写入 |
| Neo4j | `app/services/knowledge_retriever.py` | 图谱关系和复杂问答 |
| LLM 补充生成 | `app/services/llm_client.py` | OpenAI 兼容接口，可选启用，生成 supplementalContent |
| 回答生成 | `app/services/answer_generator.py` | 回答模板、RAG 补充和暂无数据兜底 |
| 反馈后台 | `app/services/feedback_service.py`, `app/services/admin_service.py` | 反馈、审核任务、统计接口 |

## 5. 前端接入字段

成员五重点使用 `/api/qa/ask` 返回字段：

- `qaLogId`：反馈接口必传；
- `status`：`answered/no_data/need_clarification/unsupported/error`；
- `intent`：问题类型；
- `answer`：直接展示给用户的回答；
- `factContent`：来自 MySQL / Neo4j 的事实内容；
- `supplementalContent`：模板或可配置大模型补充说明；
- `resolvedObject`：当前文物对象；
- `sources`：答案来源；
- `relatedArtifacts`：推荐文物；
- `debug.entities`：复杂问答实体，联调时使用；
- `debug.recentContext`：最近 5 轮上下文，联调时使用。

## 6. 当前剩余工作

- 使用真实文物 `object_id` 做 MySQL / Neo4j 联调；
- 校验成员三 Cypher 与实际图谱 schema 是否完全一致；
- 准备固定演示样例，覆盖 MySQL、Neo4j、统计问答、反馈和 RAG 回退；
- 若取得 LLM API Key，在 `.env` 中配置 `LLM_API_KEY` 并验证补充生成；
- 准备最终演示数据和答辩脚本。
