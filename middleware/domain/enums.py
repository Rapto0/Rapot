from __future__ import annotations

from enum import Enum


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ExecutionMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    LIVE = "LIVE"


class BrokerName(str, Enum):
    MOCK = "MOCK"
    OSMANLI = "OSMANLI"
    BINANCE_SPOT = "BINANCE_SPOT"


class OrderStatus(str, Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    REJECTED = "rejected"
    SUBMITTED = "submitted"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TrancheStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class MarketType(str, Enum):
    EQUITY = "EQUITY"
    CRYPTO_SPOT = "CRYPTO_SPOT"
