"""Delivery assignment and tracking endpoints."""

from fastapi import APIRouter, Response, status

from app.dependencies import DeliveryServiceDep
from app.schemas.deliveries import DeliveryCreate, DeliveryRead, DeliveryStatusUpdate

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.post(
    "",
    response_model=DeliveryRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"description": "Active delivery already exists for this order"},
        status.HTTP_409_CONFLICT: {"description": "No courier available"},
    },
)
async def create_delivery(
    payload: DeliveryCreate,
    response: Response,
    delivery_service: DeliveryServiceDep,
) -> DeliveryRead:
    delivery, created = await delivery_service.request_delivery(payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return DeliveryRead.model_validate(delivery)


@router.get("", response_model=list[DeliveryRead])
def list_deliveries(
    delivery_service: DeliveryServiceDep,
    order_id: str | None = None,
) -> list[DeliveryRead]:
    return [DeliveryRead.model_validate(d) for d in delivery_service.list(order_id)]


@router.get("/{delivery_id}", response_model=DeliveryRead)
def get_delivery(delivery_id: str, delivery_service: DeliveryServiceDep) -> DeliveryRead:
    return DeliveryRead.model_validate(delivery_service.get(delivery_id))


@router.patch("/{delivery_id}", response_model=DeliveryRead)
async def update_delivery_status(
    delivery_id: str,
    payload: DeliveryStatusUpdate,
    delivery_service: DeliveryServiceDep,
) -> DeliveryRead:
    delivery = await delivery_service.update_status(delivery_id, payload.status)
    return DeliveryRead.model_validate(delivery)
