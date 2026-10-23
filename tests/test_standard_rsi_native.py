"""Independent ta-RSI oracle and native bridge continuity; no external I/O."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from ta.momentum import rsi

from application.services.advanced_alarm_market_data import AdvancedMarketData
from application.services.custom_indicator_data import native_bars
from application.services.standard_rsi_native import StandardRsiSeed
from tests.test_advanced_alarm_market_data import MemoryCache, rule
from tests.test_advanced_alarm_market_data import Provider as MarketProvider
from tests.test_custom_indicator_bootstrap import configured, quote, witness
from tests.test_custom_indicator_data import NOW, frame


@pytest.mark.parametrize("period", [2, 14, 30, 100, 500])
@pytest.mark.parametrize("count", [60, 500, 519])
def test_live_open_bar_equals_ta_rsi_last_500_history(period, count):
    raw = frame(count=count)
    bars = native_bars(raw, "1D", "BIST", NOW)
    seed = StandardRsiSeed.build(bars, {period})
    original = tuple(seed.closes)
    for price in [100.0, 200.0, 50.0, 150.0]:
        closes = raw.Close.tail(500).copy()
        closes.iloc[-1] = price
        expected = rsi(closes, window=period).iloc[-1]
        actual = seed.value(period, price)
        if np.isnan(expected):
            assert actual is None
        else:
            assert actual == pytest.approx(expected, abs=1e-11)
        assert tuple(seed.closes) == original  # Quotes replace the open candle.


def test_rollover_restarts_the_exact_500_bar_window():
    raw = frame(count=519)
    bars = native_bars(raw, "1D", "BIST", NOW)
    seed = StandardRsiSeed.build(bars, {14, 50})
    for index in range(5):
        closed = replace(seed.bucket, close=150 + index, confirmed=True)
        current = replace(
            closed,
            time=closed.time + 86400,
            end=closed.time + 2 * 86400,
            close=175 + index,
            confirmed=False,
        )
        assert seed.advance(closed, current)
        assert len(seed.closes) == 500
        for period in (14, 50):
            expected = rsi(pd.Series(seed.closes), window=period).iloc[-1]
            assert seed.value(period, current.close) == pytest.approx(expected, abs=1e-11)
    assert not seed.advance(replace(closed, time=1), current)


def setup_bridge():
    clock, provider, service, selected, key = configured("htf_rsi_score", all_timeframes=True)
    service.configure_standard_rsi({(*key[:2], tf): {14, 25} for tf in ("1D", "1W")})
    service.process(*service._next_job())
    witness(service, key, clock)
    return clock, provider, service, selected, key


@pytest.mark.parametrize("timeframe", ["1d", "1wk"])
def test_normal_rsi_uses_same_price_and_no_additional_history(timeframe):
    clock, provider, service, selected, key = setup_bridge()
    calls = len(provider.calls)
    ref = {"field": "rsi", "period": 14, "timeframe": timeframe}
    symbol = selected["symbols"][0]
    assert not service.standard_rsi_observation(ref, symbol, "intrabar", clock[0])["ready"]
    prior = None
    for price in (100.0, 200.0, 50.0):
        quote(service, key, clock, price)
        observed = service.standard_rsi_observation(ref, symbol, "intrabar", clock[0])
        closes = provider.data.Close.tail(500).copy()
        closes.iloc[-1] = price
        assert observed["ready"]
        assert observed["current"] == pytest.approx(rsi(closes, window=14).iloc[-1], abs=1e-11)
        assert observed["previous"] == prior
        assert observed["live_price"] == price
        assert observed["observation_id"] == service._results[key]["digest"]
        assert observed["source_timestamp"] == clock[0]
        prior = observed["current"]
    assert len(provider.calls) == calls
    assert service._next_job() is None


@pytest.mark.parametrize(
    "change",
    ["gap", "epoch", "revision", "stale", "paused", "missing_seed", "day_witness", "transport"],
)
def test_standard_bridge_fails_closed_on_continuity_change(change):
    clock, provider, service, selected, key = setup_bridge()
    quote(service, key, clock, 150)
    ref = {"field": "rsi", "period": 14, "timeframe": "1wk"}
    symbol = selected["symbols"][0]
    assert service.standard_rsi_observation(ref, symbol, "intrabar", clock[0])["ready"]
    if change in {"gap", "revision"}:
        service.live_gap(
            "Synthetic history correction" if change == "revision" else "Synthetic gap", key[:2]
        )
    elif change == "epoch":
        provider.generation += 1
    elif change == "stale":
        clock[0] += 31
    elif change == "paused":
        provider.tradingview_enabled = False
    elif change == "missing_seed":
        service.live.clear_comparisons(key[:2])
    elif change == "transport":
        service.live._connection = SimpleNamespace(connected=False)
    else:
        service.native_witness_wait(key[:2], "New native day requires witnesses")
    assert not service.standard_rsi_observation(ref, symbol, "intrabar", clock[0])["ready"]


def test_period_edit_reuses_existing_closed_window_without_refetch():
    clock, provider, service, selected, key = setup_bridge()
    quote(service, key, clock, 150)
    calls = len(provider.calls)
    service.configure_standard_rsi({(*key[:2], "1D"): {30}})
    ref = {"field": "rsi", "period": 30, "timeframe": "1d"}
    assert not service.standard_rsi_observation(ref, selected["symbols"][0], "intrabar", clock[0])[
        "ready"
    ]
    quote(service, key, clock, 120)
    observed = service.standard_rsi_observation(ref, selected["symbols"][0], "intrabar", clock[0])
    closes = provider.data.Close.tail(500).copy()
    closes.iloc[-1] = 120
    assert observed["current"] == pytest.approx(rsi(closes, window=30).iloc[-1], abs=1e-11)
    assert len(provider.calls) == calls and service._next_job() is None


def test_native_rollover_updates_shared_seed_without_history():
    clock, provider, service, selected, key = setup_bridge()
    quote(service, key, clock, 150)
    native_key = (*key[:2], "1D")
    seed = service._standard_rsi[native_key]["seed"]
    old_time = seed.bucket.time
    closed = replace(seed.bucket, close=150, high=max(seed.bucket.high, 150), confirmed=True)
    current = replace(
        closed, time=old_time + 86400, end=old_time + 86400 + 40000, close=151, confirmed=False
    )
    calls = len(provider.calls)
    service.native_advanced(native_key, closed, current)
    assert service._standard_rsi[native_key]["seed"] is seed
    assert seed.bucket.time == current.time and seed.closes[-2] == 150
    assert seed.value(14, 151) == pytest.approx(
        rsi(pd.Series(seed.closes), window=14).iloc[-1], abs=1e-11
    )
    assert service._standard_rsi[native_key]["observation"] is None
    assert len(provider.calls) == calls


def test_real_closed_history_revision_discards_standard_seed_and_observation():
    clock, provider, service, selected, key = setup_bridge()
    quote(service, key, clock, 150)
    before = service.publication_token(key[:2])
    provider.data.iloc[5, provider.data.columns.get_loc("Close")] += 0.1
    service._native.clear()
    service.process(key, service.live._configs[key], service._generation)
    assert service.publication_token(key[:2]) != before
    assert not service._standard_rsi
    observed = service.standard_rsi_observation(
        {"field": "rsi", "period": 14, "timeframe": "1d"},
        selected["symbols"][0],
        "intrabar",
        clock[0],
    )
    assert not observed["ready"] and observed["current"] is None


def combined_hub(tmp_path, *, count=1):
    clock, provider, custom, selected, key = configured("htf_rsi_score", all_timeframes=True)
    smi = configured("smi_votes", all_timeframes=True)[3]
    smi["id"] = "smi"
    daily = {**rule("rsi", timeframe="1d", op="lte", right=10), "id": "daily"}
    weekly = {**rule("rsi", timeframe="1wk", op="lte", right=25), "id": "weekly"}
    rules = [selected, smi, daily, weekly]
    symbols = [{"market_type": "BIST", "symbol": "THYAO"}] + [
        {"market_type": "BIST", "symbol": f"B{i:04}"} for i in range(1, count)
    ]
    for selected_rule in rules:
        selected_rule["symbols"] = deepcopy(symbols)
        selected_rule["mode"] = "once_per_bar"
    settings = SimpleNamespace(
        database_path=str(tmp_path / "main.sqlite3"),
        advanced_alarm_cache_path=None,
        advanced_alarm_market_enabled=True,
        advanced_alarm_all_bist_enabled=False,
        advanced_alarm_max_symbols=2000,
        advanced_alarm_quote_stale_seconds=120,
    )
    market = AdvancedMarketData(
        settings, provider=MarketProvider(), cache=MemoryCache(), clock=lambda: clock[0]
    )
    market._custom = custom
    market.configure(rules)
    return clock, provider, custom, key, market, rules


def test_four_real_rule_plans_share_1262_histories_without_new_provider_jobs(tmp_path):
    _, provider, custom, _, market, rules = combined_hub(tmp_path, count=631)
    assert len(custom._standard_rsi_demands) == 1262
    assert len(custom.live._configs) == 1262
    assert len(custom.live._wanted) == 6310
    assert market._requests == {} and provider.calls == [] and market._provider.calls == []
    assert all(market.uses_live_updates(selected) for selected in rules[2:])


def test_real_custom_and_market_bridge_publish_before_synchronous_callback(tmp_path):
    clock, provider, custom, key, market, rules = combined_hub(tmp_path)
    for _ in range(2):
        custom.process(*custom._next_job())
    witness(custom, key, clock)
    assert len(custom._standard_rsi) == 2
    calls = len(provider.calls)
    observations = []

    def callback(market_type, symbol):
        observations.append(
            [
                market.snapshot(selected, {"market_type": market_type, "symbol": symbol})
                for selected in rules
            ]
        )

    market.set_update_listener(callback)
    for price in (200, 0.1, 200):
        quote(custom, key, clock, price)
        assert len(observations) > 0
        observed = observations[-1]
        assert all(item["ready"] for item in observed), observed
        assert len({item["observation_id"] for item in observed}) == 1
        closes = provider.data.Close.tail(500).copy()
        closes.iloc[-1] = price
        expected = rsi(closes, window=14).iloc[-1]
        assert observed[2]["value"] == pytest.approx(expected, abs=1e-11)
        assert observed[3]["value"] == pytest.approx(expected, abs=1e-11)
        assert observed[2]["matched"] == (expected <= 10)
        assert observed[3]["matched"] == (expected <= 25)
    assert len(observations) == 3
    assert not observations[0][2]["matched"] and observations[1][2]["matched"]
    assert not observations[2][2]["matched"]
    assert len(provider.calls) == calls and market._provider.calls == []
    assert custom._next_job() is None and market._requests == {}

    # Removing custom native subscriptions clears the seed and restores the
    # supported ordinary path; saved rule definitions remain intact.
    before = deepcopy(rules[2:])
    market.configure(rules[2:])
    assert not custom._standard_rsi and not custom._standard_rsi_demands
    assert len(market._requests) == 2 and not market.uses_live_updates(rules[2])
    assert rules[2:] == before
    assert not market.snapshot(rules[2], rules[2]["symbols"][0])["ready"]
