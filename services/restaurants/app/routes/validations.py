"""Order validation endpoint, called synchronously by the orders SAGA orchestrator."""

from fastapi import APIRouter

from app.dependencies import OrderValidationServiceDep
from app.schemas.validations import OrderValidationRequest, OrderValidationResponse

router = APIRouter(prefix="/restaurants/{restaurant_id}/order-validations", tags=["validations"])


@router.post("", response_model=OrderValidationResponse)
def validate_order(
    restaurant_id: str,
    payload: OrderValidationRequest,
    validation_service: OrderValidationServiceDep,
) -> OrderValidationResponse:
    """Always 200 with the verdict (``valid`` / ``reasons``) — see README for the rationale."""
    result = validation_service.validate(restaurant_id, payload)
    return OrderValidationResponse(
        valid=result.valid, subtotal=result.subtotal, reasons=result.reasons
    )
