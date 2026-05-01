from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from middleware.domain.constants import (
    SIGNAL_SIDE_MAP,
    SUPPORTED_SIGNAL_CODES,
    SUPPORTED_SIGNAL_SOURCES,
    TRADINGVIEW_SCHEMA_VERSION,
)
from middleware.domain.enums import OrderStatus, Side, TrancheStatus


class TradingViewWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schemaVersion: Literal[1] = TRADINGVIEW_SCHEMA_VERSION
    source: str = Field(min_length=1, max_length=120)
    symbol: str = Field(min_length=1, max_length=24)
    ticker: str = Field(min_length=1, max_length=24)
    signalCode: str = Field(min_length=3, max_length=20)
    signalText: str = Field(min_length=1, max_length=200)
    side: Side
    price: Decimal = Field(gt=0)
    timeframe: str = Field(min_length=1, max_length=24)
    barTime: int = Field(gt=0)
    barIndex: int = Field(ge=0)
    isRealtime: bool

    @field_validator("symbol", "ticker")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized.isascii():
            raise ValueError("symbol/ticker must be ASCII")
        if not normalized.replace(".", "").replace("-", "").isalnum():
            raise ValueError("symbol/ticker contains invalid characters")
        return normalized

    @field_validator("signalCode")
    @classmethod
    def normalize_signal_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in SUPPORTED_SIGNAL_CODES:
            raise ValueError(f"unsupported signalCode: {normalized}")
        return normalized

    @field_validator("source")
    @classmethod
    def normalize_source(cls, value: str) -> str:
        normalized = value.strip()
        canonical = next(
            (item for item in SUPPORTED_SIGNAL_SOURCES if item.lower() == normalized.lower()),
            None,
        )
        if canonical is None:
            raise ValueError(f"unsupported source: {normalized}")
        return canonical

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("timeframe cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_cross_fields(self) -> TradingViewWebhookPayload:
        if self.symbol != self.ticker:
            raise ValueError("symbol and ticker must match for BIST equity flow")

        expected_side = SIGNAL_SIDE_MAP[self.signalCode]
        if self.side != expected_side:
            raise ValueError(
                f"side does not match signalCode mapping: {self.signalCode} -> {expected_side.value}"
            )
        return self


class ProcessSignalResponse(BaseModel):
    signal_event_id: int
    order_id: int | None = None
    duplicate: bool
    status: OrderStatus | None = None
    message: str
    risk_reason: str | None = None
    broker_order_id: str | None = None


class OsmanliProxyResponse(BaseModel):
    forward_enabled: bool
    forwarded: bool
    forward_status_code: int | None = None
    forward_error: str | None = None
    message: str
    extracted_signal: TradingViewWebhookPayload
    process_result: ProcessSignalResponse


class PositionItem(BaseModel):
    symbol: str
    open_tranche_count: int
    total_remaining_lots: int
    total_remaining_quantity: Decimal = Decimal("0")
    weighted_avg_entry_price: Decimal | None = None


class TrancheItem(BaseModel):
    id: int
    symbol: str
    signal_code: str
    entry_price: Decimal
    entry_time: datetime
    requested_lots: int
    filled_lots: int
    remaining_lots: int
    requested_quantity: Decimal = Decimal("0")
    filled_quantity: Decimal = Decimal("0")
    remaining_quantity: Decimal = Decimal("0")
    status: TrancheStatus
    open_order_id: int | None = None
    close_order_id: int | None = None


class OrderItem(BaseModel):
    id: int
    signal_event_id: int
    idempotency_key: str
    symbol: str
    side: Side
    signal_code: str
    requested_lots: int
    filled_lots: int
    requested_quantity: Decimal = Decimal("0")
    filled_quantity: Decimal = Decimal("0")
    limit_price: Decimal
    budget_tl: Decimal | None = None
    quote_budget: Decimal | None = None
    status: OrderStatus
    rejection_reason: str | None = None
    broker_name: str
    broker_order_id: str | None = None
    base_asset: str | None = None
    quote_asset: str | None = None
    target_tranche_id: int | None = None
    created_at: datetime
    updated_at: datetime
    realized_pnl: Decimal | None = None


class SignalItem(BaseModel):
    id: int
    event_hash: str
    schema_version: int
    source: str
    symbol: str
    ticker: str
    signal_code: str
    signal_text: str
    side: Side
    price: Decimal
    timeframe: str
    bar_time: datetime
    bar_index: int
    is_realtime: bool
    received_at: datetime


class ReplaySignalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload: TradingViewWebhookPayload
    bypass_idempotency: bool = False


class SimulateFillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: int = Field(gt=0)
    filled_lots: int | None = Field(default=None, ge=1)
    fill_price: Decimal | None = Field(default=None, gt=0)


class HealthResponse(BaseModel):
    status: str
    app: str
    now: datetime
    trading_enabled: bool
    execution_mode: str
    broker: str


class BrokerOrderRequestPayload(BaseModel):
    """
    Neutral order payload passed from domain layer to adapters.
    """

    symbol: str
    side: Side
    lots: int
    quantity: Decimal | None = None
    limit_price: Decimal
    tif: str = "IOC"
    signal_code: str
    idempotency_key: str
    metadata: dict[str, Any] = Field(default_factory=dict)
