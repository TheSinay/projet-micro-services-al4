"""Home-made resilience patterns for the saga orchestrator (ADR 0007).

This module is self-contained and hermetically testable:

- :class:`CircuitBreaker` — CLOSED / OPEN / HALF_OPEN state machine with a sliding
  failure window and an injectable clock (``time.monotonic`` by default);
- :func:`retry_async` — bounded retries with exponential backoff + jitter, with
  injectable ``sleep`` and ``rng`` so tests never wait nor depend on randomness.

Retries are only ever triggered by *transient* failures (timeout, network error,
5xx translated to :class:`TransientDownstreamError` by the HTTP clients) — never
by a 4xx: a client error does not heal by retrying.

Per ADR 0007 the module lives inside the orders service and is never imported by
another service (no shared business code between services).
"""

import asyncio
import random
import time
from collections import deque
from collections.abc import Awaitable, Callable
from enum import StrEnum

import httpx

from app.logging import logger


class CircuitOpenError(Exception):
    """Raised when the circuit is OPEN: fail fast, no network call is attempted."""


class TransientDownstreamError(Exception):
    """A retryable downstream failure (5xx answer from a downstream service)."""


# Failures worth retrying / recording by the breaker: timeouts, network errors, 5xx.
# httpx.TimeoutException is a subclass of httpx.TransportError; kept explicit for clarity.
RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    httpx.TimeoutException,
    httpx.TransportError,
    TransientDownstreamError,
)


class CircuitState(StrEnum):
    """The three states of the circuit breaker."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """Process-local circuit breaker (CLOSED -> OPEN -> HALF_OPEN, ADR 0007).

    - CLOSED: calls go through; failures are recorded in a sliding window
      (``window_seconds``); reaching ``failure_threshold`` failures within the
      window trips the circuit OPEN. A success clears the window.
    - OPEN: every call fails immediately with :class:`CircuitOpenError` (fail
      fast, no network I/O). After ``recovery_timeout`` seconds the circuit
      becomes HALF_OPEN.
    - HALF_OPEN: exactly ONE trial call goes through (concurrent calls fail
      fast); a success closes the circuit, a failure re-opens it.

    Only exceptions listed in ``record_on`` count as failures (a 4xx business
    error must not trip the breaker); other exceptions propagate untouched.
    The clock is injectable for deterministic tests.
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        window_seconds: float = 30.0,
        recovery_timeout: float = 15.0,
        clock: Callable[[], float] = time.monotonic,
        record_on: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
        name: str = "circuit",
    ) -> None:
        self._failure_threshold = failure_threshold
        self._window_seconds = window_seconds
        self._recovery_timeout = recovery_timeout
        self._clock = clock
        self._record_on = record_on
        self._name = name
        self._state = CircuitState.CLOSED
        self._failures: deque[float] = deque()
        self._opened_at = 0.0
        self._trial_in_flight = False

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for the time-based OPEN -> HALF_OPEN move."""
        if (
            self._state is CircuitState.OPEN
            and self._clock() - self._opened_at >= self._recovery_timeout
        ):
            return CircuitState.HALF_OPEN
        return self._state

    async def call[T](self, func: Callable[[], Awaitable[T]]) -> T:
        """Run ``func`` under the breaker policy; raise CircuitOpenError when OPEN."""
        state = self.state
        if state is CircuitState.OPEN:
            raise CircuitOpenError(f"circuit '{self._name}' is open (failing fast)")
        if state is CircuitState.HALF_OPEN:
            return await self._trial(func)
        try:
            result = await func()
        except self._record_on:
            self._record_failure()
            raise
        self._failures.clear()
        return result

    async def _trial[T](self, func: Callable[[], Awaitable[T]]) -> T:
        """HALF_OPEN: let exactly one trial through; success closes, failure re-opens."""
        if self._trial_in_flight:
            raise CircuitOpenError(f"circuit '{self._name}' is half-open (trial in flight)")
        self._state = CircuitState.HALF_OPEN
        self._trial_in_flight = True
        try:
            result = await func()
        except self._record_on:
            self._trip()
            raise
        else:
            self._reset()
            return result
        finally:
            self._trial_in_flight = False

    def _record_failure(self) -> None:
        now = self._clock()
        self._failures.append(now)
        cutoff = now - self._window_seconds
        while self._failures and self._failures[0] <= cutoff:
            self._failures.popleft()
        if len(self._failures) >= self._failure_threshold:
            self._trip()

    def _trip(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()
        self._failures.clear()
        logger.warning("circuit_opened", circuit=self._name)

    def _reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failures.clear()
        logger.info("circuit_closed", circuit=self._name)


async def retry_async[T](
    func: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = RETRYABLE_EXCEPTIONS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    rng: Callable[[], float] = random.random,
) -> T:
    """Call ``func`` up to ``attempts`` times with exponential backoff + jitter.

    Only exceptions listed in ``retry_on`` (transient failures: timeout, network
    error, 5xx) are retried; anything else — a 4xx in particular — propagates
    immediately. The delay before attempt ``n+1`` is
    ``min(base_delay * 2**(n-1), max_delay) * (0.5 + rng())`` (full jitter in
    [0.5x, 1.5x)). ``sleep`` and ``rng`` are injectable for deterministic tests.
    """
    last_error: BaseException | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await func()
        except retry_on as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = min(base_delay * 2 ** (attempt - 1), max_delay) * (0.5 + rng())
            logger.warning(
                "retrying_call",
                attempt=attempt,
                max_attempts=attempts,
                delay_seconds=round(delay, 3),
                error=str(exc),
            )
            await sleep(delay)
    assert last_error is not None  # attempts >= 1, so the loop set it before breaking
    raise last_error
