"""Price computation for orders.

Amounts are ``float`` for the prototype; every computed amount is systematically
rounded with ``round(x, 2)`` to avoid float artefacts (e.g. ``1.1 * 3``).
"""

import math

from app.repositories.entities import CartItem

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in kilometers between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.asin(math.sqrt(a))


def compute_subtotal(items: list[CartItem]) -> float:
    """Sum of ``(unit_price + sum of option price deltas) * quantity`` over the cart lines."""
    subtotal = sum(
        (item.unit_price + sum(option.price_delta for option in item.options)) * item.quantity
        for item in items
    )
    return round(subtotal, 2)


def compute_delivery_fee(
    base_fee: float,
    fee_per_km: float,
    restaurant_lat: float | None,
    restaurant_lng: float | None,
    delivery_lat: float,
    delivery_lng: float,
) -> float:
    """Delivery fee: flat base fee plus a per-km part when both positions are known.

    When the restaurant coordinates are unknown, only the flat base fee applies.
    """
    if restaurant_lat is None or restaurant_lng is None:
        return round(base_fee, 2)
    distance_km = haversine_km(restaurant_lat, restaurant_lng, delivery_lat, delivery_lng)
    return round(base_fee + fee_per_km * distance_km, 2)
