"""Schema for the health check endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response of ``GET /health`` (used by load balancer / Docker healthchecks)."""

    status: str
    service: str
