from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from middleware.broker_adapters.base import BrokerClient, BrokerOrderResult
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload


@dataclass(slots=True)
class MockBrokerClient(BrokerClient):
    auto_fill: bool = True
    name: str = "MOCK"

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        broker_order_id = f"MOCK-{uuid4().hex[:12].upper()}"
        timestamp = datetime.now(UTC).isoformat()

        raw: dict[str, Any] = {
            "broker": self.name,
            "broker_order_id": broker_order_id,
            "symbol": payload.symbol,
            "side": payload.side.value,
            "lots": payload.lots,
            "limit_price": str(payload.limit_price),
            "tif": payload.tif,
            "idempotency_key": payload.idempotency_key,
            "received_at": timestamp,
        }

        if self.auto_fill:
            raw["note"] = "mock auto-fill enabled"
            return BrokerOrderResult(
                accepted=True,
                status=OrderStatus.FILLED,
                broker_order_id=broker_order_id,
                filled_lots=payload.lots,
                avg_fill_price=payload.limit_price,
                message="mock order filled instantly",
                raw_payload=raw,
            )

        raw["note"] = "mock accepted without fill"
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.ACKNOWLEDGED,
            broker_order_id=broker_order_id,
            filled_lots=0,
            avg_fill_price=None,
            message="mock order acknowledged",
            raw_payload=raw,
        )
