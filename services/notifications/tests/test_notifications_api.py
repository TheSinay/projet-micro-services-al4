"""Tests for GET /api/v1/notifications (filters, ordering, error handling)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.dispatch import NotificationDispatcher
from app.services.exceptions import DomainError
from tests.conftest import make_event


def _seed(dispatcher: NotificationDispatcher) -> None:
    """Two events in chronological order: confirmed first, picked_up last."""
    dispatcher.handle_event(
        make_event(
            "order.confirmed",
            {"order_id": "order-1", "user_id": "user-1", "restaurant_id": "resto-1"},
            correlation_id="corr-a",
        )
    )
    dispatcher.handle_event(
        make_event(
            "delivery.picked_up",
            {"order_id": "order-1", "user_id": "user-1"},
            correlation_id="corr-b",
        )
    )


def test_list_returns_all_notifications_most_recent_first(
    client: TestClient, dispatcher: NotificationDispatcher
) -> None:
    _seed(dispatcher)
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 4  # 2 client (confirmed) + 1 restaurant + 1 client (picked_up)
    assert items[0]["event"] == "delivery.picked_up"
    assert items[-1]["event"] == "order.confirmed"


def test_list_filters_by_recipient_type(
    client: TestClient, dispatcher: NotificationDispatcher
) -> None:
    _seed(dispatcher)
    response = client.get("/api/v1/notifications", params={"recipient_type": "restaurant"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["recipient_type"] == "restaurant"
    assert items[0]["recipient_id"] == "resto-1"
    assert items[0]["subject"] == "Nouvelle commande à préparer"


def test_list_filters_by_recipient_id_and_event(
    client: TestClient, dispatcher: NotificationDispatcher
) -> None:
    _seed(dispatcher)
    response = client.get(
        "/api/v1/notifications",
        params={"recipient_id": "user-1", "event": "order.confirmed"},
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert {item["channel"] for item in items} == {"email", "push"}
    assert all(item["event"] == "order.confirmed" for item in items)


def test_list_with_unmatched_filter_returns_empty_list(
    client: TestClient, dispatcher: NotificationDispatcher
) -> None:
    _seed(dispatcher)
    response = client.get("/api/v1/notifications", params={"recipient_id": "nobody"})
    assert response.status_code == 200
    assert response.json() == []


def test_invalid_recipient_type_is_rejected_with_422(client: TestClient) -> None:
    response = client.get("/api/v1/notifications", params={"recipient_type": "alien"})
    assert response.status_code == 422


def test_response_exposes_correlation_id_of_the_source_event(
    client: TestClient, dispatcher: NotificationDispatcher
) -> None:
    _seed(dispatcher)
    response = client.get("/api/v1/notifications", params={"event": "delivery.picked_up"})
    assert response.status_code == 200
    assert response.json()[0]["correlation_id"] == "corr-b"


def test_domain_errors_are_translated_to_json_detail(app: FastAPI) -> None:
    """The shared DomainError handler maps business errors to ``{"detail": ...}``."""

    class TeapotError(DomainError):
        status_code = 418
        detail = "teapot"

    @app.get("/boom")
    def boom() -> None:
        raise TeapotError()

    with TestClient(app) as client:
        response = client.get("/boom")
    assert response.status_code == 418
    assert response.json() == {"detail": "teapot"}
