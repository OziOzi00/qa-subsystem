from uuid import UUID

from app.core.database import execute, fetch_one, insert_and_get_id
from app.schemas.feedback import FeedbackRequest, FeedbackResponse, FeedbackType


class FeedbackService:
    """Handle user feedback submission and review task generation."""

    async def submit(self, request: FeedbackRequest) -> FeedbackResponse:
        qa_log_pk = await self._resolve_qa_log_id(request.qa_log_id)
        feedback_id = await self._insert_feedback(qa_log_pk, request)

        review_task_created = False
        if request.feedback_type == FeedbackType.INACCURATE:
            await execute(
                """INSERT INTO qa_review_task
                   (feedback_id, qa_log_id, task_status, priority, created_at, updated_at)
                   VALUES (%s, %s, 'pending', 1, NOW(), NOW())""",
                feedback_id,
                qa_log_pk,
            )
            review_task_created = True

        return FeedbackResponse(
            feedbackId=feedback_id,
            qaLogId=str(request.qa_log_id),
            reviewTaskCreated=review_task_created,
        )

    async def _resolve_qa_log_id(self, qa_log_uuid: UUID) -> int:
        """Look up qa_log.id by UUID; insert a minimal record if missing."""
        row = await fetch_one(
            "SELECT id FROM qa_log WHERE qa_log_uuid = %s",
            str(qa_log_uuid),
        )
        if row:
            return row[0]

        # Insert a minimal log record when the real logger (member 2)
        # hasn't written one yet.  ON DUPLICATE KEY UPDATE makes this
        # safe regardless of execution order — if member 2's record or a
        # previous placeholder already exists, we just retrieve its id.
        return await insert_and_get_id(
            """INSERT INTO qa_log
               (qa_log_uuid, question, status, created_at)
               VALUES (%s, '', 'no_data', NOW())
               ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)""",
            str(qa_log_uuid),
        )

    async def _insert_feedback(
        self,
        qa_log_pk: int,
        request: FeedbackRequest,
    ) -> int:
        return await insert_and_get_id(
            """INSERT INTO qa_feedback
               (qa_log_id, user_id, feedback_type, comment, source_client, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            qa_log_pk,
            request.user_id,
            request.feedback_type.value,
            request.comment,
            request.source_client,
        )


feedback_service = FeedbackService()
