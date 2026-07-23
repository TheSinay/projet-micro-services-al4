"""Client for service-deliveries: courier assignment (saga continuation, T12)."""

from typing import Any

import httpx

from app.clients.base import check_response, correlation_headers

_EXPECTED_ASSIGN = frozenset({200, 201})


class DeliveriesClient:
    """Async client for the delivery assignment endpoint."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def request_delivery(
        self,
        order_id: str,
        pickup_address: dict[str, Any],
        dropoff_address: dict[str, Any],
        user_id: str | None = None,
    ) -> str | None:
        """``POST /api/v1/deliveries`` — returns the delivery id, or None when no
        courier is available (409, retried later by the continuation handler).

        ``user_id`` is forwarded so deliveries can echo it in its ``delivery.*`` events,
        letting the notifications service reach the client without an extra lookup.
        """
        response = await self._http.post(
            f"{self._base_url}/api/v1/deliveries",
            json={
                "order_id": order_id,
                "user_id": user_id,
                "pickup_address": pickup_address,
                "dropoff_address": dropoff_address,
            },
            headers=correlation_headers(),
        )
        if response.status_code == 409:
            return None
        check_response("deliveries", response, _EXPECTED_ASSIGN)
        return str(response.json()["id"])
