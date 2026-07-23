"""Tests for registration and profile endpoints."""

from fastapi.testclient import TestClient

from tests.conftest import USER_PAYLOAD


def test_register_returns_201_with_public_profile(client: TestClient) -> None:
    response = client.post("/api/v1/users", json=USER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == USER_PAYLOAD["email"]
    assert body["name"] == USER_PAYLOAD["name"]
    assert body["phone"] == USER_PAYLOAD["phone"]
    assert body["id"]
    assert "password" not in body
    assert "password_hash" not in body


def test_register_defaults_role_to_client(client: TestClient) -> None:
    response = client.post("/api/v1/users", json=USER_PAYLOAD)
    assert response.status_code == 201
    assert response.json()["role"] == "client"


def test_register_ignores_role_in_payload(client: TestClient) -> None:
    """The role is backend-owned: any client-provided role is ignored."""
    payload = {**USER_PAYLOAD, "role": "restaurant_owner"}
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "client"


def test_get_profile_exposes_role(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["role"] == "client"


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    response = client.post("/api/v1/users", json=USER_PAYLOAD)
    assert response.status_code == 409
    assert response.json() == {"detail": "Email already registered"}


def test_register_duplicate_email_is_case_insensitive(client: TestClient) -> None:
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    payload = {**USER_PAYLOAD, "email": USER_PAYLOAD["email"].upper()}
    assert client.post("/api/v1/users", json=payload).status_code == 409


def test_register_invalid_email_returns_422(client: TestClient) -> None:
    payload = {**USER_PAYLOAD, "email": "not-an-email"}
    assert client.post("/api/v1/users", json=payload).status_code == 422


def test_get_profile_with_valid_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == USER_PAYLOAD["email"]
    assert body["name"] == USER_PAYLOAD["name"]


def test_get_profile_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_get_profile_with_unknown_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer definitely-not-a-token"}
    )
    assert response.status_code == 401


def test_get_profile_with_malformed_scheme_returns_401(client: TestClient, auth_token: str) -> None:
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Basic {auth_token}"})
    assert response.status_code == 401


def test_get_profile_with_empty_bearer_token_returns_401(client: TestClient) -> None:
    """Edge case (QA): a 'Bearer' scheme with an empty/blank token must be rejected."""
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer   "})
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing authentication token"}


def test_update_profile_changes_name_and_phone(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/v1/users/me",
        headers=auth_headers,
        json={"name": "Alice Durand", "phone": "+33700000000"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Alice Durand"
    assert body["phone"] == "+33700000000"

    # The change is persisted for subsequent reads.
    profile = client.get("/api/v1/users/me", headers=auth_headers).json()
    assert profile["name"] == "Alice Durand"


def test_update_profile_without_token_returns_401(client: TestClient) -> None:
    response = client.put("/api/v1/users/me", json={"name": "X", "phone": "+337"})
    assert response.status_code == 401
