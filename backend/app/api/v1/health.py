from fastapi import APIRouter

from app.core.config import is_database_configured, settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        environment=settings.ENVIRONMENT,
        databaseConfigured=is_database_configured(),
    )
