"""Schema for the /health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response consumed by the load balancer / docker-compose."""

    status: str
    service: str
