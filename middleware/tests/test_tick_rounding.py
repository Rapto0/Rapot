from __future__ import annotations

from decimal import Decimal

from middleware.risk.tick import TickPolicy, round_down_to_tick, round_up_to_tick


def test_round_up_to_tick():
    assert round_up_to_tick(Decimal("287.251"), Decimal("0.05")) == Decimal("287.30")


def test_round_down_to_tick():
    assert round_down_to_tick(Decimal("287.251"), Decimal("0.05")) == Decimal("287.25")


def test_tick_policy_uses_symbol_override():
    policy = TickPolicy(default_tick=Decimal("0.01"), symbol_overrides={"THYAO": Decimal("0.05")})
    limit = policy.buy_limit_price("THYAO", Decimal("100"), buy_bps=10)
    assert limit == Decimal("100.10")
