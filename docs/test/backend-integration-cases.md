# 后端接口联调用例

本文档给成员五前端、组长联调和最终演示使用。默认后端地址为 `http://127.0.0.1:8000`。

## 1. 健康检查

```http
GET /api/health
```

期望：

```json
{
  "status": "ok"
}
```

## 2. 11 类简单问答

### 2.1 材质

```json
{
  "question": "演示文物的材质是什么？",
  "objectId": "DEMO_001",
  "sessionId": "demo-session",
  "sourceClient": "demo"
}
```

期望：`intent=artifact_material`，`status=answered`。

### 2.2 尺寸多轮追问

先发送 2.1，再发送：

```json
{
  "question": "它的尺寸是多少？",
  "sessionId": "demo-session",
  "sourceClient": "demo"
}
```

期望：后端从会话上下文解析 `objectId=DEMO_001`，`intent=artifact_dimensions`。

### 2.3 其他简单问答示例

| 问题 | 期望意图 |
|---|---|
| `这件文物收藏在哪里？` | `artifact_museum` |
| `这件文物是什么朝代的？` | `artifact_period` |
| `这件文物属于什么类型？` | `artifact_type` |
| `介绍一下这件文物` | `artifact_description` |
| `这幅画的作者是谁？` | `artifact_artist` |
| `作者生平是什么？` | `artist_biography` |
| `同一作者还有哪些作品？` | `same_artist_artifacts` |
| `同一朝代还有哪些文物？` | `same_dynasty_artifacts` |
| `推荐相关文物` | `related_artifacts` |

## 3. 复杂问答基础版

### 3.1 某博物馆收藏数量

```json
{
  "question": "大英博物馆收藏了多少件中国文物？",
  "sourceClient": "demo"
}
```

期望：

- `intent=statistics_count`
- `debug.entities.museum=大英博物馆`
- 若 Neo4j 有数据则 `answered`，否则 `no_data`

### 3.2 收藏某类型最多的博物馆

```json
{
  "question": "收藏瓷器最多的博物馆是哪个？",
  "sourceClient": "demo"
}
```

期望：

- `intent=statistics_top_museum`
- `debug.entities.artifact_type=瓷器`

### 3.3 博物馆所在城市

```json
{
  "question": "大英博物馆位于哪个城市？",
  "sourceClient": "demo"
}
```

期望：

- `intent=museum_city`
- `debug.entities.museum=大英博物馆`

## 4. 用户反馈

前端从 `/api/qa/ask` 响应中读取 `qaLogId`，再提交：

```json
{
  "qaLogId": "<qaLogId>",
  "feedbackType": "inaccurate",
  "comment": "答案不准确，请人工审核。",
  "sourceClient": "web"
}
```

期望：

- `feedbackId` 为数字；
- `reviewTaskCreated=true`；
- 后台审核任务列表可以查到对应记录。

## 5. 后台接口

| 方法 | 地址 | 用途 |
|---|---|---|
| GET | `/api/admin/qa/logs?page=1&pageSize=10` | 查看问答日志 |
| GET | `/api/admin/qa/feedback?page=1&pageSize=10` | 查看反馈 |
| GET | `/api/admin/qa/failed-questions?page=1&pageSize=10` | 查看失败问题 |
| GET | `/api/admin/qa/review-tasks?page=1&pageSize=10` | 查看审核任务 |
| POST | `/api/admin/qa/review-tasks/{task_id}/review` | 处理审核任务 |
| GET | `/api/admin/qa/statistics/failure-types` | 失败问题类型统计 |
| GET | `/api/admin/qa/statistics/inaccurate-types` | 不准确反馈意图统计 |

## 6. 自动冒烟测试

启动后端后运行：

```powershell
python scripts/smoke_test_backend.py --base-url http://127.0.0.1:8000
```

若后端已配置 MySQL 且 `qa_` 表存在，可运行完整检查：

```powershell
python scripts/smoke_test_backend.py --base-url http://127.0.0.1:8000 --include-db
```
