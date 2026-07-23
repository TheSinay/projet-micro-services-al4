"""Tests for the login endpoint."""

from fastapi.testclient import TestClient

from tests.conftest import USER_PAYLOAD


def test_login_returns_opaque_token(client: TestClient) -> None:
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": "WrongPassword1"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "AnyPassword1"},
    )
    assert response.status_code == 401


def test_login_email_is_case_insensitive(client: TestClient) -> None:
    """Edge case (QA): emails are stored lowercased, login must accept any casing."""
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        json={"email": str(USER_PAYLOAD["email"]).upper(), "password": USER_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_full_flow_register_login_profile(client: TestClient) -> None:
    assert client.post("/api/v1/users", json=USER_PAYLOAD).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": USER_PAYLOAD["email"], "password": USER_PAYLOAD["password"]},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    profile = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == USER_PAYLOAD["email"]
