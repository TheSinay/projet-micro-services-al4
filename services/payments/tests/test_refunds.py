"""Tests for refunds: partial, total, cumulated limits and status conflicts."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.psp import FlakyPspGateway
from tests.conftest import StubRng


def _create_payment(client: TestClient, order_id: str = "order-r", amount: float = 50.0) -> str:
    response = client.post("/api/v1/payments", json={"order_id": order_id, "amount": amount})
    assert response.status_code == 201
    payment_id: str = response.json()["id"]
    return payment_id


def test_partial_refund_sets_partially_refunded(client: TestClient) -> None:
    payment_id = _create_payment(client)
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 20.0, "reason": "damaged item"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PARTIALLY_REFUNDED"
    assert body["refunded_amount"] == 20.0
    assert len(body["refunds"]) == 1
    assert body["refunds"][0]["reason"] == "damaged item"


def test_partial_then_remaining_refund_sets_refunded(client: TestClient) -> None:
    payment_id = _create_payment(client)
    client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 20.0, "reason": "damaged item"},
    )
    # No amount -> refund the whole remaining refundable amount (30.0).
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"reason": "order cancelled"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "REFUNDED"
    assert body["refunded_amount"] == 50.0
    assert [refund["amount"] for refund in body["refunds"]] == [20.0, 30.0]


def test_total_refund_without_amount(client: TestClient) -> None:
    payment_id = _create_payment(client)
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"reason": "full compensation"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "REFUNDED"
    assert response.json()["refunded_amount"] == 50.0


def test_refund_exceeding_captured_amount_is_rejected(client: TestClient) -> None:
    payment_id = _create_payment(client)
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 60.0, "reason": "too much"},
    )
    assert response.status_code == 422
    assert response.json() == {"detail": "Cumulated refunds exceed captured amount"}


def test_cumulated_refunds_cannot_exceed_captured_amount(client: TestClient) -> None:
    payment_id = _create_payment(client)
    first = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 30.0, "reason": "partial"},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 30.0, "reason": "would overflow"},
    )
    assert second.status_code == 422


def test_refund_on_failed_payment_is_conflict(app: FastAPI, client: TestClient) -> None:
    app.state.psp_gateway = FlakyPspGateway(failure_rate=1.0, rng=StubRng([0.5]))
    failed = client.post("/api/v1/payments", json={"order_id": "order-f", "amount": 10.0})
    assert failed.status_code == 502
    failed_id = client.get("/api/v1/payments", params={"order_id": "order-f"}).json()[0]["id"]

    response = client.post(
        f"/api/v1/payments/{failed_id}/refunds",
        json={"reason": "cannot refund a failed charge"},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Payment cannot be refunded in its current status"}


def test_refund_on_fully_refunded_payment_is_conflict(client: TestClient) -> None:
    payment_id = _create_payment(client)
    client.post(f"/api/v1/payments/{payment_id}/refunds", json={"reason": "full"})
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 1.0, "reason": "nothing left"},
    )
    assert response.status_code == 409


def test_refund_unknown_payment_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/payments/does-not-exist/refunds",
        json={"reason": "ghost payment"},
    )
    assert response.status_code == 404


def test_refund_rejects_non_positive_amount(client: TestClient) -> None:
    payment_id = _create_payment(client)
    response = client.post(
        f"/api/v1/payments/{payment_id}/refunds",
        json={"amount": 0, "reason": "invalid"},
    )
    assert response.status_code == 422


def test_refund_requires_reason(client: TestClient) -> None:
    payment_id = _create_payment(client)
    response = client.post(f"/api/v1/payments/{payment_id}/refunds", json={"amount": 5.0})
    assert response.status_code == 422
