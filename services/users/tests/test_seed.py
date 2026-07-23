"""Tests for default seed users."""

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.users import UserRole
from app.seed import SEED_USERS


def test_seed_users_have_expected_roles() -> None:
    roles = {user.id: user.role for user in SEED_USERS}
    assert roles["usr_alice"] == UserRole.CLIENT
    assert roles["usr_resto"] == UserRole.RESTAURANT_OWNER
    assert roles["usr_bob"] == UserRole.COURIER


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
