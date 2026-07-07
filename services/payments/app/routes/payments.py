"""Payment endpoints (charge, refunds, lookups)."""

from fastapi import APIRouter, Response, status

from app.dependencies import PaymentServiceDep
from app.schemas.payments import PaymentCreate, PaymentRead, RefundCreate

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    payment_service: PaymentServiceDep,
    response: Response,
) -> PaymentRead:
    """Charge an order. Idempotent per ``order_id``: replaying an already captured
    order returns the existing payment with 200 (no double debit)."""
    payment, created = payment_service.create_payment(payload)
    if not created:
        response.status_code = status.HTTP_200_OK
    return PaymentRead.model_validate(payment)


@router.get("", response_model=list[PaymentRead])
def list_payments(
    payment_service: PaymentServiceDep,
    order_id: str | None = None,
) -> list[PaymentRead]:
    payments = payment_service.list_payments(order_id)
    return [PaymentRead.model_validate(payment) for payment in payments]


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: str, payment_service: PaymentServiceDep) -> PaymentRead:
    return PaymentRead.model_validate(payment_service.get_payment(payment_id))


@router.post(
    "/{payment_id}/refunds",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_refund(
    payment_id: str,
    payload: RefundCreate,
    payment_service: PaymentServiceDep,
) -> PaymentRead:
    """Apply a partial or total refund; returns the updated payment."""
    return PaymentRead.model_validate(payment_service.refund(payment_id, payload))
