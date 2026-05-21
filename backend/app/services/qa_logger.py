from uuid import UUID, uuid4

from app.models.qa_pipeline import QAPipelineContext
from app.schemas.qa import AnswerStatus


class QALogger:
    """Write QA logs and failed-question records.

    The current implementation only returns a generated ID. Member 2 can replace
    this with `qa_log`, `qa_source_record`, and `qa_failed_question` writes.
    """

    async def record(self, context: QAPipelineContext) -> UUID:
        return uuid4()

    async def record_failed_if_needed(self, context: QAPipelineContext) -> None:
        """Placeholder for future failed-question persistence."""
        if context.generated_answer is None:
            return
        if context.generated_answer.status not in {
            AnswerStatus.NO_DATA,
            AnswerStatus.NEED_CLARIFICATION,
            AnswerStatus.UNSUPPORTED,
            AnswerStatus.ERROR,
        }:
            return
        # Member 2 will persist these cases into qa_failed_question.


qa_logger = QALogger()
