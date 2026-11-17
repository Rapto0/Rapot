"""Bounded tracker preparation shares the native batch and rejects stale results."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from application.services.custom_indicator_data import CustomIndicatorData, Native, native_bars
from application.services.rsi_tracker import HISTORY_BARS, NATIVE_TIMEFRAMES
from tests.test_custom_indicator_batch_data import BatchProvider
from tests.test_custom_indicator_data import NOW, Provider, frame


def tracker(provider=None, symbols=("THYAO",)):
    clock = [NOW + 0.2]
    provider = provider or BatchProvider()
    provider.data = frame(count=HISTORY_BARS)
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    service.tracker_snapshot("tab", "BIST", symbols, tuple(NATIVE_TIMEFRAMES))
    service._sync_live()
    service.live._connection = SimpleNamespace(connected=True)
    for symbol in symbols:
        for tf in NATIVE_TIMEFRAMES.values():
            bars = native_bars(frame(tf, HISTORY_BARS), tf, "BIST", clock[0])
            service.live._buckets[("BIST", symbol, tf)] = (bars[-2:], clock[0])
    return clock, provider, service


def test_tracker_reuses_cache_then_batches_at_most_ten_frames_for_one_symbol():
    clock, provider, service = tracker(symbols=("THYAO", "GARAN"))
    key = ("BIST", "THYAO", "1D")
    bars = native_bars(provider.data, "1D", "BIST", clock[0])
    service._native[key] = Native(bars, clock[0], HISTORY_BARS, "cached", 1)
    service._tracker_history_step()
    assert len(provider.batches) == 1 and not provider.calls
    symbol, exchange, requests = provider.batches[0]
    assert (symbol, exchange) == ("THYAO", "BIST")
    assert len(requests) == 10 and "1D" not in requests
    assert set(requests.values()) == {HISTORY_BARS}
    assert len(service.tracker.seeds) == 11
    service._tracker_history_step()
    assert len(provider.batches) == 1
    clock[0] += 2
    service._tracker_history_step()
    assert len(provider.batches[1][2]) == 5
    assert len(service.tracker.seeds) == 16
    clock[0] += 2
    service._tracker_history_step()
    assert provider.batches[2][0] == "GARAN"
    assert len(provider.batches[2][2]) == 10


def test_provider_without_batch_support_fetches_only_one_frame_per_turn():
    clock, provider, service = tracker(Provider())
    service._tracker_history_step()
    assert len(provider.calls) == len(service.tracker.seeds) == 1
    service._tracker_history_step()
    assert len(provider.calls) == 1
    clock[0] += 2
    service._tracker_history_step()
    assert len(provider.calls) == len(service.tracker.seeds) == 2


@pytest.mark.parametrize(
    "race", ("epoch", "connection", "disconnect", "lease", "publication", "pause", "stop")
)
def test_batch_cannot_publish_after_account_connection_lease_or_continuity_change(race):
    _, provider, service = tracker()

    def changed():
        if race == "epoch":
            provider.generation += 1
        elif race == "connection":
            service.live._connection = SimpleNamespace(connected=True)
        elif race == "disconnect":
            service.live._connection.connected = False
        elif race == "lease":
            service.tracker.views.clear()
        elif race == "publication":
            service._publication_members[("BIST", "THYAO")] = 1
        elif race == "pause":
            provider.tradingview_enabled = False
        else:
            service._stop.set()

    provider.hook = changed
    service._tracker_history_step()
    assert len(provider.batches) == 1
    assert not service.tracker.seeds


def test_native_witness_is_rechecked_separately_for_each_returned_timeframe():
    _, provider, service = tracker()
    changed_key = ("BIST", "THYAO", "1D")

    def changed():
        pair, timestamp = service.live._buckets[changed_key]
        service.live._buckets[changed_key] = (
            (replace(pair[0], close=pair[0].close + 1), pair[1]),
            timestamp,
        )

    provider.hook = changed
    service._tracker_history_step()
    assert changed_key not in service.tracker.seeds
    assert changed_key in service.tracker.retry
    assert len(service.tracker.seeds) == 9


def test_failed_batch_is_backed_off_without_serial_provider_fallback():
    clock, provider, service = tracker()

    def failed():
        raise TimeoutError("provider unavailable")

    provider.hook = failed
    service._tracker_history_step()
    assert not service.tracker.seeds and not provider.calls
    assert len(service.tracker.retry) == 10
    assert all(retry > clock[0] for retry in service.tracker.retry.values())
    service._tracker_history_step()
    assert len(provider.batches) == 1


def test_invalid_frame_does_not_prevent_other_valid_frames_from_preparing():
    _, provider, service = tracker()
    original = provider._frame

    def bad_frame(tf):
        result = original(tf)
        if tf == "1D":
            result.attrs["native_timeframe"] = "2D"
        return result

    provider._frame = bad_frame
    service._tracker_history_step()
    assert len(service.tracker.seeds) == 9
    assert ("BIST", "THYAO", "1D") in service.tracker.retry


def test_busy_alarm_preparation_still_services_visible_page_after_each_alarm(monkeypatch):
    _, _, service = tracker()
    calls = []

    def next_job():
        service._turn += 1
        return ("alarm",)

    def page():
        calls.append("page")
        if len(calls) == 6:
            service._stop.set()

    monkeypatch.setattr(service, "_next_job", next_job)
    monkeypatch.setattr(service, "process", lambda job: calls.append(job))
    monkeypatch.setattr(service, "_tracker_history_step", page)
    service._loop()
    assert calls == ["alarm", "page"] * 3
