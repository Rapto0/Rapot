from __future__ import annotations

from decimal import Decimal

from middleware.broker_adapters.osmanli_mapper import OsmanliOrderMapper
from middleware.domain.enums import OrderStatus, Side
from middleware.domain.events import BrokerOrderRequestPayload


def test_osmanli_mapper_builds_submit_envelope():
    mapper = OsmanliOrderMapper()
    envelope = mapper.build_submit_order_envelope(
        BrokerOrderRequestPayload(
            symbol="THYAO",
            side=Side.BUY,
            lots=10,
            limit_price=Decimal("287.83"),
            signal_code="H_BLS",
            idempotency_key="abcdef1234567890abcdef1234567890abcdef12",
        ),
        account_id="ACC-001",
    )

    payload = envelope.to_dict()
    assert payload["method"] == "POST"
    assert payload["endpoint_hint"] == "TODO_OFFICIAL_SUBMIT_ORDER_ENDPOINT"
    assert payload["body"]["symbol"] == "THYAO"
    assert payload["body"]["lots"] == 10
    assert payload["body"]["account_id"] == "ACC-001"
    assert payload["headers"]["x-idempotency-key"] == "abcdef1234567890abcdef1234567890abcdef12"


def test_osmanli_mapper_status_mapping_defaults_to_failed():
    assert OsmanliOrderMapper.map_external_status("filled") == OrderStatus.FILLED
    assert OsmanliOrderMapper.map_external_status("unknown-status") == OrderStatus.FAILED
