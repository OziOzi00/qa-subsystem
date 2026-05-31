import os
from functools import cached_property

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Knowledge QA Subsystem"
    API_VERSION: str = "0.1.0"
    API_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"

    BACKEND_CORS_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        description="Comma-separated list of allowed CORS origins.",
    )

    MYSQL_DSN: str | None = None
    NEO4J_URI: str | None = None
    NEO4J_USER: str | None = None
    NEO4J_PASSWORD: str | None = None

    LLM_API_KEY: str | None = None
    LLM_BASE_URL: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: int = 20
    LLM_ENABLED: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @cached_property
    def cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
        return [origin for origin in origins if origin]


settings = Settings()


def is_database_configured() -> bool:
    return bool(os.getenv("MYSQL_DSN") or settings.MYSQL_DSN) and bool(
        os.getenv("NEO4J_URI") or settings.NEO4J_URI
    )
