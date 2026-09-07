from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from unittest.mock import Mock

import requests
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerOrderResult
from middleware.broker_adapters.binance_spot import BinanceAPIError, BinanceSpotBrokerClient
from middleware.domain.enums import ExecutionMode, OrderStatus, Side
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.domain.idempotency import build_client_order_id
from middleware.infra.db import get_session_local
from middleware.infra.models import ExecutionReport
from middleware.infra.settings import settings
from middleware.repositories.order_repository import OrderRepository
from middleware.risk.binance_filters import BinanceSymbolRules


def _rules(symbol: str) -> BinanceSymbolRules:
    return BinanceSymbolRules(
        symbol=symbol.upper(),
        status="TRADING",
        base_asset=symbol.upper().removesuffix("USDT"),
        quote_asset="USDT",
        tick_size=Decimal("0.01"),
        min_price=Decimal("0.01"),
        max_price=Decimal("1000000"),
        step_size=Decimal("0.000001"),
        min_qty=Decimal("0.000001"),
        max_qty=Decimal("1000"),
        min_notional=Decimal("5"),
    )


def _payload(*, signal_code: str, side: str, bar_index: int) -> dict:
    return {
        "source": "Combo+Hunter",
        "symbol": "BTCUSDT",
        "ticker": "BTCUSDT",
        "signalCode": signal_code,
        "signalText": signal_code,
        "side": side,
        "price": "50000",
        "timeframe": "1H",
        "barTime": 1713772800000 + (bar_index * 60000),
        "barIndex": bar_index,
        "isRealtime": True,
    }


@dataclass(slots=True)
class PartialTerminalBroker:
    name: str = "BINANCE_SPOT"
    zero_fill: bool = False

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return _rules(symbol)

    def get_asset_balance(self, asset: str) -> Decimal:
        return Decimal("1000")

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        return BrokerAssetBalance(asset=asset, free=Decimal("1000"), locked=Decimal("0"))

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        quantity = Decimal("0") if self.zero_fill else payload.quantity / Decimal("2")
        status = OrderStatus.CANCELLED if payload.side == Side.BUY else OrderStatus.EXPIRED
        return BrokerOrderResult(
            accepted=False,
            status=status,
            broker_order_id=f"TERMINAL-{payload.side.value}",
            client_order_id=payload.client_order_id,
            filled_quantity=quantity,
            avg_fill_price=payload.limit_price if quantity > 0 else None,
            message=f"terminal {status.value}",
            raw_payload={"executedQty": str(quantity)},
        )


@dataclass(slots=True)
class RecoveringBroker:
    name: str = "BINANCE_SPOT"
    submitted: BrokerOrderRequestPayload | None = None
    recovery_calls: int = 0

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return _rules(symbol)

    def get_asset_balance(self, asset: str) -> Decimal:
        return Decimal("1000")

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        return BrokerAssetBalance(asset=asset, free=Decimal("1000"), locked=Decimal("0"))

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        self.submitted = payload
        return BrokerOrderResult(
            accepted=False,
            status=OrderStatus.UNKNOWN,
            client_order_id=payload.client_order_id,
            message="submit timed out and lookup was inconclusive",
            execution_uncertain=True,
        )

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        assert self.submitted is not None
        assert symbol == self.submitted.symbol
        assert client_order_id == self.submitted.client_order_id
        self.recovery_calls += 1
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id="RECOVERED-1",
            client_order_id=client_order_id,
            filled_quantity=self.submitted.quantity,
            avg_fill_price=self.submitted.limit_price,
            message="recovered by client order id",
            raw_payload={"executedQty": str(self.submitted.quantity)},
        )


@dataclass(slots=True)
class IncrementalFillBroker:
    name: str = "BINANCE_SPOT"
    submitted: BrokerOrderRequestPayload | None = None

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        return _rules(symbol)

    def get_asset_balance(self, asset: str) -> Decimal:
        return Decimal("1000")

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        return BrokerAssetBalance(asset=asset, free=Decimal("1000"), locked=Decimal("0"))

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        self.submitted = payload
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.PARTIALLY_FILLED,
            broker_order_id="INCREMENTAL-1",
            client_order_id=payload.client_order_id,
            filled_quantity=payload.quantity / Decimal("2"),
            avg_fill_price=Decimal("49000"),
            message="first cumulative snapshot",
        )

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        assert self.submitted is not None
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id="INCREMENTAL-1",
            client_order_id=client_order_id,
            filled_quantity=self.submitted.quantity,
            avg_fill_price=Decimal("50000"),
            message="final cumulative snapshot",
        )


def test_partial_cancelled_buy_and_expired_sell_update_inventory_once(client, monkeypatch):
    broker = PartialTerminalBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0
    settings.sell_bps = 0

    buy = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=1),
    )
    assert buy.status_code == 200
    assert buy.json()["status"] == "cancelled"
    assert len(buy.json()["client_order_id"]) == 36
    position = client.get("/positions/BTCUSDT").json()["position"]
    assert Decimal(position["total_remaining_quantity"]) == Decimal("0.001")

    sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=2),
    )
    assert sell.status_code == 200
    assert sell.json()["status"] == "expired"
    position = client.get("/positions/BTCUSDT").json()["position"]
    assert Decimal(position["total_remaining_quantity"]) == Decimal("0.0005")

    duplicate_sell = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_PAH", side="SELL", bar_index=2),
    )
    assert duplicate_sell.json()["duplicate"] is True
    position = client.get("/positions/BTCUSDT").json()["position"]
    assert Decimal(position["total_remaining_quantity"]) == Decimal("0.0005")


def test_zero_fill_terminal_order_does_not_create_inventory(client, monkeypatch):
    broker = PartialTerminalBroker(zero_fill=True)
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0

    response = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=3),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert client.get("/positions/BTCUSDT").status_code == 404


def test_unknown_submit_can_be_recovered_repeatedly_without_double_fill(client, monkeypatch):
    broker = RecoveringBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0

    submitted = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=4),
    )
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "unknown"
    assert client.get("/positions/BTCUSDT").status_code == 404

    duplicate = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=4),
    )
    assert duplicate.json()["duplicate"] is True
    assert duplicate.json()["status"] == "unknown"

    order_id = submitted.json()["order_id"]
    first_recovery = client.post(f"/admin/recover-order/{order_id}")
    second_recovery = client.post(f"/admin/recover-order/{order_id}")
    assert first_recovery.status_code == second_recovery.status_code == 200
    assert first_recovery.json()["status"] == second_recovery.json()["status"] == "filled"
    assert broker.recovery_calls == 2
    position = client.get("/positions/BTCUSDT").json()["position"]
    assert Decimal(position["total_remaining_quantity"]) == Decimal("0.002")

    with get_session_local()() as session:
        recovery_reports = list(
            session.scalars(
                select(ExecutionReport)
                .where(
                    ExecutionReport.order_id == order_id,
                    ExecutionReport.event_type == "recovery",
                )
                .order_by(ExecutionReport.id)
            )
        )
    assert [report.payload_json["applied_delta_quantity"] for report in recovery_reports] == [
        "0.002000000000",
        "0E-12",
    ]


def test_cumulative_partial_snapshots_apply_only_increment_and_preserve_average(
    client, monkeypatch
):
    broker = IncrementalFillBroker()
    monkeypatch.setattr("middleware.api.dependencies.build_broker_client", lambda cfg: broker)
    settings.binance_buy_quote_amount_usdt = Decimal("100")
    settings.buy_bps = 0

    submitted = client.post(
        "/webhooks/tradingview",
        json=_payload(signal_code="H_BLS", side="BUY", bar_index=5),
    )
    assert submitted.json()["status"] == "partially_filled"
    order_id = submitted.json()["order_id"]

    client.post(f"/admin/recover-order/{order_id}")
    client.post(f"/admin/recover-order/{order_id}")

    position = client.get("/positions/BTCUSDT").json()
    assert Decimal(position["position"]["total_remaining_quantity"]) == Decimal("0.002")
    assert Decimal(position["tranches"][0]["entry_price"]) == Decimal("50000")


def test_binance_timeout_queries_by_client_order_id(monkeypatch):
    settings.execution_mode = ExecutionMode.LIVE
    settings.binance_live_enabled = True
    settings.binance_api_key = "test-api-key"
    settings.binance_secret_key = "test-secret-key"
    client = BinanceSpotBrokerClient(settings)
    calls: list[tuple[str, str, dict]] = []

    def fake_signed_request(self, method: str, path: str, params: dict):
        calls.append((method, path, params))
        if method == "POST":
            raise requests.Timeout("ambiguous timeout")
        return {
            "symbol": "BTCUSDT",
            "orderId": 42,
            "clientOrderId": params["origClientOrderId"],
            "status": "CANCELED",
            "executedQty": "0.001",
            "cummulativeQuoteQty": "50",
        }

    monkeypatch.setattr(BinanceSpotBrokerClient, "_signed_request", fake_signed_request)
    payload = BrokerOrderRequestPayload(
        symbol="BTCUSDT",
        side=Side.BUY,
        lots=0,
        quantity=Decimal("0.002"),
        limit_price=Decimal("50000"),
        signal_code="H_BLS",
        idempotency_key="intent-1",
        client_order_id=build_client_order_id("intent-1"),
    )

    result = client.submit_limit_order(payload)

    assert result.status == OrderStatus.CANCELLED
    assert result.filled_quantity == Decimal("0.001")
    assert result.avg_fill_price == Decimal("50000")
    assert calls[1][0:2] == ("GET", "/api/v3/order")
    assert calls[1][2]["origClientOrderId"] == payload.client_order_id


def test_binance_inconclusive_timeout_stays_unknown(monkeypatch):
    settings.execution_mode = ExecutionMode.LIVE
    settings.binance_live_enabled = True
    settings.binance_api_key = "test-api-key"
    settings.binance_secret_key = "test-secret-key"
    client = BinanceSpotBrokerClient(settings)

    def always_timeout(self, method: str, path: str, params: dict):
        raise requests.Timeout("still ambiguous")

    monkeypatch.setattr(BinanceSpotBrokerClient, "_signed_request", always_timeout)
    payload = BrokerOrderRequestPayload(
        symbol="BTCUSDT",
        side=Side.BUY,
        lots=0,
        quantity=Decimal("0.002"),
        limit_price=Decimal("50000"),
        signal_code="H_BLS",
        idempotency_key="intent-2",
        client_order_id=build_client_order_id("intent-2"),
    )

    result = client.submit_limit_order(payload)

    assert result.status == OrderStatus.UNKNOWN
    assert result.execution_uncertain is True
    assert result.client_order_id == payload.client_order_id


def test_binance_duplicate_client_id_recovers_order_after_restart(monkeypatch):
    settings.execution_mode = ExecutionMode.LIVE
    settings.binance_live_enabled = True
    settings.binance_api_key = "test-api-key"
    settings.binance_secret_key = "test-secret-key"
    client = BinanceSpotBrokerClient(settings)

    def duplicate_then_lookup(self, method: str, path: str, params: dict):
        if method == "POST":
            raise BinanceAPIError(status_code=400, code=-2010, message="Duplicate order sent.")
        return {
            "symbol": "BTCUSDT",
            "orderId": 84,
            "clientOrderId": params["origClientOrderId"],
            "status": "FILLED",
            "executedQty": "0.002",
            "cummulativeQuoteQty": "100",
        }

    monkeypatch.setattr(BinanceSpotBrokerClient, "_signed_request", duplicate_then_lookup)
    payload = BrokerOrderRequestPayload(
        symbol="BTCUSDT",
        side=Side.BUY,
        lots=0,
        quantity=Decimal("0.002"),
        limit_price=Decimal("50000"),
        signal_code="H_BLS",
        idempotency_key="restart-intent",
        client_order_id=build_client_order_id("restart-intent"),
    )

    result = client.submit_limit_order(payload)

    assert result.status == OrderStatus.FILLED
    assert result.broker_order_id == "84"
    assert result.client_order_id == payload.client_order_id


def test_client_order_id_uses_full_intent_and_fits_binance_limit():
    prefix = "a" * 64
    first = build_client_order_id(f"{prefix}:replay:first")
    second = build_client_order_id(f"{prefix}:replay:second")

    assert first != second
    assert len(first) == len(second) == 36
    assert first.startswith("RAPOT-")


def test_recovery_reads_order_with_postgres_row_lock():
    session = Mock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    repository = OrderRepository(session, inventory_scope="scope-a")

    repository.get(7, for_update=True)

    statement = session.execute.call_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in sql
    assert "inventory_scope" in sql
