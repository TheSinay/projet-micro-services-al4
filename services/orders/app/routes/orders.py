"""Order endpoints: checkout, tracking (state machine), history."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies import OrderServiceDep
from app.schemas.orders import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def place_order(payload: OrderCreate, order_service: OrderServiceDep) -> OrderRead:
    return OrderRead.model_validate(order_service.place_order(payload))


@router.get("", response_model=list[OrderRead])
def list_orders(
    user_id: Annotated[str, Query(min_length=1)],
    order_service: OrderServiceDep,
) -> list[OrderRead]:
    return [OrderRead.model_validate(order) for order in order_service.list_for_user(user_id)]


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: str, order_service: OrderServiceDep) -> OrderRead:
    return OrderRead.model_validate(order_service.get(order_id))


@router.patch("/{order_id}/status", response_model=OrderRead)
def update_status(
    order_id: str,
    payload: OrderStatusUpdate,
    order_service: OrderServiceDep,
) -> OrderRead:
    return OrderRead.model_validate(order_service.transition(order_id, payload.status))
