"""Simulated external PSP (payment service provider).

The gateway is deliberately flaky: it rejects a charge with probability
``failure_rate`` to exercise the resilience patterns (retry, circuit breaker)
of the orders orchestrator. The random source is *injected* as a callable so
tests substitute a deterministic stub — never a hard-wired ``random.random()``.
"""

import random
from collections.abc import Callable
from typing import Protocol

from app.logging import logger


class PspGateway(Protocol):
    """Contract for the payment gateway.

    ``failure_rate`` is a mutable attribute so the chaos endpoint can tune it
    at runtime (dev/demo only).
    """

    failure_rate: float

    def charge(self, order_id: str, amount: float, currency: str) -> bool: ...


class FlakyPspGateway:
    """PSP simulation failing with probability ``failure_rate`` (0.0 = always succeeds).

    ``rng`` must return a float in ``[0, 1)``; it defaults to ``random.random``
    in production and is replaced by a deterministic stub in tests.
    """

    def __init__(self, failure_rate: float = 0.0, rng: Callable[[], float] | None = None) -> None:
        self.failure_rate = failure_rate
        self._rng: Callable[[], float] = rng if rng is not None else random.random

    def charge(self, order_id: str, amount: float, currency: str) -> bool:
        success = self._rng() >= self.failure_rate
        logger.info(
            "psp_charge_attempted",
            order_id=order_id,
            amount=amount,
            currency=currency,
            failure_rate=self.failure_rate,
            success=success,
        )
        return success
