from datetime import datetime
from decimal import Decimal

from app.core.database import execute, fetch_all, fetch_one


def _serialize_row(row: dict) -> dict:
    """Convert non-JSON-serializable types (datetime, Decimal) to plain types."""
    result = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat()
        elif isinstance(v, Decimal):
            result[k] = float(v)
        elif isinstance(v, bytes):
            result[k] = v.decode("utf-8")
        else:
            result[k] = v
    return result


def _build_paginated_response(
    rows: list[tuple],
    col_names: list[str],
    total: int,
    page: int,
    page_size: int,
) -> tuple[list[dict], int]:
    items = [_serialize_row(dict(zip(col_names, row))) for row in rows]
    return items, total


class AdminService:
    """Admin management queries for QA subsystem data."""

    async def query_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        intent: str | None = None,
        keyword: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        values: list = []

        if status:
            conditions.append("l.status = %s")
            values.append(status)
        if intent:
            conditions.append("l.intent = %s")
            values.append(intent)
        if keyword:
            conditions.append("(l.question LIKE %s OR l.answer LIKE %s)")
            kw = f"%{keyword}%"
            values.extend([kw, kw])
        if start_time:
            conditions.append("l.created_at >= %s")
            values.append(start_time)
        if end_time:
            conditions.append("l.created_at <= %s")
            values.append(end_time)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        row = await fetch_one(f"SELECT COUNT(*) FROM qa_log l {where}", *values)
        total = row[0] if row else 0

        offset = (page - 1) * page_size
        sql = (
            f"SELECT l.id, l.qa_log_uuid, l.session_id, l.user_id,"
            f" l.question, l.intent, l.intent_confidence,"
            f" l.status, l.answer, l.object_id,"
            f" l.resolve_source, l.source_client,"
            f" l.latency_ms, l.created_at"
            f" FROM qa_log l {where}"
            f" ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
        )
        rows = await fetch_all(sql, *(values + [page_size, offset]))

        cols = [
            "id", "qa_log_uuid", "session_id", "user_id",
            "question", "intent", "intent_confidence",
            "status", "answer", "object_id",
            "resolve_source", "source_client",
            "latency_ms", "created_at",
        ]
        return _build_paginated_response(rows, cols, total, page, page_size)

    async def query_feedback(
        self,
        page: int = 1,
        page_size: int = 20,
        feedback_type: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        values: list = []

        if feedback_type:
            conditions.append("f.feedback_type = %s")
            values.append(feedback_type)
        if keyword:
            conditions.append("f.comment LIKE %s")
            values.append(f"%{keyword}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        row = await fetch_one(f"SELECT COUNT(*) FROM qa_feedback f {where}", *values)
        total = row[0] if row else 0

        offset = (page - 1) * page_size
        sql = (
            f"SELECT f.id, f.qa_log_id, f.user_id,"
            f" f.feedback_type, f.comment, f.source_client, f.created_at"
            f" FROM qa_feedback f {where}"
            f" ORDER BY f.created_at DESC LIMIT %s OFFSET %s"
        )
        rows = await fetch_all(sql, *(values + [page_size, offset]))

        cols = [
            "id", "qa_log_id", "user_id",
            "feedback_type", "comment", "source_client", "created_at",
        ]
        return _build_paginated_response(rows, cols, total, page, page_size)

    async def query_failed_questions(
        self,
        page: int = 1,
        page_size: int = 20,
        failure_type: str | None = None,
        status: str | None = None,
        intent: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        values: list = []

        if failure_type:
            conditions.append("q.failure_type = %s")
            values.append(failure_type)
        if status:
            conditions.append("q.status = %s")
            values.append(status)
        if intent:
            conditions.append("q.intent = %s")
            values.append(intent)
        if keyword:
            conditions.append("q.question LIKE %s")
            values.append(f"%{keyword}%")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        row = await fetch_one(
            f"SELECT COUNT(*) FROM qa_failed_question q {where}", *values
        )
        total = row[0] if row else 0

        offset = (page - 1) * page_size
        sql = (
            f"SELECT q.id, q.qa_log_id, q.session_id, q.user_id,"
            f" q.question, q.intent, q.failure_type,"
            f" q.object_id, q.error_detail, q.status, q.created_at"
            f" FROM qa_failed_question q {where}"
            f" ORDER BY q.created_at DESC LIMIT %s OFFSET %s"
        )
        rows = await fetch_all(sql, *(values + [page_size, offset]))

        cols = [
            "id", "qa_log_id", "session_id", "user_id",
            "question", "intent", "failure_type",
            "object_id", "error_detail", "status", "created_at",
        ]
        return _build_paginated_response(rows, cols, total, page, page_size)

    async def query_review_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        task_status: str | None = None,
        review_result: str | None = None,
    ) -> tuple[list[dict], int]:
        conditions: list[str] = []
        values: list = []

        if task_status:
            conditions.append("t.task_status = %s")
            values.append(task_status)
        if review_result:
            conditions.append("t.review_result = %s")
            values.append(review_result)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        row = await fetch_one(
            f"SELECT COUNT(*) FROM qa_review_task t {where}", *values
        )
        total = row[0] if row else 0

        offset = (page - 1) * page_size
        sql = (
            f"SELECT t.id, t.feedback_id, t.qa_log_id,"
            f" t.task_status, t.review_result, t.priority,"
            f" t.reviewer_admin_id, t.review_comment,"
            f" t.corrected_answer, t.created_at, t.updated_at, t.reviewed_at"
            f" FROM qa_review_task t {where}"
            f" ORDER BY t.created_at DESC LIMIT %s OFFSET %s"
        )
        rows = await fetch_all(sql, *(values + [page_size, offset]))

        cols = [
            "id", "feedback_id", "qa_log_id",
            "task_status", "review_result", "priority",
            "reviewer_admin_id", "review_comment",
            "corrected_answer", "created_at", "updated_at", "reviewed_at",
        ]
        return _build_paginated_response(rows, cols, total, page, page_size)

    async def review_task(
        self,
        task_id: int,
        review_result: str,
        review_comment: str | None,
        reviewer_id: int,
    ) -> bool:
        updated = await execute(
            """UPDATE qa_review_task SET
               task_status = 'done',
               review_result = %s,
               review_comment = %s,
               reviewer_admin_id = %s,
               reviewed_at = NOW(),
               updated_at = NOW()
               WHERE id = %s""",
            review_result,
            review_comment,
            reviewer_id,
            task_id,
        )
        return updated > 0

    async def statistics_failure_types(
        self,
    ) -> list[dict]:
        """Count failed questions grouped by failure_type, ordered by frequency."""
        rows = await fetch_all(
            """SELECT failure_type, COUNT(*) AS cnt
               FROM qa_failed_question
               GROUP BY failure_type
               ORDER BY cnt DESC"""
        )
        return [
            {"failureType": row[0], "count": row[1]} for row in rows
        ]

    async def statistics_inaccurate_types(
        self,
    ) -> list[dict]:
        """Count inaccurate feedback grouped by the original question's intent."""
        rows = await fetch_all(
            """SELECT l.intent, COUNT(*) AS cnt
               FROM qa_feedback f
               JOIN qa_log l ON l.id = f.qa_log_id
               WHERE f.feedback_type = 'inaccurate'
               GROUP BY l.intent
               ORDER BY cnt DESC"""
        )
        return [
            {"intent": row[0], "count": row[1]} for row in rows
        ]


admin_service = AdminService()
