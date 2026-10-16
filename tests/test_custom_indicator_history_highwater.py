"""Shared lookback requests cannot shrink after bounded raw-cache eviction."""

from dataclasses import replace

from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_bootstrap import configured, quote, witness
from tests.test_custom_indicator_data import NOW, Provider, frame


def source(monkeypatch, count=519):
    provider = Provider()
    provider.data = frame(count=count)

    def history(symbol, **kwargs):
        provider.calls.append((symbol, kwargs))
        result = provider.data.tail(kwargs["bars"]).copy()
        result.attrs["native_timeframe"] = kwargs["timeframe"]
        return result

    monkeypatch.setattr(provider, "custom_indicator_history", history)
    service = CustomIndicatorData(provider=provider, clock=lambda: NOW)
    return provider, service


def test_larger_prefix_resets_once_but_evicted_smaller_request_keeps_highwater(monkeypatch):
    provider, service = source(monkeypatch)
    key = ("BIST", "THYAO", "1D")
    service._native_frame(*key, 511, 1)
    first_token = service.publication_token(key[:2])
    expanded = service._native_frame(*key, 519, 1)
    assert len(expanded.bars) == expanded.requested == 519
    expanded_token = service.publication_token(key[:2])
    assert expanded_token != first_token  # Existing conservative prefix guard remains.
    for smaller in (511, 515, 511):
        service._native.pop(key)
        retained = service._native_frame(*key, smaller, 1)
        assert len(retained.bars) == retained.requested == 519
        assert provider.calls[-1][1]["bars"] == 519
        assert service._history_summaries[key].requested == 519
        assert service.publication_token(key[:2]) == expanded_token


def test_real_historical_revision_still_invalidates_with_highwater(monkeypatch):
    provider, service = source(monkeypatch)
    key = ("BIST", "THYAO", "1D")
    service._native_frame(*key, 519, 1)
    before = service.publication_token(key[:2])
    provider.data.iloc[5, provider.data.columns.get_loc("Close")] += 0.1
    service._native.pop(key)
    service._native_frame(*key, 511, 1)
    assert provider.calls[-1][1]["bars"] == 519
    assert service.publication_token(key[:2]) != before


def test_short_listing_remembers_requested_count_not_returned_count(monkeypatch):
    provider, service = source(monkeypatch, count=60)
    key = ("BIST", "THYAO", "1D")
    entry = service._native_frame(*key, 519, 1)
    assert len(entry.bars) == 60 and entry.requested == 519
    assert service._history_summaries[key].requested == 519
    service._native.pop(key)
    service._native_frame(*key, 511, 1)
    assert provider.calls[-1][1]["bars"] == 519
    old = service._native[key]
    service.native_advanced(key, old.bars[-1], replace(old.bars[-1], time=NOW + 86400))
    assert service._history_summaries[key].requested == 519


def test_current_member_admitted_max_is_requested_on_first_bootstrap(monkeypatch):
    _, provider, service, _, key = configured()
    small = service.live._configs[key]
    large = {**small, "requirements": [{**row, "bars": 519} for row in small["requirements"]]}
    # A second already admitted setting shares the native key. Unrelated members
    # must not enlarge this member's demand or require a full universe traversal.
    sibling = (*key[:2], "larger-settings")
    unrelated = ("BIST", "OTHER", "unrelated-settings")
    service.live._configs[sibling] = large
    service.live._configs[unrelated] = {
        **large,
        "requirements": [{**row, "bars": 999} for row in large["requirements"]],
    }
    service.live._members[key[:2]].append(sibling)
    service.live._members[unrelated[:2]] = [unrelated]
    service.process(key, small, service._generation)
    assert service._results[key]["error"] is None
    assert len(provider.calls) == 1
    assert provider.calls[0][1]["bars"] == 519


def test_epoch_invalidation_drops_request_highwater(monkeypatch):
    _, service = source(monkeypatch)
    service._native_frame("BIST", "THYAO", "1D", 519, 1)
    service.invalidate()
    assert not service._history_summaries
    smaller = service._native_frame("BIST", "THYAO", "1D", 511, 1)
    assert smaller.requested == 511


def test_refetch_after_eviction_retains_live_evaluator_and_comparison(monkeypatch):
    clock, provider, service, _, key = configured()
    provider.data = frame(count=519)

    def history(symbol, **kwargs):
        provider.calls.append((symbol, kwargs))
        result = provider.data.tail(kwargs["bars"]).copy()
        result.attrs["native_timeframe"] = kwargs["timeframe"]
        return result

    monkeypatch.setattr(provider, "custom_indicator_history", history)
    service._native_frame(*key[:2], "1D", 519, 1)
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, float(provider.data.iloc[-1].Close))
    quote(service, key, clock, float(provider.data.iloc[-1].Close) + 0.1)
    evaluator = service.live._compiled[key]
    observed = service._results[key]
    token = service.publication_token(key[:2])
    assert observed["points"][-1]["ready"] and observed["previous"]
    service._native.clear()  # Bounded raw cache may evict this member at any time.
    service.process(key, service.live._configs[key], service._generation)
    assert provider.calls[-1][1]["bars"] == 519
    assert service.live._compiled[key] is evaluator
    assert service._results[key] is observed
    assert service._results[key]["previous"]
    assert service.publication_token(key[:2]) == token
    assert service._results[key]["points"][-1]["ready"]
