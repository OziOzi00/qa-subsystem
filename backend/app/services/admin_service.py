from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status

from app.db.mysql import MySQLClient, MySQLConfig, get_mysql_dsn


def _serialize_value(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _serialize_value(value) for key, value in row.items()}


class AdminService:
    """Admin management queries for QA logs, feedback, failures, and reviews."""

    def __init__(self, client: MySQLClient | None = None) -> None:
        self._client = client

    def _get_client(self) -> MySQLClient:
        if self._client is not None:
            return self._client

        mysql_dsn = get_mysql_dsn()
        if not mysql_dsn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MYSQL_DSN 未配置，后台问答管理接口暂不可用。",
            )
        try:
            self._client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MYSQL_DSN 配置无效，后台问答管理接口暂不可用。",
            ) from exc
        return self._client

    async def query_logs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        intent: str | None = None,
        keyword: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        values: list[object] = []

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

        return self._query_paginated(
            table_sql="qa_log l",
            select_sql=(
                "l.id, l.qa_log_uuid, l.session_id, l.user_id, l.question, "
                "l.intent, l.intent_confidence, l.status, l.answer, l.object_id, "
                "l.resolve_source, l.source_client, l.latency_ms, l.created_at"
            ),
            conditions=conditions,
            values=values,
            order_sql="l.created_at DESC",
            page=page,
            page_size=page_size,
        )

    async def query_feedback(
        self,
        page: int = 1,
        page_size: int = 20,
        feedback_type: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        values: list[object] = []

        if feedback_type:
            conditions.append("f.feedback_type = %s")
            values.append(feedback_type)
        if keyword:
            conditions.append("f.comment LIKE %s")
            values.append(f"%{keyword}%")

        return self._query_paginated(
            table_sql="qa_feedback f",
            select_sql=(
                "f.id, f.qa_log_id, f.user_id, f.feedback_type, "
                "f.comment, f.source_client, f.created_at"
            ),
            conditions=conditions,
            values=values,
            order_sql="f.created_at DESC",
            page=page,
            page_size=page_size,
        )

    async def query_failed_questions(
        self,
        page: int = 1,
        page_size: int = 20,
        failure_type: str | None = None,
        status: str | None = None,
        intent: str | None = None,
        keyword: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        values: list[object] = []

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

        return self._query_paginated(
            table_sql="qa_failed_question q",
            select_sql=(
                "q.id, q.qa_log_id, q.session_id, q.user_id, q.question, "
                "q.intent, q.failure_type, q.object_id, q.error_detail, "
                "q.status, q.created_at"
            ),
            conditions=conditions,
            values=values,
            order_sql="q.created_at DESC",
            page=page,
            page_size=page_size,
        )

    async def query_review_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        task_status: str | None = None,
        review_result: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[str] = []
        values: list[object] = []

        if task_status:
            conditions.append("t.task_status = %s")
            values.append(task_status)
        if review_result:
            conditions.append("t.review_result = %s")
            values.append(review_result)

        return self._query_paginated(
            table_sql="qa_review_task t",
            select_sql=(
                "t.id, t.feedback_id, t.qa_log_id, t.task_status, "
                "t.review_result, t.priority, t.assigned_admin_id, "
                "t.reviewer_admin_id, t.review_comment, t.corrected_answer, "
                "t.created_at, t.updated_at, t.reviewed_at"
            ),
            conditions=conditions,
            values=values,
            order_sql="t.created_at DESC",
            page=page,
            page_size=page_size,
        )

    async def review_task(
        self,
        task_id: int,
        review_result: str,
        review_comment: str | None,
        reviewer_id: int,
    ) -> bool:
        client = self._get_client()
        existing = client.fetch_one(
            "SELECT id FROM qa_review_task WHERE id = %s",
            (task_id,),
        )
        if existing is None:
            return False

        client.execute(
            """
            UPDATE qa_review_task SET
                task_status = 'done',
                review_result = %s,
                review_comment = %s,
                reviewer_admin_id = %s,
                reviewed_at = NOW(),
                updated_at = NOW()
            WHERE id = %s
            """,
            (review_result, review_comment, reviewer_id, task_id),
        )
        return True

    async def statistics_failure_types(self) -> list[dict[str, Any]]:
        rows = self._get_client().fetch_all(
            """
            SELECT failure_type AS failureType, COUNT(*) AS count
            FROM qa_failed_question
            GROUP BY failure_type
            ORDER BY count DESC
            """
        )
        return [_serialize_row(row) for row in rows]

    async def statistics_inaccurate_types(self) -> list[dict[str, Any]]:
        rows = self._get_client().fetch_all(
            """
            SELECT COALESCE(l.intent, 'unknown') AS intent, COUNT(*) AS count
            FROM qa_feedback f
            JOIN qa_log l ON l.id = f.qa_log_id
            WHERE f.feedback_type = 'inaccurate'
            GROUP BY COALESCE(l.intent, 'unknown')
            ORDER BY count DESC
            """
        )
        return [_serialize_row(row) for row in rows]

    def _query_paginated(
        self,
        table_sql: str,
        select_sql: str,
        conditions: list[str],
        values: list[object],
        order_sql: str,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""
        client = self._get_client()

        count_row = client.fetch_one(
            f"SELECT COUNT(*) AS total FROM {table_sql} {where_sql}",
            tuple(values),
        )
        total = int(count_row["total"]) if count_row else 0

        offset = (page - 1) * page_size
        rows = client.fetch_all(
            f"""
            SELECT {select_sql}
            FROM {table_sql}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            tuple(values + [page_size, offset]),
        )
        return [_serialize_row(row) for row in rows], total


admin_service = AdminService()
