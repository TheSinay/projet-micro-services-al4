"""Client for service-restaurants: order validation and kitchen tickets (saga steps 2 and 4)."""

from dataclasses import dataclass, field

import httpx

from app.clients.base import check_response, correlation_headers
from app.repositories.entities import CartItem

_EXPECTED_VALIDATION = frozenset({200})
_EXPECTED_TICKET = frozenset({201})


@dataclass
class ValidationVerdict:
    """Business verdict of ``POST /order-validations`` (always HTTP 200 downstream)."""

    valid: bool
    subtotal: float | None = None
    reasons: list[str] = field(default_factory=list)


class RestaurantsClient:
    """Async client for the two restaurant endpoints used by the orchestrator."""

    def __init__(self, http: httpx.AsyncClient, base_url: str) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")

    async def validate_order(
        self, restaurant_id: str, items: list[CartItem]
    ) -> ValidationVerdict:
        """Saga step 2 — ``POST /api/v1/restaurants/{id}/order-validations``.

        An unknown restaurant (404) is reported as an invalid verdict instead of an
        exception: for the orchestrator both cases mean "cancel, nothing to refund".
        """
        response = await self._http.post(
            f"{self._base_url}/api/v1/restaurants/{restaurant_id}/order-validations",
            json={
                "items": [
                    {
                        "menu_item_id": item.menu_item_id,
                        "unit_price": item.unit_price,
                        "quantity": item.quantity,
                    }
                    for item in items
                ]
            },
            headers=correlation_headers(),
        )
        if response.status_code == 404:
            return ValidationVerdict(valid=False, reasons=["restaurant inconnu"])
        check_response("restaurants", response, _EXPECTED_VALIDATION)
        body = response.json()
        return ValidationVerdict(
            valid=bool(body["valid"]),
            subtotal=body.get("subtotal"),
            reasons=[str(reason) for reason in body.get("reasons", [])],
        )

    async def create_kitchen_ticket(
        self, restaurant_id: str, order_id: str, items: list[CartItem]
    ) -> bool:
        """Saga step 4 — ``POST /api/v1/restaurants/{id}/kitchen-tickets``.

        Returns True when the kitchen accepts (201) and False when it refuses (409,
        the compensation trigger). Other statuses raise the usual exception families.
        """
        response = await self._http.post(
            f"{self._base_url}/api/v1/restaurants/{restaurant_id}/kitchen-tickets",
            json={
                "order_id": order_id,
                "items": [
                    {"menu_item_id": item.menu_item_id, "quantity": item.quantity}
                    for item in items
                ],
            },
            headers=correlation_headers(),
        )
        if response.status_code == 409:
            return False
        check_response("restaurants", response, _EXPECTED_TICKET)
        return True
