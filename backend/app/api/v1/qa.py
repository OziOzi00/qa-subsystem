from fastapi import APIRouter

from app.schemas.qa import AskRequest, AskResponse
from app.services.qa_service import qa_service

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask_question(payload: AskRequest) -> AskResponse:
    return await qa_service.ask(payload)
