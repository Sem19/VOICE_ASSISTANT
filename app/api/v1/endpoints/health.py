"""Health check endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import __version__
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response payload."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=__version__,
        environment=settings.app_env,
        timestamp=datetime.now(tz=UTC),
    )
