from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ReviewResult(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    FIXED = "fixed"


class PaginatedResponse(BaseModel):
    """Common paginated list response."""

    model_config = {"populate_by_name": True}

    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")


class ReviewTaskActionRequest(BaseModel):
    """Request body for reviewing a review task."""

    model_config = {"populate_by_name": True}

    review_result: ReviewResult = Field(alias="reviewResult")
    review_comment: str | None = Field(default=None, alias="reviewComment")
    reviewer_id: int = Field(alias="reviewerId")
