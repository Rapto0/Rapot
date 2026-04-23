from __future__ import annotations

from dataclasses import dataclass, field

from middleware.broker_adapters.base import BrokerClient, BrokerOrderResult
from middleware.broker_adapters.osmanli_mapper import OsmanliOrderMapper
from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.settings import MiddlewareSettings


@dataclass(slots=True)
class OsmanliBrokerClient(BrokerClient):
    """
    Osmanli adapter skeleton.

    IMPORTANT:
    - Live auth/session/order routing must follow official Osmanli docs.
    - This class intentionally does not assume undocumented payloads or token flows.
    """

    cfg: MiddlewareSettings
    mapper: OsmanliOrderMapper = field(default_factory=OsmanliOrderMapper)
    name: str = "OSMANLI"

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        mapped_request = self.mapper.build_submit_order_envelope(
            payload, account_id=self.cfg.osmanli_account_id
        )
        live_gate_message = (
            "Osmanli live adapter disabled by config. "
            "Set MW_OSMANLI_LIVE_ENABLED=true only after official UAT sign-off."
        )
        if self.cfg.osmanli_live_enabled:
            live_gate_message = (
                "Osmanli live transport is not implemented yet. "
                "Wire official auth/order flow based on broker documentation."
            )

        return BrokerOrderResult(
            accepted=False,
            status=OrderStatus.FAILED,
            broker_order_id=None,
            filled_lots=0,
            avg_fill_price=None,
            message=live_gate_message,
            raw_payload={
                "mapper_version": self.mapper.mapper_version,
                "mapped_request": mapped_request.to_dict(),
                "todo": [
                    "wire official Osmanli token/session bootstrap",
                    "map official submit response payload to internal status",
                    "implement official cancel and order status polling/callback flow",
                ],
            },
        )
