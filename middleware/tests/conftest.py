from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from middleware.api.main import app
from middleware.broker_adapters.base import BrokerOrderResult
from middleware.domain.enums import BrokerName, ExecutionMode, OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.db import configure_engine, get_engine
from middleware.infra.models import Base
from middleware.infra.settings import settings
from middleware.risk.binance_filters import BinanceSymbolRules


def _clear_settings_cache() -> None:
    for key in ("signal_multipliers", "allowed_symbols"):
        settings.__dict__.pop(key, None)


@dataclass(slots=True)
class FakeBinanceSpotBroker:
    name: str = "BINANCE_SPOT"

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
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

    def get_asset_balance(self, asset: str) -> Decimal:
        return Decimal("1000")

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        quantity = payload.quantity or Decimal("0")
        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.FILLED,
            broker_order_id=f"BINANCE-TEST-{payload.idempotency_key[:8]}",
            filled_lots=0,
            filled_quantity=quantity,
            avg_fill_price=payload.limit_price,
            message="fake Binance fill",
            raw_payload={
                "symbol": payload.symbol,
                "side": payload.side.value,
                "quantity": str(quantity),
                "price": str(payload.limit_price),
            },
        )


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    temp_dir = Path("middleware/tests/.tmp_db")
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_file = temp_dir / "middleware_test.sqlite3"
    if db_file.exists():
        db_file.unlink()
    settings.app_env = "development"
    settings.database_url = f"sqlite+pysqlite:///{db_file}"
    settings.execution_mode = ExecutionMode.DRY_RUN
    settings.trading_enabled = False
    settings.broker_name = BrokerName.BINANCE_SPOT
    settings.binance_live_enabled = False
    settings.binance_base_url = "https://testnet.binance.vision"
    settings.binance_api_key = None
    settings.binance_secret_key = None
    settings.binance_request_timeout_seconds = 10
    settings.binance_recv_window_ms = 5000
    settings.binance_buy_quote_amount_usdt = 25
    settings.binance_quote_asset = "USDT"
    settings.binance_dry_run_auto_fill = True
    settings.binance_check_balance = True
    settings.allow_admin_endpoints = True
    settings.buy_bps = 20
    settings.sell_bps = 20
    settings.max_open_tranches_per_symbol = 4
    settings.max_symbol_exposure_usdt = None
    settings.max_daily_loss_usdt = None
    settings.max_orders_per_day = None
    settings.max_signal_age_seconds = None
    settings.max_signal_future_skew_seconds = 120
    settings.require_realtime_signals = False
    settings.allowed_symbols_csv = None
    settings.require_webhook_auth = True
    settings.webhook_auth_token = "test-token"
    _clear_settings_cache()
    monkeypatch.setattr(
        "middleware.api.dependencies.build_broker_client",
        lambda cfg: FakeBinanceSpotBroker(),
    )

    configure_engine(settings.database_url)
    Base.metadata.create_all(bind=get_engine())
    yield
    configure_engine(settings.database_url)
    if db_file.exists():
        db_file.unlink()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, headers={"X-Webhook-Token": "test-token"}) as test_client:
        yield test_client


@pytest.fixture
def sample_buy_payload() -> dict:
    return {
        "source": "Combo+Hunter",
        "symbol": "BTCUSDT",
        "ticker": "BTCUSDT",
        "signalCode": "H_BLS",
        "signalText": "Hunter Beles",
        "side": "BUY",
        "price": 50000,
        "timeframe": "1H",
        "barTime": 1713772800000,
        "barIndex": 12345,
        "isRealtime": True,
    }
