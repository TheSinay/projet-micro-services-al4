"""HTTP routers under ``/api/v1`` — routes contain no business logic."""

from fastapi import APIRouter

from app.routes import couriers, deliveries

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(couriers.router)
api_router.include_router(deliveries.router)
