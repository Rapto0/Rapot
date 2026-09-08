from __future__ import annotations

import pytest

from middleware.domain.enums import ExecutionMode
from middleware.infra.settings import MiddlewareSettings, settings


def test_runtime_config_rejects_disabled_webhook_auth_in_production():
    settings.app_env = "production"
    settings.require_webhook_auth = False

    with pytest.raises(ValueError, match="MW_REQUIRE_WEBHOOK_AUTH"):
        settings.validate_runtime_configuration()


def test_blank_optional_env_values_parse_as_none(monkeypatch):
    monkeypatch.setenv("MW_MAX_OPEN_TRANCHES_PER_SYMBOL", "")
    monkeypatch.setenv("MW_MAX_SYMBOL_EXPOSURE_USDT", "")
    monkeypatch.setenv("MW_MAX_DAILY_LOSS_USDT", "")
    monkeypatch.setenv("MW_MAX_ORDERS_PER_DAY", "")
    monkeypatch.setenv("MW_MAX_SIGNAL_AGE_SECONDS", "")
    monkeypatch.setenv("MW_INVENTORY_ACCOUNT_ID", "")

    cfg = MiddlewareSettings(_env_file=None)

    assert cfg.max_open_tranches_per_symbol is None
    assert cfg.max_symbol_exposure_usdt is None
    assert cfg.max_daily_loss_usdt is None
    assert cfg.max_orders_per_day is None
    assert cfg.max_signal_age_seconds is None
    assert cfg.inventory_account_id is None


def test_inventory_scope_requires_explicit_live_account_and_separates_venues():
    cfg = MiddlewareSettings.model_construct(
        execution_mode=ExecutionMode.LIVE,
        broker_name=settings.broker_name,
        inventory_account_id=None,
        binance_base_url="https://testnet.binance.vision",
    )

    with pytest.raises(ValueError, match="MW_INVENTORY_ACCOUNT_ID"):
        _ = cfg.inventory_scope

    cfg.inventory_account_id = "Primary_Account"
    testnet_scope = cfg.inventory_scope
    cfg.binance_base_url = "https://api.binance.com"
    assert cfg.inventory_scope != testnet_scope
    assert cfg.inventory_scope.endswith("|primary_account")


def test_inventory_scope_rejects_unstable_identifiers():
    cfg = MiddlewareSettings.model_construct(
        execution_mode=ExecutionMode.DRY_RUN,
        broker_name=settings.broker_name,
        app_env="development/other",
        inventory_account_id="pytest",
    )
    with pytest.raises(ValueError, match="MW_APP_ENV"):
        _ = cfg.inventory_scope


def test_max_orders_per_day_rejects_negative_values():
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        MiddlewareSettings(_env_file=None, max_orders_per_day=-1)
