import os
from typing import Protocol
from uuid import UUID, uuid4

from app.models.qa_pipeline import QAPipelineContext
from app.db.mysql import MySQLClient, MySQLConfig
from app.repositories.mysql.qa_log_repository import QALogRepository
from app.schemas.qa import AnswerStatus


class LogRepository(Protocol):
    def insert_log(self, payload: dict[str, object]) -> int: ...

    def insert_source(self, qa_log_id: int, source) -> None: ...


class QALogger:
    """Write QA logs and failed-question records.

    The current implementation only returns a generated ID. Member 2 can replace
    this with `qa_log`, `qa_source_record`, and `qa_failed_question` writes.
    """

    def __init__(self, repository: LogRepository | None = None) -> None:
        self._repository = repository

    async def record(self, context: QAPipelineContext) -> UUID:
        qa_log_id = uuid4()
        if self._repository is None:
            return qa_log_id

        try:
            row_id = self._repository.insert_log(
                self._build_log_payload(context, qa_log_id)
            )
            if context.retrieval is not None:
                for source in context.retrieval.sources:
                    self._repository.insert_source(row_id, source)
        except Exception:
            return qa_log_id
        return qa_log_id

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

    def _build_log_payload(
        self,
        context: QAPipelineContext,
        qa_log_id: UUID,
    ) -> dict[str, object]:
        intent = context.intent
        retrieval = context.retrieval
        generated_answer = context.generated_answer
        resolved_object = context.resolved_object

        intent_detail = None
        if intent is not None:
            intent_detail = {
                "matchedKeywords": intent.matched_keywords,
                "entities": intent.entities,
                "confidence": intent.confidence,
            }

        return {
            "qa_log_uuid": str(qa_log_id),
            "session_id": context.session_id,
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "request_object_id": context.object_id,
            "question": context.question,
            "normalized_question": context.question,
            "intent": intent.intent if intent else None,
            "intent_confidence": intent.confidence if intent else None,
            "intent_detail_json": intent_detail,
            "status": generated_answer.status.value if generated_answer else "error",
            "answer": generated_answer.answer if generated_answer else None,
            "fact_content": generated_answer.fact_content if generated_answer else None,
            "supplemental_content": (
                generated_answer.supplemental_content if generated_answer else None
            ),
            "artifact_id": _artifact_id_from_raw(retrieval.raw if retrieval else {}),
            "object_id": resolved_object.object_id if resolved_object else None,
            "resolve_source": resolved_object.resolve_source if resolved_object else None,
            "candidates_json": resolved_object.candidates if resolved_object else [],
            "source_client": context.source_client,
            "retrieval_raw_json": retrieval.raw if retrieval else None,
            "error_message": None,
        }


def _artifact_id_from_raw(raw: dict[str, object]) -> int | None:
    artifact_id = raw.get("artifactId")
    if artifact_id is None:
        return None
    try:
        return int(artifact_id)
    except (TypeError, ValueError):
        return None


def _build_default_logger() -> QALogger:
    mysql_dsn = os.getenv("MYSQL_DSN")
    if not mysql_dsn:
        return QALogger()
    try:
        client = MySQLClient(MySQLConfig.from_dsn(mysql_dsn))
    except ValueError:
        return QALogger()
    return QALogger(repository=QALogRepository(client))


qa_logger = _build_default_logger()
