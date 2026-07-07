"""Unit tests for the simulated PSP gateway (injected random source)."""

from app.services.psp import FlakyPspGateway
from tests.conftest import StubRng


def test_charge_fails_when_draw_below_failure_rate() -> None:
    gateway = FlakyPspGateway(failure_rate=0.5, rng=StubRng([0.49, 0.5, 0.51]))
    assert gateway.charge("order-x", 10.0, "EUR") is False
    assert gateway.charge("order-x", 10.0, "EUR") is True
    assert gateway.charge("order-x", 10.0, "EUR") is True


def test_default_random_source_respects_rate_bounds() -> None:
    # random.random() lives in [0, 1): rate 0.0 always succeeds, rate 1.0 always fails.
    assert FlakyPspGateway(failure_rate=0.0).charge("order-y", 10.0, "EUR") is True
    assert FlakyPspGateway(failure_rate=1.0).charge("order-y", 10.0, "EUR") is False
