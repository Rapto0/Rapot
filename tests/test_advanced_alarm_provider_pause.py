"""Provider containment must stop BIST work without disabling direct Binance data."""

from copy import deepcopy

import pytest

from application.services.borsapy_gateway import BorsapyGatewayError
from tests import test_advanced_alarm_market_data as fixtures
from tests.test_advanced_alarm_market_data import rule


@pytest.fixture
def hub(tmp_path):
    return fixtures.hub.__wrapped__(tmp_path)


def test_paused_bist_rules_keep_members_but_schedule_no_provider_jobs(hub):
    hub._provider.tradingview_paused = lambda: True
    selected = rule("rsi")
    hub.configure([selected])
    for _ in range(5):
        hub.connection_step()
        assert hub._take_work() is None
    assert hub.symbol_count(1) == 1
    assert not hub._provider.calls
    assert hub.status()["state"] == "provider_paused"
    assert hub.status()["history_scheduled"] == 0
    assert hub.status()["history_requested"] == 1
    observation = hub.snapshot(selected, selected["symbols"][0])
    assert not observation["ready"] and observation["matched"] is None
    assert observation["continuity_reason"] == "provider_paused"
    with pytest.raises(BorsapyGatewayError) as error:
        hub.history("THYAO", "BIST", "1m")
    assert error.value.status_code == 503
    assert not hub._chart_leases


def test_paused_tradingview_keeps_direct_crypto_history_and_quotes(hub):
    hub._provider.tradingview_paused = lambda: True
    bist = rule("rsi")
    crypto = deepcopy(bist)
    crypto.update(id=2, symbols=[{"symbol": "BTCUSDT", "market_type": "Kripto"}])
    quotes = []
    hub._provider.crypto_quotes = lambda batch: quotes.append(batch) or {}
    hub.configure([bist, crypto])
    hub.connection_step()
    assert quotes == [["BTCUSDT"]]
    work = hub._take_work()
    assert work[0] == ("Kripto", "BTCUSDT", "1m")
    hub.fetch_history(*work)
    assert hub._provider.calls == [("history", "BTCUSDT", "Kripto", "1m")]
    assert hub.history("BTCUSDT", "Kripto", "1m")["candles"]


def test_pause_rejects_cached_bist_results_and_closes_existing_connection(hub):
    selected = rule("rsi")
    hub.configure([selected])
    hub.connection_step()
    work = hub._take_work()
    hub.fetch_history(*work)
    connection = hub._connection
    assert hub._series
    calls = list(hub._provider.calls)
    hub._provider.tradingview_paused = lambda: True
    hub.connection_step()
    assert not connection.connected
    assert hub._connection is None
    assert hub._take_work() is None
    assert not hub.snapshot(selected, selected["symbols"][0])["ready"]
    assert hub._provider.calls == calls
