"""Tests for the Redis-backed cart store (with a fake client) and the backend wiring.

No test opens a network connection: the fake client is a dict, and
``redis.Redis.from_url`` is lazy (it only connects on the first command).
"""

from app.config import Settings
from app.events import InMemoryEventBus, RedisEventBus
from app.main import create_app
from app.repositories.entities import Cart, CartItem, ItemOption
from app.repositories.memory import InMemoryCartStore
from app.repositories.redis_store import RedisCartStore


class FakeRedisClient:
    """Hermetic stand-in for the subset of redis.Redis used by the cart store."""

    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def get(self, name: str, /) -> str | None:
        return self.data.get(name)

    def set(self, name: str, value: str, /) -> bool:
        self.data[name] = value
        return True

    def delete(self, *names: str) -> int:
        removed = 0
        for name in names:
            removed += int(self.data.pop(name, None) is not None)
        return removed


def _cart() -> Cart:
    return Cart(
        user_id="user-1",
        restaurant_id="resto-1",
        restaurant_lat=48.0,
        restaurant_lng=2.0,
        items=[
            CartItem(
                menu_item_id="pizza",
                name="Pizza",
                unit_price=10.0,
                quantity=2,
                options=[ItemOption("extra cheese", 1.5)],
            )
        ],
    )


def test_save_then_get_round_trips_the_cart() -> None:
    client = FakeRedisClient()
    store = RedisCartStore(client)
    store.save(_cart())
    assert "cart:user-1" in client.data
    assert store.get("user-1") == _cart()


def test_get_missing_cart_returns_none() -> None:
    store = RedisCartStore(FakeRedisClient())
    assert store.get("user-1") is None


def test_clear_deletes_the_key() -> None:
    client = FakeRedisClient()
    store = RedisCartStore(client)
    store.save(_cart())
    store.clear("user-1")
    assert client.data == {}
    assert store.get("user-1") is None


def test_create_app_wires_memory_backends_by_default() -> None:
    app = create_app(Settings())
    assert isinstance(app.state.cart_store, InMemoryCartStore)
    assert isinstance(app.state.event_bus, InMemoryEventBus)


def test_create_app_wires_redis_backends_when_configured() -> None:
    settings = Settings(cart_store_backend="redis", event_bus_backend="redis")
    app = create_app(settings)
    assert isinstance(app.state.cart_store, RedisCartStore)
    assert isinstance(app.state.event_bus, RedisEventBus)
