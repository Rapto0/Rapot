from __future__ import annotations

import pytest

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

    cfg = MiddlewareSettings(_env_file=None)

    assert cfg.max_open_tranches_per_symbol is None
    assert cfg.max_symbol_exposure_usdt is None
    assert cfg.max_daily_loss_usdt is None
    assert cfg.max_orders_per_day is None
    assert cfg.max_signal_age_seconds is None
