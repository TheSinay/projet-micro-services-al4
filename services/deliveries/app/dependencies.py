"""FastAPI dependency wiring: repositories and event bus (from app.state), services."""

from typing import Annotated

from fastapi import Depends, Request

from app.events import EventBus
from app.repositories.interfaces import CourierRepository, DeliveryRepository
from app.services.courier_service import CourierService
from app.services.delivery_service import DeliveryService


def get_courier_repository(request: Request) -> CourierRepository:
    repository: CourierRepository = request.app.state.courier_repository
    return repository


def get_delivery_repository(request: Request) -> DeliveryRepository:
    repository: DeliveryRepository = request.app.state.delivery_repository
    return repository


def get_event_bus(request: Request) -> EventBus:
    bus: EventBus = request.app.state.event_bus
    return bus


def get_courier_service(
    couriers: Annotated[CourierRepository, Depends(get_courier_repository)],
) -> CourierService:
    return CourierService(couriers)


def get_delivery_service(
    couriers: Annotated[CourierRepository, Depends(get_courier_repository)],
    deliveries: Annotated[DeliveryRepository, Depends(get_delivery_repository)],
    events: Annotated[EventBus, Depends(get_event_bus)],
) -> DeliveryService:
    return DeliveryService(couriers, deliveries, events)


CourierServiceDep = Annotated[CourierService, Depends(get_courier_service)]
DeliveryServiceDep = Annotated[DeliveryService, Depends(get_delivery_service)]
