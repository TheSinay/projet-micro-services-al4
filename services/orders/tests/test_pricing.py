"""Unit tests for the pricing helpers (haversine, subtotal, delivery fee, rounding)."""

import pytest

from app.repositories.entities import CartItem, ItemOption
from app.services.pricing import compute_delivery_fee, compute_subtotal, haversine_km


def test_haversine_zero_for_same_point() -> None:
    assert haversine_km(48.85, 2.35, 48.85, 2.35) == 0.0


def test_haversine_one_degree_of_latitude() -> None:
    # One degree of latitude = R * pi / 180 = 111.19492664... km
    assert haversine_km(48.0, 2.0, 49.0, 2.0) == pytest.approx(111.19492664, abs=1e-6)


def test_subtotal_includes_option_deltas() -> None:
    items = [
        CartItem(
            menu_item_id="pizza",
            name="Pizza",
            unit_price=10.0,
            quantity=2,
            options=[ItemOption("extra cheese", 1.5), ItemOption("no basil", -0.5)],
        ),
        CartItem(menu_item_id="soda", name="Cola", unit_price=3.5, quantity=1),
    ]
    assert compute_subtotal(items) == 25.5


def test_subtotal_is_rounded_to_two_decimals() -> None:
    # 1.1 * 3 = 3.3000000000000003 as raw floats: round(x, 2) is systematic.
    items = [CartItem(menu_item_id="x", name="X", unit_price=1.1, quantity=3)]
    assert compute_subtotal(items) == 3.3


def test_delivery_fee_flat_when_restaurant_position_unknown() -> None:
    assert compute_delivery_fee(2.5, 0.5, None, None, 48.0, 2.0) == 2.5
    assert compute_delivery_fee(2.5, 0.5, 48.0, None, 48.0, 2.0) == 2.5


def test_delivery_fee_with_distance() -> None:
    # 2.50 + 0.50 * 111.19492664... = 58.097... -> 58.10
    assert compute_delivery_fee(2.5, 0.5, 48.0, 2.0, 49.0, 2.0) == 58.1
