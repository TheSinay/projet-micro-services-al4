"""Courier fleet endpoints."""

from fastapi import APIRouter, status

from app.dependencies import CourierServiceDep
from app.schemas.couriers import CourierCreate, CourierRead, CourierUpdate

router = APIRouter(prefix="/couriers", tags=["couriers"])


@router.post("", response_model=CourierRead, status_code=status.HTTP_201_CREATED)
def create_courier(payload: CourierCreate, courier_service: CourierServiceDep) -> CourierRead:
    courier = courier_service.create(payload)
    return CourierRead.model_validate(courier)


@router.get("", response_model=list[CourierRead])
def list_couriers(courier_service: CourierServiceDep) -> list[CourierRead]:
    return [CourierRead.model_validate(courier) for courier in courier_service.list_all()]


@router.get("/{courier_id}", response_model=CourierRead)
def get_courier(courier_id: str, courier_service: CourierServiceDep) -> CourierRead:
    return CourierRead.model_validate(courier_service.get(courier_id))


@router.patch("/{courier_id}", response_model=CourierRead)
def update_courier(
    courier_id: str,
    payload: CourierUpdate,
    courier_service: CourierServiceDep,
) -> CourierRead:
    return CourierRead.model_validate(courier_service.update(courier_id, payload))
