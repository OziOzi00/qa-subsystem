"""Pytest tests for admin endpoints.

Requires the server running on http://127.0.0.1:8000.
"""
import pytest


class TestAdminLogs:
    """GET /api/admin/qa/logs"""

    def test_default_pagination(self, client):
        """TC-ADM-LOG-001: Default pagination returns valid structure."""
        r = client.get("/admin/qa/logs", params={"page": 1, "pageSize": 10})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert data["page"] == 1
        assert data["pageSize"] == 10
        assert data["totalPages"] >= 1

    def test_filter_by_intent(self, client):
        """TC-ADM-LOG-002: Filter by intent parameter."""
        r = client.get("/admin/qa/logs", params={"intent": "artifact_museum"})
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["intent"] == "artifact_museum"

    def test_keyword_search(self, client):
        """TC-ADM-LOG-003: Keyword search in question/answer."""
        r = client.get("/admin/qa/logs", params={"keyword": "演示"})
        assert r.status_code == 200

    def test_time_range_filter(self, client):
        """TC-ADM-LOG-004: startTime and endTime filter."""
        r = client.get(
            "/admin/qa/logs",
            params={"startTime": "2026-01-01", "endTime": "2026-12-31"},
        )
        assert r.status_code == 200


class TestAdminFeedback:
    """GET /api/admin/qa/feedback"""

    def test_default_pagination(self, client):
        """TC-ADM-FB-001: Default pagination."""
        r = client.get("/admin/qa/feedback", params={"page": 1, "pageSize": 10})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_filter_by_type(self, client):
        """TC-ADM-FB-002: Filter by feedbackType."""
        r = client.get(
            "/admin/qa/feedback", params={"feedbackType": "inaccurate"}
        )
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["feedback_type"] == "inaccurate"


class TestAdminFailedQuestions:
    """GET /api/admin/qa/failed-questions"""

    def test_default_pagination(self, client):
        """TC-ADM-FQ-001: Default pagination."""
        r = client.get(
            "/admin/qa/failed-questions", params={"page": 1, "pageSize": 10}
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data


class TestAdminReviewTasks:
    """GET /api/admin/qa/review-tasks"""

    def test_default_pagination(self, client):
        """TC-ADM-RT-001: Default pagination."""
        r = client.get(
            "/admin/qa/review-tasks", params={"page": 1, "pageSize": 10}
        )
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

    def test_filter_by_status(self, client):
        """TC-ADM-RT-002: Filter by taskStatus."""
        r = client.get(
            "/admin/qa/review-tasks", params={"taskStatus": "pending"}
        )
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["task_status"] == "pending"


class TestAdminReview:
    """POST /api/admin/qa/review-tasks/{id}/review"""

    def _first_pending_task_id(self, client) -> int | None:
        """Helper: return the first pending review task id, or None."""
        r = client.get(
            "/admin/qa/review-tasks", params={"taskStatus": "pending"}
        )
        items = r.json().get("items", [])
        return items[0]["id"] if items else None

    def test_approve_review(self, client, valid_admin_id):
        """TC-ADM-RV-001: Approve a review task."""
        task_id = self._first_pending_task_id(client)
        if task_id is None:
            pytest.skip("No pending review task available")

        payload = {
            "reviewResult": "approved",
            "reviewComment": "已确认反馈有效。",
            "reviewerId": valid_admin_id,
        }
        r = client.post(f"/admin/qa/review-tasks/{task_id}/review", json=payload)
        assert r.status_code == 200
        assert r.json()["reviewResult"] == "approved"

    def test_reject_nonexistent_task(self, client):
        """TC-ADM-RV-002: Returns 404 for non-existent task."""
        payload = {
            "reviewResult": "approved",
            "reviewerId": 1,
        }
        r = client.post("/admin/qa/review-tasks/99999/review", json=payload)
        assert r.status_code == 404
        assert "不存在" in r.json()["detail"]

    def test_review_result_rejected(self, client, valid_admin_id):
        """TC-ADM-RV-003: Reject a review task."""
        task_id = self._first_pending_task_id(client)
        if task_id is None:
            pytest.skip("No pending review task available")

        payload = {
            "reviewResult": "rejected",
            "reviewComment": "反馈与数据一致，无需修改。",
            "reviewerId": valid_admin_id,
        }
        r = client.post(f"/admin/qa/review-tasks/{task_id}/review", json=payload)
        assert r.status_code == 200
        assert r.json()["reviewResult"] == "rejected"


class TestStatistics:
    """GET /api/admin/qa/statistics/*"""

    def test_failure_types(self, client):
        """TC-STAT-001: Failure type statistics return valid structure."""
        r = client.get("/admin/qa/statistics/failure-types")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_inaccurate_types(self, client):
        """TC-STAT-002: Inaccurate type statistics return valid structure."""
        r = client.get("/admin/qa/statistics/inaccurate-types")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
