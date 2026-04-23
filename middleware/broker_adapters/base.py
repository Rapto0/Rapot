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
    filled_lots: int = 0
    avg_fill_price: Decimal | None = None
    message: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class BrokerClient(ABC):
    name: str

    @abstractmethod
    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        raise NotImplementedError
