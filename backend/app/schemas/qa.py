from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AnswerStatus(StrEnum):
    ANSWERED = "answered"
    NO_DATA = "no_data"
    NEED_CLARIFICATION = "need_clarification"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class SourceType(StrEnum):
    MYSQL = "mysql"
    NEO4J = "neo4j"
    LLM = "llm"
    TEMPLATE = "template"


class AskRequest(BaseModel):
    """Unified request body for the question answering entry point."""

    model_config = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=1, max_length=1000)
    object_id: str | None = Field(default=None, alias="objectId")
    session_id: str | None = Field(default=None, alias="sessionId")
    user_id: int | None = Field(default=None, alias="userId")
    conversation_id: str | None = Field(default=None, alias="conversationId")
    source_client: str | None = Field(
        default=None,
        alias="sourceClient",
        description="Caller client, such as web, app, or demo.",
    )


class ResolvedObject(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    object_id: str | None = Field(default=None, alias="objectId")
    title: str | None = None
    resolve_source: str = Field(alias="resolveSource")
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class AnswerSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_type: SourceType = Field(alias="sourceType")
    source_name: str = Field(alias="sourceName")
    detail_url: str | None = Field(default=None, alias="detailUrl")
    fact_text: str | None = Field(default=None, alias="factText")
    confidence: float | None = Field(default=None, ge=0, le=1)


class RelatedArtifact(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    object_id: str = Field(alias="objectId")
    title: str
    reason: str | None = None
    image_url: str | None = Field(default=None, alias="imageUrl")


class AskResponse(BaseModel):
    """Unified response body for all QA answers."""

    model_config = ConfigDict(populate_by_name=True)

    qa_log_id: UUID = Field(default_factory=uuid4, alias="qaLogId")
    session_id: str | None = Field(default=None, alias="sessionId")
    status: AnswerStatus
    intent: str | None = None
    answer: str
    fact_content: str | None = Field(default=None, alias="factContent")
    supplemental_content: str | None = Field(default=None, alias="supplementalContent")
    resolved_object: ResolvedObject = Field(alias="resolvedObject")
    sources: list[AnswerSource] = Field(default_factory=list)
    related_artifacts: list[RelatedArtifact] = Field(
        default_factory=list,
        alias="relatedArtifacts",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    need_feedback: bool = Field(default=True, alias="needFeedback")
    debug: dict[str, Any] | None = None
