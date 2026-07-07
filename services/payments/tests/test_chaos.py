"""Tests for the chaos endpoint (runtime tuning of the PSP failure rate)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import PAYMENT_PAYLOAD


def test_chaos_updates_failure_rate_and_applies_immediately(
    app: FastAPI, client: TestClient
) -> None:
    response = client.post("/api/v1/_chaos", json={"failure_rate": 1.0})
    assert response.status_code == 200
    assert response.json() == {"failure_rate": 1.0}
    assert app.state.psp_gateway.failure_rate == 1.0

    # rate 1.0: any rng draw in [0, 1) is < 1.0 -> the charge always fails.
    failed = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert failed.status_code == 502

    client.post("/api/v1/_chaos", json={"failure_rate": 0.0})
    ok = client.post("/api/v1/payments", json=PAYMENT_PAYLOAD)
    assert ok.status_code == 201


@pytest.mark.parametrize("failure_rate", [-0.1, 1.5])
def test_chaos_rejects_out_of_range_rate(client: TestClient, failure_rate: float) -> None:
    response = client.post("/api/v1/_chaos", json={"failure_rate": failure_rate})
    assert response.status_code == 422
