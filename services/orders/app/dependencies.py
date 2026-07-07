"""FastAPI dependency wiring: stores (from app.state) -> services -> routes."""

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.events import EventBus
from app.repositories.interfaces import CartStore, OrderRepository
from app.services.cart_service import CartService
from app.services.order_service import OrderService


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_cart_store(request: Request) -> CartStore:
    store: CartStore = request.app.state.cart_store
    return store


def get_order_repository(request: Request) -> OrderRepository:
    repository: OrderRepository = request.app.state.order_repository
    return repository


def get_event_bus(request: Request) -> EventBus:
    event_bus: EventBus = request.app.state.event_bus
    return event_bus


def get_cart_service(
    carts: Annotated[CartStore, Depends(get_cart_store)],
) -> CartService:
    return CartService(carts)


def get_order_service(
    carts: Annotated[CartStore, Depends(get_cart_store)],
    orders: Annotated[OrderRepository, Depends(get_order_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> OrderService:
    return OrderService(
        carts,
        orders,
        event_bus,
        base_delivery_fee=settings.base_delivery_fee,
        delivery_fee_per_km=settings.delivery_fee_per_km,
    )


CartServiceDep = Annotated[CartService, Depends(get_cart_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
