from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerOrderResult
from middleware.domain.enums import ExecutionMode, OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.infra.models import Base
from middleware.risk.binance_filters import BinanceSymbolRules


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

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        return BrokerAssetBalance(asset=asset.upper(), free=Decimal("0"), locked=Decimal("0"))

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
def configure_test_environment(
    monkeypatch: pytest.MonkeyPatch, test_sandbox: Path
) -> Iterator[None]:
    # Keep application/config imports after the root offline bootstrap (pytest_configure).
    from middleware.infra import db
    from middleware.infra.settings import MiddlewareSettings, settings

    db_file = test_sandbox / "middleware.sqlite3"
    # Use model defaults directly: neither .env nor inherited MW_* values belong in tests.
    test_settings = MiddlewareSettings.model_construct(
        database_url=f"sqlite+pysqlite:///{db_file.as_posix()}",
        webhook_auth_token="test-token",
        app_env="development",
        execution_mode=ExecutionMode.DRY_RUN,
        trading_enabled=False,
        binance_live_enabled=False,
        binance_api_key=None,
        binance_secret_key=None,
    )

    with monkeypatch.context() as middleware_patch:
        # Preserve singleton identity for existing imports and restore all fields/caches afterwards.
        middleware_patch.setattr(settings, "__dict__", test_settings.__dict__.copy())
        middleware_patch.setattr(
            settings, "__pydantic_fields_set__", test_settings.model_fields_set.copy()
        )
        middleware_patch.setattr(db, "_engine", None)
        middleware_patch.setattr(db, "_session_local", None)
        middleware_patch.setattr(
            "middleware.api.dependencies.build_broker_client",
            lambda cfg: FakeBinanceSpotBroker(),
        )

        try:
            db.configure_engine(settings.database_url)
            Base.metadata.create_all(bind=db.get_engine())
            yield
        finally:
            # Release SQLite handles before pytest cleans its temporary directory (also on Windows).
            if db._engine is not None:
                db._engine.dispose()


@pytest.fixture
def client() -> Iterator[TestClient]:
    from middleware.api.main import app

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
