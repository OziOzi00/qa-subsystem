from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackType(StrEnum):
    HELPFUL = "helpful"
    INACCURATE = "inaccurate"


class FeedbackRequest(BaseModel):
    """Request body for submitting QA feedback."""

    model_config = {"populate_by_name": True}

    qa_log_id: UUID = Field(alias="qaLogId")
    user_id: int | None = Field(default=None, alias="userId")
    feedback_type: FeedbackType = Field(alias="feedbackType")
    comment: str | None = Field(default=None, max_length=2000)
    source_client: str | None = Field(default=None, alias="sourceClient")


class FeedbackResponse(BaseModel):
    """Response after feedback is recorded."""

    model_config = {"populate_by_name": True}

    feedback_id: int = Field(alias="feedbackId")
    qa_log_id: str = Field(alias="qaLogId")
    review_task_created: bool = Field(alias="reviewTaskCreated")
    message: str = "反馈已记录。"
