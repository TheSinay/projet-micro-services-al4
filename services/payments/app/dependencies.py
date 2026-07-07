"""FastAPI dependency wiring: repositories and gateway (from app.state) -> services."""

from typing import Annotated

from fastapi import Depends, Request

from app.repositories.interfaces import PaymentRepository
from app.services.payment_service import PaymentService
from app.services.psp import PspGateway


def get_payment_repository(request: Request) -> PaymentRepository:
    repository: PaymentRepository = request.app.state.payment_repository
    return repository


def get_psp_gateway(request: Request) -> PspGateway:
    gateway: PspGateway = request.app.state.psp_gateway
    return gateway


def get_payment_service(
    payments: Annotated[PaymentRepository, Depends(get_payment_repository)],
    psp: Annotated[PspGateway, Depends(get_psp_gateway)],
) -> PaymentService:
    return PaymentService(payments, psp)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
PspGatewayDep = Annotated[PspGateway, Depends(get_psp_gateway)]
