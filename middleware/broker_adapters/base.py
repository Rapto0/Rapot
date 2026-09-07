from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload


@dataclass(slots=True)
class BrokerOrderResult:
    accepted: bool
    status: OrderStatus
    broker_order_id: str | None = None
    client_order_id: str | None = None
    filled_lots: int = 0
    filled_quantity: Decimal = Decimal("0")
    avg_fill_price: Decimal | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)
    execution_uncertain: bool = False


@dataclass(frozen=True, slots=True)
class BrokerAssetBalance:
    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        return self.free + self.locked


class BrokerClient(ABC):
    name: str

    @abstractmethod
    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        raise NotImplementedError

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        raise NotImplementedError("broker adapter does not support order recovery")
