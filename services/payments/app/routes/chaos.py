"""Chaos endpoint (dev/demo only): tune the simulated PSP failure rate at runtime.

Used by the resilience demo to trip the orders-side circuit breaker without
restarting the container. This is infrastructure tooling, not business logic.
"""

from fastapi import APIRouter

from app.dependencies import PspGatewayDep
from app.logging import logger
from app.schemas.chaos import ChaosRead, ChaosUpdate

router = APIRouter(tags=["chaos"])


@router.post("/_chaos", response_model=ChaosRead)
def update_failure_rate(payload: ChaosUpdate, psp: PspGatewayDep) -> ChaosRead:
    psp.failure_rate = payload.failure_rate
    logger.warning("chaos_failure_rate_updated", failure_rate=payload.failure_rate)
    return ChaosRead(failure_rate=psp.failure_rate)
