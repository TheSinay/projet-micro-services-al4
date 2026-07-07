"""Tests for the X-Correlation-Id middleware."""

from fastapi.testclient import TestClient


def test_correlation_id_is_generated_when_absent(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers.get("X-Correlation-Id")


def test_provided_correlation_id_is_echoed_back(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-Id": "corr-test-123"})
    assert response.headers["X-Correlation-Id"] == "corr-test-123"


def test_correlation_id_present_on_error_responses(client: TestClient) -> None:
    response = client.get("/api/v1/payments/unknown-id")
    assert response.status_code == 404
    assert response.headers.get("X-Correlation-Id")
