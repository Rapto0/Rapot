from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from middleware.domain.constants import BUY_SIGNAL_CODES, SELL_SIGNAL_CODES, SUPPORTED_SIGNAL_CODES
from middleware.domain.enums import ExecutionMode, Side
from middleware.domain.errors import RiskRejection
from middleware.infra.settings import MiddlewareSettings

_BIST_SYMBOL_RE = re.compile(r"^[A-Z0-9.-]{1,24}$")


@dataclass(slots=True)
class BuyRiskInput:
    symbol: str
    signal_code: str
    side: Side
    buy_lots: int
    buy_limit_price: Decimal
    open_tranche_count: int
    symbol_exposure_tl: Decimal
    orders_today: int
    realized_pnl_today: Decimal


@dataclass(slots=True)
class SellRiskInput:
    symbol: str
    signal_code: str
    side: Side
    sell_lots: int
    open_tranche_exists: bool
    orders_today: int
    realized_pnl_today: Decimal


class RiskEngine:
    def __init__(self, cfg: MiddlewareSettings):
        self.cfg = cfg

    def _validate_common(
        self,
        *,
        symbol: str,
        signal_code: str,
        side: Side,
        orders_today: int,
        realized_pnl_today: Decimal,
    ) -> None:
        if signal_code not in SUPPORTED_SIGNAL_CODES:
            raise RiskRejection(f"unsupported signal code: {signal_code}")

        if not _BIST_SYMBOL_RE.match(symbol):
            raise RiskRejection("invalid symbol format")

        if self.cfg.allowed_symbols and symbol not in self.cfg.allowed_symbols:
            raise RiskRejection(f"symbol is not in allowed universe: {symbol}")

        if signal_code in BUY_SIGNAL_CODES and side != Side.BUY:
            raise RiskRejection("signal/side mismatch for BUY signal")

        if signal_code in SELL_SIGNAL_CODES and side != Side.SELL:
            raise RiskRejection("signal/side mismatch for SELL signal")

        if self.cfg.max_orders_per_day is not None and orders_today >= self.cfg.max_orders_per_day:
            raise RiskRejection("max_orders_per_day guard triggered")

        if self.cfg.max_daily_loss_tl is not None and realized_pnl_today <= (
            Decimal("0") - self.cfg.max_daily_loss_tl
        ):
            raise RiskRejection("max_daily_loss_tl guard triggered")

    def validate_buy(self, payload: BuyRiskInput) -> None:
        self._validate_common(
            symbol=payload.symbol,
            signal_code=payload.signal_code,
            side=payload.side,
            orders_today=payload.orders_today,
            realized_pnl_today=payload.realized_pnl_today,
        )

        if payload.buy_lots < 1:
            raise RiskRejection("buy_lots < 1")

        if payload.open_tranche_count >= self.cfg.max_open_tranches_per_symbol:
            raise RiskRejection(
                f"max open tranches exceeded (max={self.cfg.max_open_tranches_per_symbol})"
            )

        if self.cfg.max_symbol_exposure_tl is not None:
            incoming_exposure = Decimal(payload.buy_lots) * payload.buy_limit_price
            if payload.symbol_exposure_tl + incoming_exposure > self.cfg.max_symbol_exposure_tl:
                raise RiskRejection("max_symbol_exposure_tl guard triggered")

        if self.cfg.execution_mode == ExecutionMode.LIVE and not self.cfg.trading_enabled:
            raise RiskRejection("trading disabled: set MW_TRADING_ENABLED=true for live mode")

    def validate_sell(self, payload: SellRiskInput) -> None:
        self._validate_common(
            symbol=payload.symbol,
            signal_code=payload.signal_code,
            side=payload.side,
            orders_today=payload.orders_today,
            realized_pnl_today=payload.realized_pnl_today,
        )

        if payload.sell_lots < 1:
            raise RiskRejection("sell lots < 1")

        if not payload.open_tranche_exists:
            raise RiskRejection("no open tranche to sell")

        if self.cfg.execution_mode == ExecutionMode.LIVE and not self.cfg.trading_enabled:
            raise RiskRejection("trading disabled: set MW_TRADING_ENABLED=true for live mode")
