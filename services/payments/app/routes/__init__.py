"""HTTP routers under ``/api/v1`` — routes contain no business logic."""

from fastapi import APIRouter

from app.routes import chaos, payments

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(payments.router)
api_router.include_router(chaos.router)
