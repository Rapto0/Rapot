from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal


def _to_decimal(value: Decimal | float | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def round_up_to_tick(
    price: Decimal | float | int | str, tick_size: Decimal | float | int | str
) -> Decimal:
    price_dec = _to_decimal(price)
    tick_dec = _to_decimal(tick_size)
    if tick_dec <= 0:
        raise ValueError("tick_size must be positive")
    units = (price_dec / tick_dec).to_integral_value(rounding=ROUND_CEILING)
    return units * tick_dec


def round_down_to_tick(
    price: Decimal | float | int | str, tick_size: Decimal | float | int | str
) -> Decimal:
    price_dec = _to_decimal(price)
    tick_dec = _to_decimal(tick_size)
    if tick_dec <= 0:
        raise ValueError("tick_size must be positive")
    units = (price_dec / tick_dec).to_integral_value(rounding=ROUND_FLOOR)
    return units * tick_dec


@dataclass(slots=True)
class TickPolicy:
    default_tick: Decimal
    symbol_overrides: dict[str, Decimal]

    def get_tick_size(self, symbol: str) -> Decimal:
        return self.symbol_overrides.get(symbol.upper(), self.default_tick)

    def buy_limit_price(self, symbol: str, close_price: Decimal, buy_bps: int) -> Decimal:
        raw_price = close_price * (Decimal("1") + (Decimal(buy_bps) / Decimal("10000")))
        return round_up_to_tick(raw_price, self.get_tick_size(symbol))

    def sell_limit_price(self, symbol: str, close_price: Decimal, sell_bps: int) -> Decimal:
        raw_price = close_price * (Decimal("1") - (Decimal(sell_bps) / Decimal("10000")))
        return round_down_to_tick(raw_price, self.get_tick_size(symbol))
