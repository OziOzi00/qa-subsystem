from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.feedback import FeedbackRequest, FeedbackType
from app.services.admin_service import AdminService
from app.services.feedback_service import FeedbackService


class FakeClient:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.feedback_id = 21
        self.review_id = 31

    def fetch_one(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, object] | None:
        if "COUNT(*) AS total" in sql:
            return {"total": 2}
        if "FROM qa_log" in sql:
            return {"id": 11}
        return None

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, object]]:
        if "FROM qa_failed_question" in sql and "GROUP BY" in sql:
            return [{"failureType": "no_data", "count": 3}]
        if "FROM qa_feedback f" in sql and "GROUP BY" in sql:
            return [{"intent": "artifact_museum", "count": 4}]
        return [
            {
                "id": 1,
                "qa_log_uuid": str(uuid4()),
                "question": "演示问题",
                "status": "answered",
                "intent": "artifact_museum",
                "created_at": None,
            }
        ]

    def execute(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> int:
        self.executed.append((sql, params))
        if "INSERT INTO qa_feedback" in sql:
            return self.feedback_id
        if "INSERT INTO qa_review_task" in sql:
            return self.review_id
        return 1


def test_feedback_service_creates_review_task_for_inaccurate_feedback() -> None:
    client = FakeClient()
    service = FeedbackService(client=client)
    qa_log_id = uuid4()

    response = _run(
        service.submit(
            FeedbackRequest(
                qaLogId=qa_log_id,
                feedbackType=FeedbackType.INACCURATE,
                comment="答案不准确",
                sourceClient="pytest",
            )
        )
    )

    assert response.feedback_id == 21
    assert response.qa_log_id == str(qa_log_id)
    assert response.review_task_created is True
    assert any("INSERT INTO qa_review_task" in sql for sql, _ in client.executed)


def test_admin_service_returns_paginated_logs() -> None:
    service = AdminService(client=FakeClient())

    items, total = _run(service.query_logs(page=1, page_size=10))

    assert total == 2
    assert items[0]["question"] == "演示问题"


def test_feedback_endpoint_rejects_invalid_payload() -> None:
    client = TestClient(app)

    response = client.post("/api/qa/feedback", json={})

    assert response.status_code == 422


def test_admin_endpoint_is_registered() -> None:
    client = TestClient(app)

    response = client.get("/api/admin/qa/logs")

    assert response.status_code in {200, 503}


def _run(coro):
    import asyncio

    return asyncio.run(coro)
