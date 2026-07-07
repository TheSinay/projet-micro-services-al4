"""HTTP routers under ``/api/v1`` — routes contain no business logic."""

from fastapi import APIRouter

from app.routes import menu_items, restaurants, tickets, validations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(restaurants.router)
api_router.include_router(menu_items.router)
api_router.include_router(validations.router)
api_router.include_router(tickets.router)
