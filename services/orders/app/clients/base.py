"""Shared plumbing for the downstream HTTP clients.

Every outgoing call propagates the ``X-Correlation-Id`` bound by the middleware
(structlog contextvars), so a single id traces an order across all services.
Downstream answers are translated into two exception families:

- :class:`app.services.resilience.TransientDownstreamError` on 5xx — retryable;
- :class:`DownstreamClientError` on unexpected 4xx — never retried.
"""

import structlog
from httpx import Response

from app.logging import CORRELATION_ID_HEADER
from app.services.resilience import TransientDownstreamError


class DownstreamClientError(Exception):
    """An unexpected 4xx from a downstream service (never retried)."""

    def __init__(self, service: str, status_code: int, detail: str) -> None:
        self.service = service
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"{service} answered {status_code}: {detail}")


def correlation_headers() -> dict[str, str]:
    """Headers propagating the current request's correlation id (if bound)."""
    correlation_id = structlog.contextvars.get_contextvars().get("correlation_id")
    if correlation_id is None:
        return {}
    return {CORRELATION_ID_HEADER: str(correlation_id)}


def check_response(service: str, response: Response, expected: frozenset[int]) -> None:
    """Raise the right exception family unless the status code is expected."""
    if response.status_code in expected:
        return
    detail = _safe_detail(response)
    if response.status_code >= 500:
        raise TransientDownstreamError(f"{service} answered {response.status_code}: {detail}")
    raise DownstreamClientError(service, response.status_code, detail)


def _safe_detail(response: Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:200]
    if isinstance(body, dict) and "detail" in body:
        return str(body["detail"])
    return str(body)[:200]
