"""Tests for default seed users."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_seed_users_are_populated_at_startup() -> None:
    app = create_app()
    with TestClient(app) as client:
        # Check login for restaurateur account
        resp = client.post(
            "/api/v1/auth/login", json={"email": "chef@gourmet.fr", "password": "Password123!"}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        # Check login for courier account
        resp = client.post(
            "/api/v1/auth/login", json={"email": "bob@livreur.fr", "password": "Password123!"}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

        # Check login for client account
        resp = client.post(
            "/api/v1/auth/login", json={"email": "alice@example.com", "password": "Password123!"}
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()
