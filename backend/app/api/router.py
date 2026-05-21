from fastapi import APIRouter

from app.api.v1 import health, qa

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(qa.router, prefix="/qa", tags=["qa"])
