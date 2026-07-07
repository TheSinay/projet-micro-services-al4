"""Tests for the address book endpoints."""

from fastapi.testclient import TestClient

from tests.conftest import ADDRESS_PAYLOAD


def _create_address(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post("/api/v1/users/me/addresses", headers=headers, json=ADDRESS_PAYLOAD)
    assert response.status_code == 201
    address_id: str = response.json()["id"]
    return address_id


def test_create_and_list_addresses(client: TestClient, auth_headers: dict[str, str]) -> None:
    address_id = _create_address(client, auth_headers)
    response = client.get("/api/v1/users/me/addresses", headers=auth_headers)
    assert response.status_code == 200
    addresses = response.json()
    assert len(addresses) == 1
    assert addresses[0]["id"] == address_id
    assert addresses[0]["label"] == ADDRESS_PAYLOAD["label"]
    assert addresses[0]["city"] == ADDRESS_PAYLOAD["city"]


def test_list_addresses_empty_by_default(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users/me/addresses", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_update_address(client: TestClient, auth_headers: dict[str, str]) -> None:
    address_id = _create_address(client, auth_headers)
    updated = {**ADDRESS_PAYLOAD, "label": "Work", "city": "Lyon"}
    response = client.put(
        f"/api/v1/users/me/addresses/{address_id}", headers=auth_headers, json=updated
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Work"
    assert body["city"] == "Lyon"
    assert body["id"] == address_id


def test_delete_address(client: TestClient, auth_headers: dict[str, str]) -> None:
    address_id = _create_address(client, auth_headers)
    response = client.delete(f"/api/v1/users/me/addresses/{address_id}", headers=auth_headers)
    assert response.status_code == 204
    assert client.get("/api/v1/users/me/addresses", headers=auth_headers).json() == []


def test_update_unknown_address_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.put(
        "/api/v1/users/me/addresses/unknown-id", headers=auth_headers, json=ADDRESS_PAYLOAD
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Address not found"}


def test_delete_unknown_address_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.delete("/api/v1/users/me/addresses/unknown-id", headers=auth_headers)
    assert response.status_code == 404


def test_address_of_another_user_is_not_reachable(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    address_id = _create_address(client, auth_headers)

    # Register a second user and try to touch the first user's address.
    other_payload = {
        "email": "bob@example.com",
        "password": "An0therPass!",
        "name": "Bob Petit",
        "phone": "+33600000000",
    }
    assert client.post("/api/v1/users", json=other_payload).status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": other_payload["email"], "password": other_payload["password"]},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    assert client.get("/api/v1/users/me/addresses", headers=other_headers).json() == []
    response = client.put(
        f"/api/v1/users/me/addresses/{address_id}", headers=other_headers, json=ADDRESS_PAYLOAD
    )
    assert response.status_code == 404


def test_create_address_invalid_latitude_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {**ADDRESS_PAYLOAD, "lat": 123.0}
    response = client.post("/api/v1/users/me/addresses", headers=auth_headers, json=payload)
    assert response.status_code == 422


def test_addresses_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/users/me/addresses").status_code == 401
