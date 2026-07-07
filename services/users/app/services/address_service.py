"""Address book logic; ownership is always enforced (a user only sees own addresses)."""

import uuid

from app.repositories.entities import Address
from app.repositories.interfaces import AddressRepository
from app.schemas.addresses import AddressCreate, AddressUpdate
from app.services.exceptions import AddressNotFoundError


class AddressService:
    """CRUD use cases for the authenticated user's addresses."""

    def __init__(self, addresses: AddressRepository) -> None:
        self._addresses = addresses

    def list_for_user(self, user_id: str) -> list[Address]:
        return self._addresses.list_by_user(user_id)

    def create(self, user_id: str, data: AddressCreate) -> Address:
        address = Address(
            id=uuid.uuid4().hex,
            user_id=user_id,
            label=data.label,
            street=data.street,
            city=data.city,
            lat=data.lat,
            lng=data.lng,
        )
        self._addresses.add(address)
        return address

    def update(self, user_id: str, address_id: str, data: AddressUpdate) -> Address:
        address = self._get_owned(user_id, address_id)
        address.label = data.label
        address.street = data.street
        address.city = data.city
        address.lat = data.lat
        address.lng = data.lng
        self._addresses.update(address)
        return address

    def delete(self, user_id: str, address_id: str) -> None:
        self._get_owned(user_id, address_id)
        self._addresses.delete(address_id)

    def _get_owned(self, user_id: str, address_id: str) -> Address:
        """Return the address if it exists and belongs to the user, else 404."""
        address = self._addresses.get_by_id(address_id)
        if address is None or address.user_id != user_id:
            raise AddressNotFoundError()
        return address
