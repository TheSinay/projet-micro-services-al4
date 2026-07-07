"""Courier management logic (CRUD, availability, simulated location updates)."""

import uuid

from app.repositories.entities import Courier, Location
from app.repositories.interfaces import CourierRepository
from app.schemas.couriers import CourierCreate, CourierUpdate
from app.services.exceptions import CourierNotFoundError


class CourierService:
    """Use cases around the courier fleet."""

    def __init__(self, couriers: CourierRepository) -> None:
        self._couriers = couriers

    def create(self, data: CourierCreate) -> Courier:
        courier = Courier(
            id=uuid.uuid4().hex,
            name=data.name,
            phone=data.phone,
            available=data.available,
            location=Location(lat=data.location.lat, lng=data.location.lng),
        )
        self._couriers.add(courier)
        return courier

    def list_all(self) -> list[Courier]:
        return self._couriers.list_all()

    def get(self, courier_id: str) -> Courier:
        courier = self._couriers.get_by_id(courier_id)
        if courier is None:
            raise CourierNotFoundError()
        return courier

    def update(self, courier_id: str, data: CourierUpdate) -> Courier:
        """Partially update availability and/or the simulated GPS position."""
        courier = self.get(courier_id)
        if data.available is not None:
            courier.available = data.available
        if data.location is not None:
            courier.location = Location(lat=data.location.lat, lng=data.location.lng)
        self._couriers.update(courier)
        return courier
