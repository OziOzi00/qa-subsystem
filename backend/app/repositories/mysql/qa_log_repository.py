import json
from typing import Protocol

from app.schemas.qa import AnswerSource


class ExecuteClient(Protocol):
    def execute(
        self,
        sql: str,
        params: tuple[object, ...] | None = None,
    ) -> int: ...


class QALogRepository:
    def __init__(self, client: ExecuteClient) -> None:
        self._client = client

    def insert_log(self, payload: dict[str, object]) -> int:
        return self._client.execute(
            """
            INSERT INTO qa_log (
                qa_log_uuid,
                session_id,
                conversation_id,
                user_id,
                request_object_id,
                question,
                normalized_question,
                intent,
                intent_confidence,
                intent_detail_json,
                status,
                answer,
                fact_content,
                supplemental_content,
                artifact_id,
                object_id,
                resolve_source,
                candidates_json,
                source_client,
                retrieval_raw_json,
                error_message
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s
            )
            """,
            (
                payload["qa_log_uuid"],
                payload.get("session_id"),
                payload.get("conversation_id"),
                payload.get("user_id"),
                payload.get("request_object_id"),
                payload["question"],
                payload.get("normalized_question"),
                payload.get("intent"),
                payload.get("intent_confidence"),
                _json_or_none(payload.get("intent_detail_json")),
                payload["status"],
                payload.get("answer"),
                payload.get("fact_content"),
                payload.get("supplemental_content"),
                payload.get("artifact_id"),
                payload.get("object_id"),
                payload.get("resolve_source"),
                _json_or_none(payload.get("candidates_json")),
                payload.get("source_client"),
                _json_or_none(payload.get("retrieval_raw_json")),
                payload.get("error_message"),
            ),
        )

    def insert_source(self, qa_log_id: int, source: AnswerSource) -> None:
        self._client.execute(
            """
            INSERT INTO qa_source_record (
                qa_log_id,
                source_type,
                source_name,
                source_table,
                source_record_id,
                artifact_id,
                object_id,
                detail_url,
                fact_text,
                source_payload_json,
                confidence
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s
            )
            """,
            (
                qa_log_id,
                source.source_type.value,
                source.source_name,
                None,
                None,
                None,
                None,
                source.detail_url,
                source.fact_text,
                _json_or_none(source.model_dump(mode="json", by_alias=True)),
                source.confidence,
            ),
        )


def _json_or_none(value: object) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)
