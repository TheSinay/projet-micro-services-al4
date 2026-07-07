"""Tests for payment creation: nominal, validation, idempotency, simulated PSP failure."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.psp import FlakyPspGateway
from tests.conftest import PAYMENT_PAYLOAD, StubRng


def test_create_payment_nominal_is_captured(client: TestClient) -> None:
    response = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["order_id"] == "order-1"
    assert body["amount"] == 42.5
    assert body["currency"] == "EUR"
    assert body["status"] == "CAPTURED"
    assert body["refunds"] == []
    assert body["refunded_amount"] == 0.0
    assert body["id"]
    assert body["created_at"]


def test_create_payment_defaults_currency_to_eur(client: TestClient) -> None:
    response = client.post("/api/v1/payments", json={"order_id": "order-2", "amount": 10.0})
    assert response.status_code == 201
    assert response.json()["currency"] == "EUR"


@pytest.mark.parametrize("amount", [0, -12.5])
def test_create_payment_rejects_non_positive_amount(client: TestClient, amount: float) -> None:
    response = client.post("/api/v1/payments", json={"order_id": "order-3", "amount": amount})
    assert response.status_code == 422


def test_create_payment_requires_order_id(client: TestClient) -> None:
    response = client.post("/api/v1/payments", json={"amount": 10.0})
    assert response.status_code == 422


def test_idempotent_replay_returns_existing_payment(client: TestClient) -> None:
    first = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert first.status_code == 201
    second = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    # No double debit: a single payment exists for the order.
    listing = client.get("/api/v1/payments", params={"order_id": "order-1"})
    assert len(listing.json()) == 1


def test_psp_failure_returns_502_and_retry_succeeds(app: FastAPI, client: TestClient) -> None:
    # Deterministic stub: first draw 0.1 < failure_rate 0.5 -> failure, then 0.99 -> success.
    app.state.psp_gateway = FlakyPspGateway(failure_rate=0.5, rng=StubRng([0.1]))

    failed = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert failed.status_code == 502
    assert failed.json() == {"detail": "PSP indisponible"}

    # The failed attempt is recorded (audit) but does not block the retry.
    listing = client.get("/api/v1/payments", params={"order_id": "order-1"})
    assert [payment["status"] for payment in listing.json()] == ["FAILED"]

    retry = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert retry.status_code == 201
    assert retry.json()["status"] == "CAPTURED"

    listing = client.get("/api/v1/payments", params={"order_id": "order-1"})
    statuses = sorted(payment["status"] for payment in listing.json())
    assert statuses == ["CAPTURED", "FAILED"]


def test_get_payment_by_id(client: TestClient) -> None:
    created = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD).json()
    response = client.get(f"/api/v1/payments/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_payment_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/payments/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


def test_list_payments_filters_by_order_id(client: TestClient) -> None:
    client.post("/api/v1/payments", json={"order_id": "order-a", "amount": 10.0})
    client.post("/api/v1/payments", json={"order_id": "order-b", "amount": 20.0})

    filtered = client.get("/api/v1/payments", params={"order_id": "order-a"})
    assert [payment["order_id"] for payment in filtered.json()] == ["order-a"]

    everything = client.get("/api/v1/payments")
    assert len(everything.json()) == 2
