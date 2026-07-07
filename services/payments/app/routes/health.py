"""Health check endpoint, mounted at the root (outside /api/v1)."""

from fastapi import APIRouter, Request

from app.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    settings: Settings = request.app.state.settings
    return HealthResponse(status="ok", service=settings.service_name)
