from uuid import UUID

from fastapi import HTTPException, status

from app.db.mysql import MySQLClient, MySQLConfig, get_mysql_dsn
from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackType


class FeedbackService:
    """Handle user feedback and inaccurate-answer review tasks."""

    def __init__(self, client: MySQLClient | None = None) -> None:
        self._client = client

    async def submit(self, request: FeedbackRequest) -> FeedbackResponse:
        client = self._get_client()
        qa_log_pk = self._resolve_qa_log_id(client, request.qa_log_id)
        feedback_id = self._insert_feedback(client, qa_log_pk, request)

        review_task_created = False
        if request.feedback_type == FeedbackType.INACCURATE:
            self._insert_review_task(client, feedback_id, qa_log_pk)
            review_task_created = True

        return FeedbackResponse(
            feedbackId=feedback_id,
            qaLogId=str(request.qa_log_id),
            reviewTaskCreated=review_task_created,
        )

    def _get_client(self) -> MySQLClient:
        if self._client is not None:
            return self._client

        mysql_dsn = get_mysql_dsn()
        if not mysql_dsn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MYSQL_DSN 未配置，反馈接口暂不可用。",
            )
        try:
            self._client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MYSQL_DSN 配置无效，反馈接口暂不可用。",
            ) from exc
        return self._client

    def _resolve_qa_log_id(self, client: MySQLClient, qa_log_uuid: UUID) -> int:
        row = client.fetch_one(
            "SELECT id FROM qa_log WHERE qa_log_uuid = %s",
            (str(qa_log_uuid),),
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到对应问答日志，无法提交反馈。",
            )
        return int(row["id"])

    def _insert_feedback(
        self,
        client: MySQLClient,
        qa_log_pk: int,
        request: FeedbackRequest,
    ) -> int:
        return client.execute(
            """
            INSERT INTO qa_feedback
                (qa_log_id, user_id, feedback_type, comment, source_client, created_at)
            VALUES
                (%s, %s, %s, %s, %s, NOW())
            """,
            (
                qa_log_pk,
                request.user_id,
                request.feedback_type.value,
                request.comment,
                request.source_client,
            ),
        )

    def _insert_review_task(
        self,
        client: MySQLClient,
        feedback_id: int,
        qa_log_pk: int,
    ) -> None:
        client.execute(
            """
            INSERT INTO qa_review_task
                (feedback_id, qa_log_id, task_status, priority, created_at, updated_at)
            VALUES
                (%s, %s, 'pending', 1, NOW(), NOW())
            """,
            (feedback_id, qa_log_pk),
        )


feedback_service = FeedbackService()
