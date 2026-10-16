"""Bounded bootstrap scheduling remains fair as native witnesses arrive."""

from collections import deque

from application.services.custom_indicator_data import MAX_SEED_CHECKS_PER_TURN
from tests.test_custom_indicator_bootstrap import configured


def universe(monkeypatch, count=805):
    clock, _, service, _, original = configured()
    config = service.live._configs[original]
    keys = tuple(("BIST", f"FIX{i:04d}", original[2]) for i in range(count))
    service.live._configs = dict.fromkeys(keys, config)
    service._job_order = keys
    service._seed_queue = deque(keys)
    service._seed_queued = set(keys)
    service._running = True
    eligible, checks = set(), []

    def witnessed(member, _needed):
        checks.append(member)
        return member in eligible

    monkeypatch.setattr(service.live, "history_ready", witnessed)
    return clock, service, keys, eligible, checks


def test_repeated_native_wakes_do_not_sweep_all_805_deferred_members(monkeypatch):
    _, service, keys, _, checks = universe(monkeypatch)
    for _ in range(20):
        before = len(checks)
        service._wake.set()
        assert service._next_job() is None
        # Existing fallback remains independently capped at64.
        assert len(checks) - before <= MAX_SEED_CHECKS_PER_TURN + 64
        assert len(service._seed_queue) == len(service._seed_queued) == len(keys)
    assert set(checks) == {key[:2] for key in keys}


def test_ready_member_at_queue_tail_is_not_starved_by_unavailable_anchors(monkeypatch):
    _, service, keys, eligible, _ = universe(monkeypatch)
    eligible.add(keys[-1][:2])
    maximum_turns = (len(keys) + MAX_SEED_CHECKS_PER_TURN - 1) // MAX_SEED_CHECKS_PER_TURN
    for _ in range(maximum_turns):
        job = service._next_job()
        if job is not None:
            break
    assert job[0] == keys[-1]


def test_ack_wakeup_can_select_a_newly_ready_front_member_immediately(monkeypatch):
    _, service, _, eligible, _ = universe(monkeypatch)
    assert service._next_job() is None
    head = service._seed_queue[0]
    eligible.add(head[:2])
    service._wake.set()
    # No clock advance or negative-readiness cache hides the new ACK.
    assert service._next_job()[0] == head


def test_rotating_queue_never_bypasses_retry_deadline(monkeypatch):
    clock, service, keys, eligible, checks = universe(monkeypatch)
    eligible.add(keys[-1][:2])
    service._history_retries[keys[-1]] = clock[0] + 30
    for _ in range(14):
        assert service._next_job() is None
    assert keys[-1][:2] not in checks  # Retry gate precedes certificate lookup.
    clock[0] += 30
    for _ in range(14):
        job = service._next_job()
        if job:
            break
    assert job[0] == keys[-1]


def test_missing_seed_outside_deferred_queue_still_recovers(monkeypatch):
    clock, service, keys, eligible, _ = universe(monkeypatch)
    missing = keys[-1]
    service._seed_queue.remove(missing)
    service._seed_queued.remove(missing)
    service._results[missing] = {
        "live": True,
        "received": clock[0],
        "seed_received": clock[0],
        "error": None,
    }
    eligible.add(missing[:2])
    for _ in range(14):
        job = service._next_job()
        if job:
            break
    assert job[0] == missing
    assert len(service._seed_queue) == 804  # Unavailable work cannot monopolize service.


def test_preview_retains_one_in_four_share_during_ready_rule_bootstrap(monkeypatch):
    clock, service, keys, eligible, _ = universe(monkeypatch)
    eligible.update(key[:2] for key in keys)
    preview = ("BIST", "ZZPREVIEW", keys[0][2])
    config = service.live._configs[keys[0]]
    service.live._configs[preview] = config
    service._previews[preview] = (clock[0] + 120, config)
    eligible.add(preview[:2])
    jobs = [service._next_job()[0] for _ in range(8)]
    assert jobs[3] == jobs[7] == preview
    assert all(key != preview for index, key in enumerate(jobs) if index not in (3, 7))


def test_fallback_consumes_queued_demand_before_queue_cursor_reaches_it(monkeypatch):
    clock, service, keys, eligible, _ = universe(monkeypatch)
    selected = keys[-1]
    eligible.add(selected[:2])
    service._job_cursor = len(keys) - 1
    assert service._next_job()[0] == selected
    assert selected not in service._seed_queued
    assert selected not in service._seed_queue
    # Model successful preparation: the remaining unavailable queue must not
    # schedule the now-ready evaluator again on any later rotation.
    service._results[selected] = {
        "received": clock[0],
        "seed_received": clock[0],
        "error": None,
    }
    monkeypatch.setattr(service.live, "has_seed", lambda key, _epoch: key == selected)
    for _ in range(15):
        assert service._next_job() is None
