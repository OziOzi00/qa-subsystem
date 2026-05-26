from fastapi import APIRouter

from app.api.v1 import admin, feedback, health, qa

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(qa.router, prefix="/qa", tags=["qa"])
api_router.include_router(feedback.router, prefix="/qa", tags=["qa"])
api_router.include_router(admin.router, tags=["admin"])
