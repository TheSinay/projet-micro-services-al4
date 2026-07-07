"""Menu item endpoints, scoped to a restaurant."""

from fastapi import APIRouter, status

from app.dependencies import MenuItemServiceDep
from app.schemas.menu_items import MenuItemCreate, MenuItemRead, MenuItemUpdate

router = APIRouter(prefix="/restaurants/{restaurant_id}/menu-items", tags=["menu-items"])


@router.post("", response_model=MenuItemRead, status_code=status.HTTP_201_CREATED)
def create_menu_item(
    restaurant_id: str,
    payload: MenuItemCreate,
    menu_item_service: MenuItemServiceDep,
) -> MenuItemRead:
    item = menu_item_service.create(restaurant_id, payload)
    return MenuItemRead.model_validate(item)


@router.put("/{item_id}", response_model=MenuItemRead)
def update_menu_item(
    restaurant_id: str,
    item_id: str,
    payload: MenuItemUpdate,
    menu_item_service: MenuItemServiceDep,
) -> MenuItemRead:
    """Full replacement — availability toggling included."""
    item = menu_item_service.update(restaurant_id, item_id, payload)
    return MenuItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu_item(
    restaurant_id: str,
    item_id: str,
    menu_item_service: MenuItemServiceDep,
) -> None:
    menu_item_service.delete(restaurant_id, item_id)
