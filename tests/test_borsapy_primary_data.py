"""BIST primary selection, independent confirmation and private cache boundaries."""

import time
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

import data_loader
from application.services import borsapy_gateway
from application.services import server_alarm_evaluator as alarms
from settings import Settings, settings


def bars():
    return pd.DataFrame(
        {"Open": [10.0], "High": [12.0], "Low": [9.0], "Close": [11.0], "Volume": [100.0]},
        index=pd.date_range("2026-10-02 10:00", periods=1, tz="Europe/Istanbul"),
    )


def test_borsapy_is_the_default_not_a_silent_legacy_fallback(monkeypatch):
    assert Settings.model_fields["borsapy_use_for_bist"].default is True
    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    legacy = Mock(side_effect=AssertionError("Legacy provider must not run"))
    monkeypatch.setattr(data_loader, "fetch_stock_data", legacy)
    monkeypatch.setattr(data_loader, "_fetch_bist_data_yfinance", legacy)
    history = Mock(side_effect=borsapy_gateway.BorsapyGatewayError("Bağlantı gerekli.", 409))
    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(history=history)
    )
    with pytest.raises(borsapy_gateway.BorsapyGatewayError):
        data_loader.get_bist_data("THYAO")
    history.assert_called_once()
    legacy.assert_not_called()


def test_explicit_legacy_selection_still_works_without_borsapy(monkeypatch):
    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    monkeypatch.setattr(data_loader, "_bist_force_yfinance_fallback", True)
    monkeypatch.setattr(data_loader, "ensure_isyatirim_ca_bundle", lambda: None)
    legacy = Mock(return_value=bars())
    monkeypatch.setattr(data_loader, "_fetch_bist_data_yfinance", legacy)
    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", Mock(side_effect=AssertionError("unexpected auth"))
    )
    assert data_loader.get_bist_data("THYAO", use_borsapy=False) is legacy.return_value
    legacy.assert_called_once_with("THYAO", "01-01-2015")


def test_gateway_acquisition_age_is_preserved_not_refreshed_by_scanner(monkeypatch):
    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    frame = bars()
    frame.attrs.update(fetched_at_ts=time.time() - 200, fetched_at_iso="2026-10-02T10:00:00")
    monkeypatch.setattr(
        borsapy_gateway,
        "get_borsapy_gateway",
        lambda: SimpleNamespace(history=lambda *args, **kwargs: frame),
    )
    loaded = data_loader.get_bist_data("THYAO")
    assert not data_loader.is_dataframe_fresh(loaded, 90)
    assert loaded.attrs["fetched_at_iso"] == frame.attrs["fetched_at_iso"]
    assert loaded.attrs["source_hint"] == "borsapy_tradingview"
    assert loaded.index[0] == pd.Timestamp("2026-10-02")
    assert frame.index[0].hour == 10


def test_independent_yahoo_confirmation_is_retained_and_not_claimed_completed(monkeypatch):
    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    secondary = Mock(return_value=bars())
    monkeypatch.setattr(data_loader, "_fetch_bist_data_yfinance", secondary)
    assert data_loader.get_bist_data_secondary("THYAO") is secondary.return_value
    secondary.assert_called_once_with("THYAO", "01-01-2015")
    policy = data_loader.bist_source_policy()
    assert policy["primary_source"] == "borsapy_tradingview"
    assert policy["independent_confirmation_source"] == "yfinance_bist"
    assert policy["independent_confirmation_required"] is True
    frame = bars()
    frame.attrs.update(source="borsapy_tradingview", adjustment="splits")
    metadata = data_loader.signal_data_metadata(frame, "BIST")
    assert metadata["DataSource"] == "borsapy_tradingview"
    assert metadata["IndependentConfirmationRequired"] is True
    assert metadata["IndependentConfirmationSource"] == "yfinance_bist"
    assert not any("confirmed" in key.lower() for key in metadata)


@pytest.mark.asyncio
async def test_async_scanner_uses_the_same_selected_primary_without_fallback(monkeypatch, caplog):
    import async_data_loader

    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    history = Mock(side_effect=RuntimeError("private-provider-cookie"))
    monkeypatch.setattr(
        borsapy_gateway, "get_borsapy_gateway", lambda: SimpleNamespace(history=history)
    )
    monkeypatch.setattr(
        data_loader, "_fetch_bist_data_yfinance", Mock(side_effect=AssertionError("fallback"))
    )
    assert await async_data_loader.fetch_bist_data_async(None, "THYAO") is None
    history.assert_called_once()
    assert "private-provider-cookie" not in caplog.text


@pytest.mark.asyncio
async def test_borsapy_alarm_rechecks_gateway_after_connection_failure(monkeypatch):
    monkeypatch.setattr(settings, "borsapy_use_for_bist", True)
    calls = Mock(side_effect=[bars(), alarms.AlarmEvaluationError("Bağlantı kapalı.")])
    evaluator = alarms.ServerAlarmEvaluator(provider=SimpleNamespace(fetch_bars=calls))
    try:
        await evaluator._fetch("THYAO", "BIST", "1d")
        with pytest.raises(alarms.AlarmEvaluationError, match="Bağlantı kapalı"):
            await evaluator._fetch("THYAO", "BIST", "1d")
        assert calls.call_count == 2
        assert not evaluator._cache
    finally:
        evaluator.close()


@pytest.mark.parametrize("use_borsapy", [True, False])
def test_share_universe_is_approved_copied_and_independent_of_price_provider(
    monkeypatch, use_borsapy
):
    monkeypatch.setattr(settings, "borsapy_use_for_bist", use_borsapy)
    monkeypatch.setattr(
        borsapy_gateway,
        "get_borsapy_gateway",
        Mock(side_effect=AssertionError("unexpected provider")),
    )
    symbols = data_loader.get_all_bist_symbols()
    assert len(symbols) == len(set(symbols)) == 631
    assert {"THYAO", "GARAN", "ASELS"} <= set(symbols)
    assert not {"ACP", "ADBNK", "DRPHN"} & set(symbols)
    symbols.clear()
    assert len(data_loader.get_all_bist_symbols()) == 631
    assert data_loader.bist_symbols_status()["source"] == "kap_verified_share_snapshot"
    assert data_loader.bist_symbols_status()["audit_as_of"] == "2026-10-12"
    assert data_loader.bist_symbols_status()["live_trading_status_verified"] is False
    assert data_loader.get_all_bist_symbols() == data_loader.ALL_BIST_TICKERS
