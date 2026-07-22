"""Shared fixtures — each test gets a fresh application, hence a clean in-memory state."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

USER_PAYLOAD: dict[str, str] = {
    "email": "alice@example.com",
    "password": "S3cretPass!",
    "name": "Alice Martin",
    "phone": "+33612345678",
}

ADDRESS_PAYLOAD: dict[str, object] = {
    "label": "Home",
    "street": "10 rue de la Paix",
    "city": "Paris",
    "lat": 48.8698,
    "lng": 2.3311,
}


@pytest.fixture
def client() -> Iterator[TestClient]:
    """A TestClient bound to a brand new application instance."""
    with TestClient(create_app(Settings(seed_data=False))) as test_client:
        yield test_client


@pytest.fixture
def auth_token(client: TestClient) -> str:
    """Register the default user and return a valid bearer token."""
    response = client.post("/api/v1/users", json=USER_PAYLOAD)
    assert response.status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    token: str = response.json()["access_token"]
    return token


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization headers for the default registered user."""
    return {"Authorization": f"Bearer {auth_token}"}
