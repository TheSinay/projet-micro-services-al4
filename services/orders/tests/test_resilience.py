"""Tests for the home-made resilience module: circuit breaker and retry policy.

Fully deterministic: the breaker clock, the retry sleep and the jitter rng are all
injected — no real time passes, no network is involved.
"""

import asyncio

import httpx
import pytest

from app.services.resilience import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
    TransientDownstreamError,
    retry_async,
)


class Clock:
    """A manually advanced monotonic clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Probe:
    """Counts calls; fails with the given exception while ``failing`` is True."""

    def __init__(self, error: BaseException | None = None) -> None:
        self.calls = 0
        self.error = error

    async def __call__(self) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return "ok"


def _breaker(clock: Clock, threshold: int = 3) -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold=threshold,
        window_seconds=30.0,
        recovery_timeout=15.0,
        clock=clock,
        name="test",
    )


async def _fail_n_times(breaker: CircuitBreaker, n: int) -> None:
    probe = Probe(TransientDownstreamError("boom"))
    for _ in range(n):
        with pytest.raises(TransientDownstreamError):
            await breaker.call(probe)


# --------------------------------------------------------------------- breaker


async def test_breaker_stays_closed_below_threshold() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 2)
    assert breaker.state is CircuitState.CLOSED


async def test_breaker_opens_after_threshold_failures() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    assert breaker.state is CircuitState.OPEN


async def test_open_breaker_fails_fast_without_calling() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    probe = Probe()
    with pytest.raises(CircuitOpenError):
        await breaker.call(probe)
    assert probe.calls == 0  # fail fast: the function was never invoked


async def test_breaker_half_opens_after_recovery_timeout() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    clock.advance(14.9)
    assert breaker.state is CircuitState.OPEN
    clock.advance(0.2)
    assert breaker.state is CircuitState.HALF_OPEN  # type: ignore[comparison-overlap]


async def test_half_open_success_closes_the_circuit() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    clock.advance(15.0)
    assert await breaker.call(Probe()) == "ok"
    assert breaker.state is CircuitState.CLOSED
    # The failure history was reset: one new failure does not re-open.
    await _fail_n_times(breaker, 1)
    assert breaker.state is CircuitState.CLOSED


async def test_half_open_failure_reopens_the_circuit() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    clock.advance(15.0)
    await _fail_n_times(breaker, 1)  # the single trial fails
    assert breaker.state is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await breaker.call(Probe())


async def test_half_open_allows_a_single_trial() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 3)
    clock.advance(15.0)

    gate = asyncio.Event()

    async def slow_success() -> str:
        await gate.wait()
        return "ok"

    trial = asyncio.create_task(breaker.call(slow_success))
    await asyncio.sleep(0)  # let the trial enter the breaker
    with pytest.raises(CircuitOpenError):
        await breaker.call(Probe())  # a concurrent call is rejected
    gate.set()
    assert await trial == "ok"
    assert breaker.state is CircuitState.CLOSED


async def test_failure_window_is_sliding() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 2)
    clock.advance(31.0)  # both failures leave the 30 s window
    await _fail_n_times(breaker, 1)
    assert breaker.state is CircuitState.CLOSED  # only 1 failure in the window
    await _fail_n_times(breaker, 2)
    assert breaker.state is CircuitState.OPEN  # type: ignore[comparison-overlap]  # 3 failures within the window


async def test_success_clears_the_failure_history_when_closed() -> None:
    clock = Clock()
    breaker = _breaker(clock)
    await _fail_n_times(breaker, 2)
    assert await breaker.call(Probe()) == "ok"
    await _fail_n_times(breaker, 2)
    assert breaker.state is CircuitState.CLOSED


async def test_unrecorded_exceptions_do_not_trip_the_breaker() -> None:
    clock = Clock()
    breaker = _breaker(clock, threshold=1)
    with pytest.raises(ValueError):
        await breaker.call(Probe(ValueError("business error")))
    assert breaker.state is CircuitState.CLOSED  # a 4xx-like error is not a breaker failure


# ----------------------------------------------------------------------- retry


class SleepRecorder:
    """Records requested delays instead of sleeping."""

    def __init__(self) -> None:
        self.delays: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.delays.append(delay)


async def test_retry_returns_immediately_on_success() -> None:
    probe = Probe()
    sleeps = SleepRecorder()
    result = await retry_async(probe, sleep=sleeps, rng=lambda: 0.5)
    assert result == "ok"
    assert probe.calls == 1
    assert sleeps.delays == []


async def test_retry_retries_transient_errors_then_succeeds() -> None:
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TransientDownstreamError("psp down")
        return "ok"

    sleeps = SleepRecorder()
    result = await retry_async(flaky, base_delay=1.0, sleep=sleeps, rng=lambda: 0.5)
    assert result == "ok"
    assert calls == 3
    # Exponential backoff with rng=0.5 -> jitter factor exactly 1.0.
    assert sleeps.delays == [1.0, 2.0]


async def test_retry_retries_timeouts() -> None:
    probe = Probe(httpx.ConnectTimeout("timed out"))
    sleeps = SleepRecorder()
    with pytest.raises(httpx.ConnectTimeout):
        await retry_async(probe, sleep=sleeps, rng=lambda: 0.5)
    assert probe.calls == 3


async def test_retry_gives_up_after_max_attempts() -> None:
    probe = Probe(TransientDownstreamError("still down"))
    sleeps = SleepRecorder()
    with pytest.raises(TransientDownstreamError):
        await retry_async(probe, attempts=3, sleep=sleeps, rng=lambda: 0.5)
    assert probe.calls == 3
    assert len(sleeps.delays) == 2  # no sleep after the final attempt


async def test_retry_never_retries_client_errors() -> None:
    probe = Probe(ValueError("a 4xx-like error"))
    sleeps = SleepRecorder()
    with pytest.raises(ValueError):
        await retry_async(probe, sleep=sleeps, rng=lambda: 0.5)
    assert probe.calls == 1  # no retry on non-transient errors
    assert sleeps.delays == []


async def test_retry_backoff_is_capped_and_jittered() -> None:
    probe = Probe(TransientDownstreamError("down"))
    sleeps = SleepRecorder()
    with pytest.raises(TransientDownstreamError):
        await retry_async(
            probe,
            attempts=4,
            base_delay=1.0,
            max_delay=2.5,
            sleep=sleeps,
            rng=lambda: 0.0,  # jitter factor 0.5
        )
    # Raw backoff [1.0, 2.0, 4.0->capped 2.5] scaled by 0.5.
    assert sleeps.delays == [0.5, 1.0, 1.25]
