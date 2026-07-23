"""Client for service-payments: charge (saga step 3) and refund (compensation).

The charge endpoint is idempotent per ``order_id`` downstream (201 on creation,
200 when replayed), which is precisely what makes the retry policy safe: a retry
after a timeout whose request actually succeeded never debits the client twice.
"""

import httpx

from app.clients.base import check_response, correlation_headers

_EXPECTED_CHARGE = frozenset({200, 201})
_EXPECTED_REFUND = frozenset({201})


class PaymentsClient:
    """Async client for the payment endpoints used by the orchestrator."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def create_payment(self, order_id: str, amount: float) -> str:
        """``POST /api/v1/payments`` — returns the payment id (502 PSP -> transient)."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/payments",
            json={"order_id": order_id, "amount": amount},
            headers=correlation_headers(),
        )
        check_response("payments", response, _EXPECTED_CHARGE)
        return str(response.json()["id"])

    async def refund(self, payment_id: str, amount: float, reason: str) -> None:
        """``POST /api/v1/payments/{id}/refunds`` — total refund compensation."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/payments/{payment_id}/refunds",
            json={"amount": amount, "reason": reason},
            headers=correlation_headers(),
        )
        check_response("payments", response, _EXPECTED_REFUND)
