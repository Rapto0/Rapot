from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import Any


def _decimal(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def floor_to_step(value: Decimal, step_size: Decimal) -> Decimal:
    if step_size <= 0:
        return value
    units = (value / step_size).to_integral_value(rounding=ROUND_FLOOR)
    return units * step_size


def ceil_to_step(value: Decimal, step_size: Decimal) -> Decimal:
    if step_size <= 0:
        return value
    units = (value / step_size).to_integral_value(rounding=ROUND_CEILING)
    return units * step_size


@dataclass(slots=True, frozen=True)
class BinanceSymbolRules:
    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    tick_size: Decimal
    min_price: Decimal
    max_price: Decimal
    step_size: Decimal
    min_qty: Decimal
    max_qty: Decimal
    min_notional: Decimal
    max_notional: Decimal | None = None

    @classmethod
    def from_exchange_info_symbol(cls, raw: dict[str, Any]) -> BinanceSymbolRules:
        filters = {item.get("filterType"): item for item in raw.get("filters", [])}
        price_filter = filters.get("PRICE_FILTER", {})
        lot_filter = filters.get("LOT_SIZE", {})
        min_notional_filter = filters.get("MIN_NOTIONAL", {})
        notional_filter = filters.get("NOTIONAL", {})

        min_notional = _decimal(
            notional_filter.get("minNotional", min_notional_filter.get("minNotional")),
            "0",
        )
        max_notional_raw = notional_filter.get("maxNotional")
        max_notional = _decimal(max_notional_raw) if max_notional_raw not in (None, "") else None

        return cls(
            symbol=str(raw.get("symbol", "")).upper(),
            status=str(raw.get("status", "")),
            base_asset=str(raw.get("baseAsset", "")),
            quote_asset=str(raw.get("quoteAsset", "")),
            tick_size=_decimal(price_filter.get("tickSize"), "0"),
            min_price=_decimal(price_filter.get("minPrice"), "0"),
            max_price=_decimal(price_filter.get("maxPrice"), "0"),
            step_size=_decimal(lot_filter.get("stepSize"), "0"),
            min_qty=_decimal(lot_filter.get("minQty"), "0"),
            max_qty=_decimal(lot_filter.get("maxQty"), "0"),
            min_notional=min_notional,
            max_notional=max_notional,
        )

    def round_buy_price(self, price: Decimal) -> Decimal:
        return ceil_to_step(price, self.tick_size)

    def round_sell_price(self, price: Decimal) -> Decimal:
        return floor_to_step(price, self.tick_size)

    def floor_quantity(self, quantity: Decimal) -> Decimal:
        return floor_to_step(quantity, self.step_size)

    def validate_limit_order(self, *, price: Decimal, quantity: Decimal) -> str | None:
        if self.status != "TRADING":
            return f"Binance symbol is not trading: {self.symbol}"

        if quantity <= 0:
            return "Binance quantity must be > 0"
        if self.min_qty > 0 and quantity < self.min_qty:
            return f"Binance quantity below LOT_SIZE.minQty ({self.min_qty})"
        if self.max_qty > 0 and quantity > self.max_qty:
            return f"Binance quantity above LOT_SIZE.maxQty ({self.max_qty})"
        if self.step_size > 0 and quantity != self.floor_quantity(quantity):
            return f"Binance quantity does not align with LOT_SIZE.stepSize ({self.step_size})"

        if price <= 0:
            return "Binance limit price must be > 0"
        if self.min_price > 0 and price < self.min_price:
            return f"Binance price below PRICE_FILTER.minPrice ({self.min_price})"
        if self.max_price > 0 and price > self.max_price:
            return f"Binance price above PRICE_FILTER.maxPrice ({self.max_price})"
        if self.tick_size > 0 and price != floor_to_step(price, self.tick_size):
            return f"Binance price does not align with PRICE_FILTER.tickSize ({self.tick_size})"

        notional = price * quantity
        if self.min_notional > 0 and notional < self.min_notional:
            return f"Binance notional below minimum ({self.min_notional})"
        if self.max_notional is not None and self.max_notional > 0 and notional > self.max_notional:
            return f"Binance notional above maximum ({self.max_notional})"
        return None
