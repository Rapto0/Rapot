from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from middleware.domain.enums import OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload

_STATUS_MAP: dict[str, OrderStatus] = {
    "submitted": OrderStatus.SUBMITTED,
    "accepted": OrderStatus.ACKNOWLEDGED,
    "acknowledged": OrderStatus.ACKNOWLEDGED,
    "partial_fill": OrderStatus.PARTIALLY_FILLED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "cancelled": OrderStatus.CANCELLED,
    "rejected": OrderStatus.FAILED,
    "failed": OrderStatus.FAILED,
}


@dataclass(slots=True, frozen=True)
class OsmanliSubmitOrderEnvelope:
    """
    Placeholder transport envelope for Osmanli integration.

    This is intentionally generic and MUST be reconciled with official Osmanli docs
    before live transport is enabled.
    """

    endpoint_hint: str
    method: str
    headers: dict[str, str]
    body: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OsmanliOrderMapper:
    mapper_version = "draft-2026-04"

    def build_submit_order_envelope(
        self,
        payload: BrokerOrderRequestPayload,
        *,
        account_id: str | None,
    ) -> OsmanliSubmitOrderEnvelope:
        client_order_id = payload.idempotency_key[:32]
        body: dict[str, Any] = {
            "symbol": payload.symbol,
            "side": payload.side.value,
            "order_type": "LIMIT",
            "lots": payload.lots,
            "limit_price": str(payload.limit_price),
            "time_in_force": payload.tif,
            "client_order_id": client_order_id,
            "signal_code": payload.signal_code,
        }
        if account_id:
            body["account_id"] = account_id

        headers = {
            "x-idempotency-key": payload.idempotency_key,
            "x-mapper-version": self.mapper_version,
        }
        return OsmanliSubmitOrderEnvelope(
            endpoint_hint="TODO_OFFICIAL_SUBMIT_ORDER_ENDPOINT",
            method="POST",
            headers=headers,
            body=body,
        )

    @staticmethod
    def map_external_status(status_text: str | None) -> OrderStatus:
        key = (status_text or "").strip().lower()
        return _STATUS_MAP.get(key, OrderStatus.FAILED)
