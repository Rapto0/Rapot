"""A cancelled initial seed keeps its FIFO place without reviving removed demand."""

from copy import deepcopy

import pytest

from application.services.custom_indicator_data import CustomIndicatorData
from tests.test_custom_indicator_data import NOW, Provider, inputs, rule
from tests.test_custom_indicator_live_data import ready_service


def send_quote(service, clock, symbol, *, fresh):
    service.live._quote(
        {
            "kind": "quote",
            "member": ("BIST", symbol),
            "price": 130,
            "source_timestamp": clock[0] if fresh else clock[0] - 31,
            "received_at": clock[0],
        }
    )


def test_cancelled_initial_seed_cannot_starve_behind_repeated_other_member_gaps():
    clock = [NOW + 1]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["symbols"] = [
        {"symbol": symbol, "market_type": "BIST"} for symbol in ("AAA", "BBB", "CCC")
    ]
    service.configure([selected])
    keys = {key[1]: key for key in service.live._configs}
    original = provider.custom_indicator_history
    cancelled = False

    def history(symbol, **kwargs):
        nonlocal cancelled
        if symbol == "AAA" and not cancelled:
            cancelled = True
            send_quote(service, clock, symbol, fresh=False)
        return original(symbol, **kwargs)

    provider.custom_indicator_history = history
    first = service._next_job()
    assert first[0] == keys["AAA"]
    service.process(*first)
    assert keys["AAA"] not in service._results
    assert not service.live.has_seed(keys["AAA"], provider.memory_epoch())
    assert list(service._seed_queue) == [keys["BBB"], keys["CCC"], keys["AAA"]]
    send_quote(service, clock, "AAA", fresh=True)
    assert not service._results[keys["AAA"]]["points"][-1]["ready"]

    seen = []
    for _ in range(30):
        job = service._next_job()
        seen.append(job[0][1])
        service.process(*job)
        if job[0][1] != "AAA":
            send_quote(service, clock, job[0][1], fresh=True)
            send_quote(service, clock, job[0][1], fresh=False)
        assert len(service._seed_queue) == len(service._seed_queued) <= 3
    assert seen[:3] == ["BBB", "CCC", "AAA"]
    assert seen.count("AAA") == 1
    assert service.live.has_seed(keys["AAA"], provider.memory_epoch())
    assert sum(symbol == "AAA" for symbol, _ in provider.calls) == 2


@pytest.mark.parametrize(
    "retirement",
    ["removed", "disabled", "member_removed", "universe_removed", "stopped", "preview_expired"],
)
def test_cancelled_seed_does_not_restore_retired_demand(retirement):
    clock = [NOW + 1]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["trigger"] = "intrabar"
    if retirement == "preview_expired":
        service.preview("rsi_votes", inputs(), "THYAO")
    elif retirement == "universe_removed":
        selected.update(scope="all_bist", symbols=[])
        service.configure([selected], universe=[{"symbol": "THYAO"}])
    else:
        service.configure([selected])
    job = service._next_job()
    key = job[0]
    original = provider.custom_indicator_history

    def history(symbol, **kwargs):
        service.live_gap("Synthetic continuity break", key[:2])
        if retirement == "removed":
            service.configure([])
        elif retirement == "disabled":
            service.configure([{**selected, "enabled": False}])
        elif retirement == "member_removed":
            updated = deepcopy(selected)
            updated["symbols"] = [{"symbol": "GARAN", "market_type": "BIST"}]
            service.configure([updated])
        elif retirement == "universe_removed":
            service.set_universe([])
        elif retirement == "stopped":
            service._stop.set()
        else:
            clock[0] += 121
        return original(symbol, **kwargs)

    provider.custom_indicator_history = history
    service.process(*job)
    assert key not in service._seed_queued
    assert key not in service._seed_due
    assert key not in service._results
    assert not service.live.has_seed(key, provider.memory_epoch())


def test_cancelled_seed_deduplicates_a_gap_that_already_requeued_existing_result():
    _, provider, service, _, key, _ = ready_service()
    service.live_gap("First continuity break", key[:2])
    job = service._next_job()
    original = provider.custom_indicator_history

    def history(symbol, **kwargs):
        service.live_gap("Second continuity break", key[:2])
        return original(symbol, **kwargs)

    provider.custom_indicator_history = history
    service.process(*job)
    assert list(service._seed_queue) == [key]
    assert service._seed_queued == service._seed_due == {key}
    assert not service.live.has_seed(key, provider.memory_epoch())
