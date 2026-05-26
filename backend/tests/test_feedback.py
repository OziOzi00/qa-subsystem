"""Pytest tests for the feedback endpoint.

Requires the server running on http://127.0.0.1:8000.
"""
import pytest


class TestFeedbackEndpoint:
    """POST /api/qa/feedback"""

    def test_helpful_feedback(self, client, new_qa_log_uuid):
        """TC-FB-001: Submit helpful feedback successfully."""
        payload = {
            "qaLogId": new_qa_log_uuid,
            "feedbackType": "helpful",
            "sourceClient": "web",
        }
        r = client.post("/qa/feedback", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["feedbackId"] > 0
        assert data["reviewTaskCreated"] is False
        assert data["qaLogId"] == new_qa_log_uuid

    def test_inaccurate_feedback_creates_review_task(self, client, new_qa_log_uuid, valid_user_id):
        """TC-FB-002: Inaccurate feedback auto-creates a review task."""
        payload = {
            "qaLogId": new_qa_log_uuid,
            "userId": valid_user_id,
            "feedbackType": "inaccurate",
            "comment": "答案不正确，博物馆名称错误。",
            "sourceClient": "demo",
        }
        r = client.post("/qa/feedback", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["reviewTaskCreated"] is True, (
            "Inaccurate feedback should create a review task"
        )

    def test_invalid_feedback_type_rejected(self, client, new_qa_log_uuid):
        """TC-FB-003: Invalid feedback_type returns 422."""
        payload = {
            "qaLogId": new_qa_log_uuid,
            "feedbackType": "invalid",
        }
        r = client.post("/qa/feedback", json=payload)
        assert r.status_code == 422

    def test_missing_required_fields(self, client):
        """TC-FB-004: Empty body returns 422."""
        r = client.post("/qa/feedback", json={})
        assert r.status_code == 422

    def test_feedback_with_comment(self, client, new_qa_log_uuid):
        """Feedback with a lengthy comment should still succeed."""
        payload = {
            "qaLogId": new_qa_log_uuid,
            "feedbackType": "inaccurate",
            "comment": "这件文物的收藏博物馆实际为大英博物馆。",
            "sourceClient": "web",
        }
        r = client.post("/qa/feedback", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["reviewTaskCreated"] is True
