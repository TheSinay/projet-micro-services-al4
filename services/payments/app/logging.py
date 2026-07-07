"""Structured JSON logging (structlog) and X-Correlation-Id middleware."""

import logging
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from structlog.typing import FilteringBoundLogger

CORRELATION_ID_HEADER = "X-Correlation-Id"

logger: FilteringBoundLogger = structlog.get_logger("app")


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog to emit JSON log lines enriched with contextvars."""
    level = logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Bind a correlation id to every request.

    The id is read from the ``X-Correlation-Id`` request header (generated if absent),
    bound to the structlog context, echoed back in the response header and logged.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = correlation_id
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
