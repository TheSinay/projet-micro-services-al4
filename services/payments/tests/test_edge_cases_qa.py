"""QA edge-case tests: float rounding on refunds, exact cumulated sums, idempotency corners.

Added by the QA agent to lock down the critical business rules:
- cumulated refunds with cent amounts (binary float traps like 0.1 + 0.2),
- refunds whose explicit amounts sum exactly to the captured amount,
- one-cent overflow rejection,
- idempotent replay while PARTIALLY_REFUNDED,
- replay after full REFUNDED (documented behaviour: a new charge is legitimate).
"""

from typing import Any

from fastapi.testclient import TestClient


def _create_payment(client: TestClient, order_id: str, amount: float) -> str:
    response = client.post("/api/v1/payments", json={"order_id": order_id, "amount": amount})
    assert response.status_code == 201
    payment_id: str = response.json()["id"]
    return payment_id


def _refund(
    client: TestClient, payment_id: str, amount: float | None, reason: str = "qa"
) -> dict[str, Any]:
    payload: dict[str, object] = {"reason": reason}
    if amount is not None:
        payload["amount"] = amount
    response = client.post(f"/api/v1/payments/{payment_id}/refunds", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_two_explicit_partial_refunds_summing_exactly_to_captured(client: TestClient) -> None:
    """25.0 + 25.0 on a 50.0 payment must yield REFUNDED, not PARTIALLY_REFUNDED."""
    payment_id = _create_payment(client, "order-exact", 50.0)
    first = _refund(client, payment_id, 25.0)
    assert first["status"] == "PARTIALLY_REFUNDED"
    second = _refund(client, payment_id, 25.0)
    assert second["status"] == "REFUNDED"
    assert second["refunded_amount"] == 50.0


def test_cent_refunds_with_float_rounding_reach_refunded(client: TestClient) -> None:
    """3.33 + 3.33 + 3.44 on a 10.10 payment: binary float sums (10.100000000000001)
    must not block the last refund nor leave the status stuck on PARTIALLY_REFUNDED."""
    payment_id = _create_payment(client, "order-cents", 10.10)
    _refund(client, payment_id, 3.33)
    _refund(client, payment_id, 3.33)
    final = _refund(client, payment_id, 3.44)
    assert final["status"] == "REFUNDED"
    assert final["refunded_amount"] == 10.10


def test_classic_binary_float_trap_point_one_times_three(client: TestClient) -> None:
    """0.1 + 0.1 + 0.1 on a 0.30 payment (0.1 + 0.2 != 0.3 in binary floats)."""
    payment_id = _create_payment(client, "order-float-trap", 0.30)
    _refund(client, payment_id, 0.1)
    _refund(client, payment_id, 0.1)
    final = _refund(client, payment_id, 0.1)
    assert final["status"] == "REFUNDED"
    assert final["refunded_amount"] == 0.3


def test_default_refund_after_cent_partials_refunds_exact_remaining(client: TestClient) -> None:
    """Omitted amount must refund the exact remaining (10.10 - 6.66 = 3.44), to the cent."""
    payment_id = _create_payment(client, "order-remaining", 10.10)
    _refund(client, payment_id, 3.33)
    _refund(client, payment_id, 3.33)
    final = _refund(client, payment_id, None)
    assert final["status"] == "REFUNDED"
    assert [refund["amount"] for refund in final["refunds"]] == [3.33, 3.33, 3.44]
    assert final["refunded_amount"] == 10.10


def test_refund_exceeding_remaining_by_one_cent_is_rejected(client: TestClient) -> None:
    payment_id = _create_payment(client, "order-one-cent", 10.10)
    _refund(client, payment_id, 6.66)
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 3.45, "reason": "one cent too much"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Cumulated refunds exceed captured amount"}
    # The rejected attempt must not have been recorded.
    payment = client.get(f"/api/v1/payments/{payment_id}").json()
    assert payment["refunded_amount"] == 6.66
    assert payment["status"] == "PARTIALLY_REFUNDED"


def test_idempotent_replay_while_partially_refunded(client: TestClient) -> None:
    """A PARTIALLY_REFUNDED payment still holds captured money: replay must return it (200),
    never charge again."""
    payment_id = _create_payment(client, "order-partial-replay", 20.0)
    _refund(client, payment_id, 5.0)

    replay = client.post(
        "/api/v1/payments",
        json={"order_id": "order-partial-replay", "amount": 20.0},
    )
    assert replay.status_code == 200
    assert replay.json()["id"] == payment_id
    assert replay.json()["status"] == "PARTIALLY_REFUNDED"

    listing = client.get("/api/v1/payments", params={"order_id": "order-partial-replay"})
    assert len(listing.json()) == 1


def test_replay_after_full_refund_creates_a_new_payment(client: TestClient) -> None:
    """Documented behaviour: once fully REFUNDED the money was returned, so a new POST
    for the same order legitimately charges again (201, new payment id)."""
    first_id = _create_payment(client, "order-refunded-replay", 15.0)
    _refund(client, first_id, None, reason="full refund")

    replay = client.post(
        "/api/v1/payments",
        json={"order_id": "order-refunded-replay", "amount": 15.0},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] != first_id
    assert replay.json()["status"] == "CAPTURED"

    listing = client.get("/api/v1/payments", params={"order_id": "order-refunded-replay"})
    statuses = sorted(payment["status"] for payment in listing.json())
    assert statuses == ["CAPTURED", "REFUNDED"]


def test_created_amount_is_rounded_to_cents(client: TestClient) -> None:
    """Amounts are stored rounded to the cent (documented rule)."""
    response = client.post(
        "/api/v1/payments",
        json={"order_id": "order-rounding", "amount": 19.999},
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 20.0
