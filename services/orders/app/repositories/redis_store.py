"""Redis-backed cart store (production backend, selected via ``ORDERS_CART_STORE_BACKEND``).

Each cart is stored as a JSON document under the key ``cart:{user_id}`` so several
instances of the service can share the same cart state (stateless service).

The store depends on a minimal structural ``RedisClient`` protocol instead of the
concrete ``redis.Redis`` class, so unit tests can exercise it hermetically with an
in-memory fake — no running Redis is ever required by the test suite.
"""

import json
from dataclasses import asdict
from typing import Any, Protocol

from app.repositories.entities import Cart, CartItem, ItemOption

CART_KEY_PREFIX = "cart:"


class RedisClient(Protocol):
    """The tiny subset of ``redis.Redis`` used by the cart store."""

    def get(self, name: str, /) -> Any: ...

    def set(self, name: str, value: str, /) -> Any: ...

    def delete(self, *names: str) -> Any: ...


def _cart_key(user_id: str) -> str:
    return f"{CART_KEY_PREFIX}{user_id}"


def _cart_from_document(document: dict[str, Any]) -> Cart:
    """Rebuild a :class:`Cart` entity from its JSON representation."""
    return Cart(
        user_id=document["user_id"],
        restaurant_id=document.get("restaurant_id"),
        restaurant_lat=document.get("restaurant_lat"),
        restaurant_lng=document.get("restaurant_lng"),
        items=[
            CartItem(
                menu_item_id=item["menu_item_id"],
                name=item["name"],
                unit_price=item["unit_price"],
                quantity=item["quantity"],
                options=[
                    ItemOption(name=option["name"], price_delta=option["price_delta"])
                    for option in item.get("options", [])
                ],
            )
            for item in document.get("items", [])
        ],
    )


class RedisCartStore:
    """JSON-per-key cart store on Redis (key ``cart:{user_id}``)."""

    def __init__(self, client: RedisClient) -> None:
        self._client = client

    def get(self, user_id: str) -> Cart | None:
        raw = self._client.get(_cart_key(user_id))
        if raw is None:
            return None
        document: dict[str, Any] = json.loads(raw)
        return _cart_from_document(document)

    def save(self, cart: Cart) -> None:
        self._client.set(_cart_key(cart.user_id), json.dumps(asdict(cart)))

    def clear(self, user_id: str) -> None:
        self._client.delete(_cart_key(user_id))
