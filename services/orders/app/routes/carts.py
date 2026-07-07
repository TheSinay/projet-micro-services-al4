"""Cart endpoints (one cart per user, single restaurant per cart)."""

from fastapi import APIRouter, status

from app.dependencies import CartServiceDep
from app.schemas.carts import CartItemAdd, CartRead

router = APIRouter(prefix="/carts", tags=["carts"])


@router.get("/{user_id}", response_model=CartRead)
def get_cart(user_id: str, cart_service: CartServiceDep) -> CartRead:
    return CartRead.model_validate(cart_service.get_cart(user_id))


@router.post("/{user_id}/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
def add_item(user_id: str, payload: CartItemAdd, cart_service: CartServiceDep) -> CartRead:
    return CartRead.model_validate(cart_service.add_item(user_id, payload))


@router.delete("/{user_id}/items/{menu_item_id}", response_model=CartRead)
def remove_item(user_id: str, menu_item_id: str, cart_service: CartServiceDep) -> CartRead:
    return CartRead.model_validate(cart_service.remove_item(user_id, menu_item_id))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def clear_cart(user_id: str, cart_service: CartServiceDep) -> None:
    cart_service.clear(user_id)
