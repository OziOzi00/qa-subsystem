# Backend

FastAPI backend for the knowledge QA subsystem.

## Run Locally

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

Environment setup details are in `docs/development/environment-setup.md`.
Do not commit real database passwords in `.env` or documentation.

## Smoke Test

After the backend server is running:

```powershell
python ..\scripts\smoke_test_backend.py --base-url http://127.0.0.1:8000
```

If `MYSQL_DSN` is configured and the public database contains all `qa_` tables,
run the DB-backed checks:

```powershell
python ..\scripts\smoke_test_backend.py --base-url http://127.0.0.1:8000 --include-db
```

## Demo QA Request

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/api/qa/ask `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"question":"演示文物的材质是什么？","objectId":"DEMO_001","sourceClient":"demo"}'
```

The service returns demo data for `DEMO_001`, and real MySQL / Neo4j-backed
answers when the corresponding environment variables are configured.

## Optional LLM / RAG Configuration

The backend supports lightweight RAG generation through an OpenAI-compatible
chat completion API. Facts are still retrieved from MySQL / Neo4j; the LLM only
generates `supplementalContent`. If these variables are not configured, the
service automatically falls back to deterministic template text.

```powershell
LLM_ENABLED=true
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=<your-api-key>
LLM_TIMEOUT_SECONDS=20
```

## QA Pipeline Modules

`POST /api/qa/ask` is orchestrated by `app/services/qa_service.py`.

Pipeline modules:

- `intent_recognizer.py`: recognizes the question intent. Owned later by Member 4.
- `object_resolver.py`: resolves `object_id` from request and later entity/context data. Owned by the leader with Member 4 and Member 2.
- `knowledge_retriever.py`: calls MySQL and Neo4j query modules. Owned later by Member 2 and Member 3.
- `llm_client.py`: optional OpenAI-compatible LLM client for lightweight RAG supplemental generation.
- `answer_generator.py`: renders fact-based answers and supplemental content. Owned later by Member 4.
- `qa_logger.py`: writes `qa_log`, `qa_source_record`, and `qa_failed_question`. Owned later by Member 2.

The leader-owned orchestration layer should stay stable so frontend, App, and
other backend modules can integrate through one unified `/api/qa/ask` contract.

## object_id Resolution Rule

The QA subsystem uses `object_id` as the shared key across Web/App, MySQL,
Neo4j, QA logs, and feedback records.

Resolution priority:

1. Unique artifact name explicitly mentioned in the question.
2. `objectId` passed by URL/body, such as `/qa?objectId=MET_12345`.
3. Current object saved in `sessionId` or `conversationId` context.
4. If multiple artifacts are matched, return candidates for user selection.
5. If no object can be determined, ask the user to provide an artifact name or
   enter from an artifact detail page.

Request `objectId` intentionally has higher priority than old session context,
because a Web/App detail-page jump represents the user's current artifact.
