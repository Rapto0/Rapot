from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from middleware.api.main import app
from middleware.domain.enums import BrokerName, ExecutionMode
from middleware.infra.db import configure_engine, get_engine
from middleware.infra.models import Base
from middleware.infra.settings import settings


def _clear_settings_cache() -> None:
    for key in ("signal_multipliers", "symbol_tick_overrides", "allowed_symbols"):
        settings.__dict__.pop(key, None)


@pytest.fixture(autouse=True)
def configure_test_environment():
    temp_dir = Path("middleware/tests/.tmp_db")
    temp_dir.mkdir(parents=True, exist_ok=True)
    db_file = temp_dir / "middleware_test.sqlite3"
    if db_file.exists():
        db_file.unlink()
    settings.app_env = "development"
    settings.database_url = f"sqlite+pysqlite:///{db_file}"
    settings.execution_mode = ExecutionMode.DRY_RUN
    settings.trading_enabled = False
    settings.broker_name = BrokerName.MOCK
    settings.mock_auto_fill = True
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
    settings.base_budget_tl = 10000
    settings.buy_bps = 20
    settings.sell_bps = 20
    settings.max_open_tranches_per_symbol = 4
    settings.max_symbol_exposure_tl = None
    settings.max_daily_loss_tl = None
    settings.max_orders_per_day = None
    settings.max_signal_age_seconds = None
    settings.max_signal_future_skew_seconds = 120
    settings.require_realtime_signals = False
    settings.symbol_tick_overrides_json = "{}"
    settings.allowed_symbols_csv = None
    settings.require_webhook_auth = True
    settings.webhook_auth_token = "test-token"
    settings.osmanli_live_enabled = False
    settings.osmanli_base_url = None
    settings.osmanli_token_url = None
    settings.osmanli_account_id = None
    settings.osmanli_client_id = None
    settings.osmanli_client_secret = None
    settings.osmanli_request_timeout_seconds = 10
    settings.osmanli_tv_webhook_url = None
    settings.osmanli_forward_enabled = False
    settings.osmanli_forward_timeout_seconds = 5
    _clear_settings_cache()

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
        "symbol": "THYAO",
        "ticker": "THYAO",
        "signalCode": "H_BLS",
        "signalText": "Hunter Beles",
        "side": "BUY",
        "price": 287.25,
        "timeframe": "1D",
        "barTime": 1713772800000,
        "barIndex": 12345,
        "isRealtime": True,
    }
