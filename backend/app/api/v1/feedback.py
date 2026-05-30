from fastapi import APIRouter

from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import feedback_service

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    """Submit user feedback (helpful / inaccurate) for a QA log entry."""
    return await feedback_service.submit(payload)
