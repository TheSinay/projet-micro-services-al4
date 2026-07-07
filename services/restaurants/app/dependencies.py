"""FastAPI dependency wiring: repositories and event bus (from app.state), then services."""

from typing import Annotated

from fastapi import Depends, Request

from app.events import EventBus
from app.repositories.interfaces import (
    KitchenTicketRepository,
    MenuItemRepository,
    RestaurantRepository,
)
from app.services.menu_item_service import MenuItemService
from app.services.restaurant_service import RestaurantService
from app.services.ticket_service import KitchenTicketService
from app.services.validation_service import OrderValidationService


def get_restaurant_repository(request: Request) -> RestaurantRepository:
    repository: RestaurantRepository = request.app.state.restaurant_repository
    return repository


def get_menu_item_repository(request: Request) -> MenuItemRepository:
    repository: MenuItemRepository = request.app.state.menu_item_repository
    return repository


def get_ticket_repository(request: Request) -> KitchenTicketRepository:
    repository: KitchenTicketRepository = request.app.state.ticket_repository
    return repository


def get_event_bus(request: Request) -> EventBus:
    bus: EventBus = request.app.state.event_bus
    return bus


def get_restaurant_service(
    restaurants: Annotated[RestaurantRepository, Depends(get_restaurant_repository)],
    menu_items: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
) -> RestaurantService:
    return RestaurantService(restaurants, menu_items)


def get_menu_item_service(
    restaurants: Annotated[RestaurantRepository, Depends(get_restaurant_repository)],
    menu_items: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
) -> MenuItemService:
    return MenuItemService(restaurants, menu_items)


def get_validation_service(
    restaurants: Annotated[RestaurantRepository, Depends(get_restaurant_repository)],
    menu_items: Annotated[MenuItemRepository, Depends(get_menu_item_repository)],
) -> OrderValidationService:
    return OrderValidationService(restaurants, menu_items)


def get_ticket_service(
    restaurants: Annotated[RestaurantRepository, Depends(get_restaurant_repository)],
    tickets: Annotated[KitchenTicketRepository, Depends(get_ticket_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> KitchenTicketService:
    return KitchenTicketService(restaurants, tickets, event_bus)


RestaurantServiceDep = Annotated[RestaurantService, Depends(get_restaurant_service)]
MenuItemServiceDep = Annotated[MenuItemService, Depends(get_menu_item_service)]
OrderValidationServiceDep = Annotated[OrderValidationService, Depends(get_validation_service)]
KitchenTicketServiceDep = Annotated[KitchenTicketService, Depends(get_ticket_service)]
