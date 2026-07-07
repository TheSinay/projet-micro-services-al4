"""Address book endpoints (scoped to the authenticated user)."""

from fastapi import APIRouter, status

from app.dependencies import AddressServiceDep, CurrentUser
from app.schemas.addresses import AddressCreate, AddressRead, AddressUpdate

router = APIRouter(prefix="/users/me/addresses", tags=["addresses"])


@router.get("", response_model=list[AddressRead])
def list_addresses(
    current_user: CurrentUser,
    address_service: AddressServiceDep,
) -> list[AddressRead]:
    addresses = address_service.list_for_user(current_user.id)
    return [AddressRead.model_validate(address) for address in addresses]


@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
def create_address(
    payload: AddressCreate,
    current_user: CurrentUser,
    address_service: AddressServiceDep,
) -> AddressRead:
    address = address_service.create(current_user.id, payload)
    return AddressRead.model_validate(address)


@router.put("/{address_id}", response_model=AddressRead)
def update_address(
    address_id: str,
    payload: AddressUpdate,
    current_user: CurrentUser,
    address_service: AddressServiceDep,
) -> AddressRead:
    address = address_service.update(current_user.id, address_id, payload)
    return AddressRead.model_validate(address)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(
    address_id: str,
    current_user: CurrentUser,
    address_service: AddressServiceDep,
) -> None:
    address_service.delete(current_user.id, address_id)
