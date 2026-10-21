"""Compact live bootstrap preserves replay consumers and identical quote values."""

from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pandas as pd
import pytest

from application.services.advanced_alarm_conditions import condition_fields
from application.services.custom_indicator_data import (
    CustomIndicatorData,
    native_bars,
    with_native_ends,
)
from application.services.custom_indicators import catalog
from tests.test_custom_indicator_data import NOW, Provider, frame, rule


def configured(indicator="rsi_votes", *, all_timeframes=False):
    clock = [NOW + 0.2]
    provider = Provider()
    provider.data = frame(count=500)
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    changes = {
        item["key"]: all_timeframes or item["key"] in {"en1", "en_1d"}
        for item in catalog.SPECS[indicator]["inputs"]
        if item["key"].startswith("en")
    }
    selected["trigger"] = "intrabar"
    selected["condition"]["left"].update(indicator=indicator, inputs=changes)
    service.configure([selected])
    key = next(iter(service.live._configs))
    return clock, provider, service, selected, key


def witness(service, key, clock):
    service.live._enabled = True
    for native_key, entry in service._native.items():
        if native_key[:2] == key[:2]:
            service.live._buckets[native_key] = (
                (replace(entry.bars[-2], confirmed=True), entry.bars[-1]),
                clock[0],
            )


def quote(service, key, clock, price):
    clock[0] += 1
    service.live.enqueue(
        {
            "kind": "quote",
            "member": key[:2],
            "price": price,
            "source_timestamp": clock[0],
            "received_at": clock[0],
        }
    )
    assert service.live.process_event()


@pytest.mark.parametrize("indicator", list(catalog.SPECS))
def test_rule_only_bootstrap_skips_replay_and_matches_all_five_live_evaluators(
    monkeypatch, indicator
):
    fast = configured(indicator, all_timeframes=True)
    replay = configured(indicator, all_timeframes=True)
    replay_inputs = replay[3]["condition"]["left"]["inputs"]
    replay[2].preview(indicator, replay_inputs, "THYAO")
    calls = []
    original = catalog.evaluate

    def counted(*args, **kwargs):
        calls.append(len(args[2]))
        return original(*args, **kwargs)

    monkeypatch.setattr(catalog, "evaluate", counted)
    for clock, _, service, selected, key in (fast, replay):
        service.process(*service._next_job())
        assert service._results[key]["error"] is None
        witness(service, key, clock)
        ref = condition_fields(selected["condition"], "1d")[0]
        assert not service.observation(ref, selected["symbols"][0], "intrabar", clock[0])["ready"]
    assert calls == [500]
    assert fast[2]._results[fast[4]]["points"] == []
    assert len(replay[2]._preview_results[replay[4]]["points"]) == 128
    assert (
        fast[2].live._compiled[fast[4]]["evaluator"].retained_cells
        == replay[2].live._compiled[replay[4]]["evaluator"].retained_cells
    )
    for price in (200, 20, 150, 75):
        for clock, _, service, _, key in (fast, replay):
            quote(service, key, clock, price)
        left = fast[2]._results[fast[4]]["points"][-1]
        right = replay[2]._results[replay[4]]["points"][-1]
        assert left["ready"] and right["ready"]
        assert left["outputs"] == right["outputs"]
    assert calls == [500]


def test_later_preview_replays_history_even_when_live_quotes_already_fill_preview_cache():
    clock, provider, service, selected, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 200)
    inputs = selected["condition"]["left"]["inputs"]
    service.preview("rsi_votes", inputs, "THYAO")
    quote(service, key, clock, 20)
    assert len(service._preview_results[key]["points"]) == 1
    assert not service._preview_results[key]["history_replayed"]
    before = service._results[key]
    evaluator = service.live._compiled[key]["evaluator"]
    service.process(*service._next_job())
    preview = service.preview("rsi_votes", inputs, "THYAO")
    assert len(preview["points"]) == 128
    assert not preview["points"][0]["rows"]
    assert preview["latest"]["rows"]
    assert preview["observation_price"] == 20
    assert service._results[key] is before
    assert service.live._compiled[key]["evaluator"] is evaluator
    assert service._preview_results[key]["history_replayed"]
    assert service._next_job() is None
    assert len(provider.calls) == 1


def test_new_closed_rule_replays_immediately_without_replacing_live_price_or_seed():
    clock, provider, service, selected, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 20)
    before = service._results[key]
    evaluator = service.live._compiled[key]["evaluator"]
    assert before["closed_points"] == []
    closed = deepcopy(selected)
    closed.update(id="closed", trigger="bar_close")
    service.configure([selected, closed])
    job = service._next_job()
    assert job[0] == key
    service.process(*job)
    ref = condition_fields(closed["condition"], "1d")[0]
    result = service.observation(ref, closed["symbols"][0], "bar_close", clock[0])
    assert result["ready"]
    assert result["bar_time"] < service._results[key]["points"][-1]["time"]
    assert service._results[key] is before
    assert service._results[key]["live_price"] == 20
    assert service.live._compiled[key]["evaluator"] is evaluator
    assert service._next_job() is None
    assert len(provider.calls) == 1


def test_expired_preview_does_not_force_rule_bootstrap_to_replay(monkeypatch):
    clock, _, service, selected, key = configured()
    service.preview("rsi_votes", selected["condition"]["left"]["inputs"], "THYAO")
    clock[0] += 121

    def forbidden(*_args, **_kwargs):
        pytest.fail("Expired chart demand must not replay history for an intrabar rule")

    monkeypatch.setattr(catalog, "evaluate", forbidden)
    service.process(*service._next_job())
    assert service._results[key]["error"] is None
    assert key in service.live._compiled
    assert not service._preview_results


def test_preview_arriving_during_seed_preparation_still_gets_full_replay(monkeypatch):
    _, _, service, selected, key = configured()
    original = service.live.prepare_seed

    def prepare(*args, **kwargs):
        result = original(*args, **kwargs)
        service.preview("rsi_votes", selected["condition"]["left"]["inputs"], "THYAO")
        return result

    monkeypatch.setattr(service.live, "prepare_seed", prepare)
    service.process(*service._next_job())
    assert service._results[key]["points"] == []
    assert key not in service._preview_results
    service.process(*service._next_job())
    assert len(service._preview_results[key]["points"]) == 128
    assert service._preview_results[key]["history_replayed"]


def test_crypto_multiday_bootstrap_fetches_daily_witness_history(monkeypatch):
    clock, provider, service, selected, _ = configured()
    provider.data = frame(market="Kripto")
    original = provider.custom_indicator_history

    def history(symbol, **kwargs):
        result = original(symbol, **kwargs)
        if kwargs["timeframe"] == "2D":
            result.index = pd.date_range(end="2026-10-13", periods=len(result), freq="2D", tz="UTC")
        return result

    monkeypatch.setattr(provider, "custom_indicator_history", history)
    selected["symbols"] = [{"market_type": "Kripto", "symbol": "BTCUSDT"}]
    selected["condition"]["left"]["inputs"].update(tf1="2D")
    selected["timeframe"] = "2D"
    service.configure([selected])
    service.process(*service._next_job())
    assert {kwargs["timeframe"] for _, kwargs in provider.calls} == {"1D", "2D"}
    result = next(iter(service._results.values()))
    assert result["error"] is None
    assert result["received"] == clock[0]


def test_history_gate_requires_daily_certificate_even_after_temporary_series_is_released(
    monkeypatch,
):
    _, provider, service, selected, _ = configured()
    selected["symbols"] = [{"market_type": "Kripto", "symbol": "BTCUSDT"}]
    selected["condition"]["left"]["inputs"].update(tf1="2D")
    selected["timeframe"] = "2D"
    service.configure([selected])
    service._running = True
    observed = []
    certificate = [False]

    def history_ready(member, needed):
        observed.append((member, set(needed)))
        return certificate[0]

    monkeypatch.setattr(service.live, "history_ready", history_ready)
    assert service._next_job() is None
    assert observed and all(item == (("Kripto", "BTCUSDT"), {"1D", "2D"}) for item in observed)
    certificate[0] = True
    job = service._next_job()
    assert job[0][:2] == ("Kripto", "BTCUSDT")
    service._queue_seed(job[0])
    certificate[0] = False
    assert service._next_job() is None
    assert provider.calls == []


def test_native_history_revision_invalidates_member_witnesses_before_rebuilding(monkeypatch):
    clock, provider, service, _, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 20)
    invalidated = []
    original = service.live.invalidate_witnesses

    def invalidate(member):
        invalidated.append(member)
        original(member)

    monkeypatch.setattr(service.live, "invalidate_witnesses", invalidate)
    provider.data.iloc[-10, provider.data.columns.get_loc("Close")] += 0.1
    service._native.clear()
    service.process(key, service.live._configs[key], service._generation)
    assert invalidated == [("BIST", "THYAO")]
    assert key not in service.live._compiled
    assert not any(native_key[:2] == key[:2] for native_key in service.live._buckets)
    assert service._results[key]["error"]


@pytest.mark.parametrize("stride,timeframe", [(2, "2D"), (3, "3D"), (10, "2W"), (21, "1M")])
def test_native_end_index_matches_linear_reference_over_large_sparse_history(stride, timeframe):
    source = native_bars(frame(count=1000), "1D", "BIST", NOW)
    # Missing supplied trading days and shortened source sessions remain gaps;
    # neither path may derive a calendar close in their absence.
    daily = tuple(
        replace(bar, end=bar.end - 3600 if index % 11 == 0 else bar.end)
        for index, bar in enumerate(source)
        if index % 13 != 0
    )
    bars = tuple(replace(bar, end=None, confirmed=False) for bar in source[::stride])
    expected = []
    for index, bar in enumerate(bars):
        following = bars[index + 1].time if index + 1 < len(bars) else None
        eligible = [day for day in daily if following and bar.time <= day.time < following]
        expected.append(
            replace(
                bar,
                end=eligible[-1].end if eligible else None,
                confirmed=bool(following and following <= NOW),
            )
        )
    assert with_native_ends(bars, daily, timeframe, "BIST", NOW) == tuple(expected)


@pytest.mark.parametrize("daily_indices", [(), (0,), (3,), (0, 2, 2, 3)])
def test_native_end_index_preserves_empty_intervals_and_exact_upper_boundary(daily_indices):
    source = native_bars(frame(count=4), "1D", "BIST", NOW)
    daily = tuple(source[index] for index in daily_indices)
    bars = (replace(source[1], end=None), replace(source[2], end=None))
    result = with_native_ends(bars, daily, "2D", "BIST", NOW)
    assert result[0].end is None  # No daily timestamp inside [bar 1, bar 2).
    assert result[0].confirmed
    assert result[1].end is None
    assert not result[1].confirmed


def test_crypto_refused_daily_anchor_is_visible_for_multiday_preview():
    _, _, service, selected, _ = configured()
    selected["symbols"] = [{"market_type": "Kripto", "symbol": "BTCUSDT"}]
    selected["condition"]["left"]["inputs"].update(tf1="2D")
    selected["timeframe"] = "2D"
    service.configure([selected])
    key = next(iter(service.live._configs))
    service.live._refused.add(("Kripto", "BTCUSDT", "1D"))
    _, state, reason = service._read(key, NOW)
    assert state == "unknown"
    assert "reddetti" in reason


def test_live_reads_and_intrabar_observations_fail_closed_when_lease_certificate_expires():
    clock, _, service, selected, key = configured(all_timeframes=True)
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 20)
    valid = [True]
    service.live._connection = SimpleNamespace(
        member_ready=lambda _member: True,
        witness_valid=lambda _key, _certificate: valid[0],
    )
    ref = condition_fields(selected["condition"], "1d")[0]
    assert service.observation(ref, selected["symbols"][0], "intrabar", clock[0])["ready"]
    valid[0] = False
    for require_latest in (False, True):
        _, state, reason = service._read(key, clock[0], require_latest=require_latest)
        assert state == "unknown"
        assert "güncel günlük mumla" in reason
    result = service.observation(ref, selected["symbols"][0], "intrabar", clock[0])
    assert not result["ready"]
    assert result["current"] is None and result["previous"] is None
