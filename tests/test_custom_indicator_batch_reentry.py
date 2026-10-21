"""Expired previews refresh a whole native demand without per-TF invalidation churn."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, rule
from tests.test_custom_indicator_preview_capacity import MixedHistory


class History(MixedHistory):
    def __init__(self):
        super().__init__()
        self.batches = []
        self.hook = lambda _requests, _frames: None

    def custom_indicator_histories(self, symbol, *, exchange, requests):
        self.batches.append(requests.copy())
        frames = {
            tf: self.custom_indicator_history(symbol, exchange=exchange, timeframe=tf, bars=count)
            for tf, count in requests.items()
        }
        self.hook(requests, frames)
        return frames


def expired_preview(market="BIST"):
    clock = [NOW + 0.2]
    provider = History()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    background = rule()
    background["trigger"] = "intrabar"
    background["symbols"] = [{"symbol": "OTHER", "market_type": "BIST"}]
    service.configure([background])
    service.live._connection = SimpleNamespace(connected=True, status=lambda: {})
    symbol = "THYAO" if market == "BIST" else "BTCUSDT"
    service.preview("htf_rsi_score", {}, symbol, market)
    key = next(key for key in service.live._configs if key[1] == symbol)
    config = service.live._configs[key]
    service.process(key, config, service._generation)
    original = service.live._compiled[key]
    clock[0] += 240
    service._next_job()
    service._sync_live()
    assert key not in service.live._compiled and key not in service._previews
    # During universe bootstrap the bounded raw cache evicts this inactive member.
    service._native.clear()
    assert len(service._history_summaries) == 10
    service.preview("htf_rsi_score", {}, symbol, market)
    assert key in service._seed_queued
    provider.batches.clear()
    provider.calls.clear()
    return clock, provider, service, key, config, original


@pytest.mark.parametrize("market", ["BIST", "Kripto"])
def test_expired_ten_tf_preview_reseeds_from_one_batch_after_one_continuity_reset(market):
    clock, provider, service, key, config, original = expired_preview(market)
    before = service.publication_token(key[:2])
    service.process(key, config, service._generation)
    assert service.publication_token(key[:2]) == (before[0], before[1] + 1)
    assert not service.live.has_seed(key, 1)  # No publication across the revision.
    assert key in service._seed_queued and not service._history_retries
    assert len(service._native) == len(service._history_summaries) == 10
    assert all(value.received == clock[0] for value in service._history_summaries.values())
    service.process(key, config, service._generation)
    assert service.live.has_seed(key, 1)
    assert len(provider.batches) == 1 and len(provider.calls) == 10
    assert service.live._compiled[key]["evaluator"].rows == original["evaluator"].rows
    assert service.live._compiled[key]["buckets"] == original["buckets"]
    assert service._results[key]["error"] is None


def test_reentry_still_waits_for_new_native_witnesses_before_running_history_job():
    _, provider, service, key, config, _ = expired_preview()
    service.process(key, config, service._generation)
    service._running = True
    assert not service._history_transport_ready(key, config)
    assert service._next_job() is None
    assert len(provider.batches) == 1
    assert not service.live.has_seed(key, 1)


@pytest.mark.parametrize("change", ["gap", "account", "removed", "stopped", "bad_frame"])
def test_reentry_batch_cannot_commit_after_partial_validation_or_external_change(change):
    _, provider, service, key, config, _ = expired_preview()
    summaries = deepcopy(service._history_summaries)

    def interrupt(_requests, frames):
        if change == "gap":
            service.live_gap("Synthetic concurrent gap", key[:2])
        elif change == "account":
            provider.generation += 1
        elif change == "removed":
            service._previews.clear()
            service._sync_live()
        elif change == "stopped":
            service._stop.set()
        else:
            frames[list(frames)[-1]].iloc[0, 1] = -1

    provider.hook = interrupt
    service.process(key, config, service._generation)
    assert not service.live.has_seed(key, provider.generation)
    assert not service._native
    assert service._history_summaries == summaries


def test_real_revision_refetches_cached_sibling_timeframes_before_single_commit():
    _, provider, service, key, config, _ = expired_preview()
    service.process(key, config, service._generation)
    service.process(key, config, service._generation)
    before = service.publication_token(key[:2])
    provider.batches.clear()
    provider.calls.clear()
    provider.data.iloc[5, provider.data.columns.get_loc("Close")] += 0.1
    service._native.pop((*key[:2], "2D"))
    service.process(key, config, service._generation)
    assert [set(batch) for batch in provider.batches] == [
        {"2D"},
        set(service._native_demand(config, key[0])) - {"2D"},
    ]
    assert len(provider.calls) == 10
    assert service.publication_token(key[:2]) == (before[0], before[1] + 1)
    assert not service.live.has_seed(key, 1)
    assert len(service._native) == 10
    assert all(
        entry.bars[5].close == provider.data.iloc[5].Close for entry in service._native.values()
    )
    service.process(key, config, service._generation)
    assert service.live.has_seed(key, 1) and len(provider.calls) == 10


@pytest.mark.parametrize("change", ["gap", "missing"])
def test_failed_later_batch_does_not_publish_earlier_validated_group(change):
    provider = History()
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    demand = {f"{index}D": 2000 for index in range(1, 12)}

    def second_group(_requests, frames):
        if len(provider.batches) == 2:
            if change == "gap":
                service.live_gap("Synthetic gap between groups", ("BIST", "THYAO"))
            else:
                frames.pop(next(iter(frames)))

    provider.hook = second_group
    with pytest.raises(ValueError):
        service._native_entries("BIST", "THYAO", demand, 1, (0, 0))
    assert len(provider.batches) == 2
    assert not service._native and not service._history_summaries
