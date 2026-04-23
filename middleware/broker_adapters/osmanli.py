from __future__ import annotations

from dataclasses import dataclass

from middleware.broker_adapters.base import BrokerClient, BrokerOrderResult
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload


@dataclass(slots=True)
class OsmanliBrokerClient(BrokerClient):
    """
    Osmanli adapter skeleton.

    IMPORTANT:
    - Live auth/session/order routing must follow official Osmanli docs.
    - This class intentionally does not assume undocumented payloads or token flows.
    """

    name: str = "OSMANLI"

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        return BrokerOrderResult(
            accepted=False,
            status=OrderStatus.FAILED,
            broker_order_id=None,
            filled_lots=0,
            avg_fill_price=None,
            message=(
                "Osmanli live adapter is TODO. "
                "Implement official auth/order flow based on broker documentation."
            ),
            raw_payload={
                "symbol": payload.symbol,
                "side": payload.side.value,
                "lots": payload.lots,
                "limit_price": str(payload.limit_price),
                "todo": "Wire official Osmanli API client",
            },
        )
