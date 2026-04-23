from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal


@dataclass(slots=True)
class BuySizingResult:
    signal_budget_tl: Decimal
    limit_price: Decimal
    buy_lots: int


def compute_signal_budget(base_budget_tl: Decimal, multiplier: Decimal) -> Decimal:
    return base_budget_tl * multiplier


def compute_buy_lots(signal_budget_tl: Decimal, buy_limit_price: Decimal) -> int:
    if buy_limit_price <= 0:
        return 0
    lots = (signal_budget_tl / buy_limit_price).to_integral_value(rounding=ROUND_FLOOR)
    return int(lots)
