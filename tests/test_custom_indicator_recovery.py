"""Missing native seeds cannot be hidden by fresh, unready price observations."""

from copy import deepcopy
from types import SimpleNamespace

from tests.test_custom_indicator_bootstrap import configured, quote, witness


def test_first_unknown_quote_does_not_hide_a_dequeued_unfinished_seed_job():
    clock, provider, service, _, key = configured()
    first_job = service._next_job()
    assert first_job[0] == key and not service._seed_queue
    service.live._enabled = True
    quote(service, key, clock, 150)
    cached = service._results[key]
    assert cached["live"] and cached["error"] is None
    assert not cached["points"][-1]["ready"]
    assert key not in service.live._compiled and key not in service._seed_due
    # A worker may have abandoned first_job after a native publication token
    # changed. A fresh quote is evidence of price activity, not a seed receipt.
    recovered = service._next_job()
    assert recovered[0] == key
    service.process(*recovered)
    assert key in service.live._compiled
    assert len(provider.calls) == 1
    witness(service, key, clock)
    quote(service, key, clock, 151)
    assert service._results[key]["points"][-1]["ready"]


def test_missing_seed_recovery_keeps_retry_and_native_witness_gates(monkeypatch):
    clock, provider, service, _, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 150)
    service.live.clear_comparisons(key[:2])
    quote(service, key, clock, 151)
    assert not service._seed_due and not service._seed_queue
    service._history_retries[key] = clock[0] + 30
    service._running = True
    witnessed = [False]
    monkeypatch.setattr(service.live, "history_ready", lambda *_: witnessed[0])
    assert service._next_job() is None
    witnessed[0] = True
    assert service._next_job() is None
    clock[0] += 31
    witnessed[0] = False
    assert service._next_job() is None
    witnessed[0] = True
    assert service._next_job()[0] == key
    assert len(provider.calls) == 1  # Scheduler checks never perform provider I/O.


def test_ready_count_requires_computed_values_and_a_retained_live_seed():
    clock, _, service, _, key = configured()
    service.live._enabled = True
    quote(service, key, clock, 150)
    assert service.status()["pending_or_stale_rule_symbols"] == 1
    service.process(*service._next_job())
    assert service.status()["pending_or_stale_rule_symbols"] == 1
    witness(service, key, clock)
    quote(service, key, clock, 151)
    assert service.status()["pending_or_stale_rule_symbols"] == 0
    service.live.clear_comparisons(key[:2])
    # Even the previous ready observation cannot hide a discarded evaluator.
    assert service._results[key]["points"][-1]["ready"]
    assert service.status()["pending_or_stale_rule_symbols"] == 1
    quote(service, key, clock, 152)
    assert service._results[key]["error"] is None
    assert service.status()["pending_or_stale_rule_symbols"] == 1


def test_worker_liveness_is_observed_instead_of_inferred_from_start_flag():
    _, _, service, _, _ = configured()
    service._running = True
    status = service.status()
    assert status["requested_running"] and not status["running"]
    assert not status["history_worker_alive"]
    history, calculation, connection = [True], [True], [True]
    service._thread = SimpleNamespace(is_alive=lambda: history[0])
    service.live._threads = [
        SimpleNamespace(name="custom-live-events", is_alive=lambda: calculation[0]),
        SimpleNamespace(name="custom-native-stream", is_alive=lambda: connection[0]),
    ]
    assert service.status()["running"]
    for alive, field in (
        (history, "history_worker_alive"),
        (calculation, "calculation_worker_alive"),
        (connection, "connection_worker_alive"),
    ):
        alive[0] = False
        status = service.status()
        assert status["requested_running"] and not status["running"]
        assert not status[field]
        alive[0] = True


def test_native_witness_wait_retains_seed_without_history_retry_and_breaks_comparison():
    clock, provider, service, _, key = configured()
    service.process(*service._next_job())
    witness(service, key, clock)
    quote(service, key, clock, 150)
    quote(service, key, clock, 151)
    old_result = deepcopy(service._results[key])
    old_publication = service.publication_token(key[:2])
    compiled = service.live._compiled[key]
    native = dict(service._native)
    service._preview_results[key] = deepcopy(old_result)
    assert old_result["previous"]
    service.native_witness_wait(key[:2], "New native day requires fresh witnesses")
    assert service.publication_token(key[:2]) != old_publication
    assert service.live._compiled[key] is compiled
    assert service._native == native
    assert not service._seed_due and not service._seed_queue
    assert service._read(key, clock[0])[1] == "unknown"
    assert service._results[key]["native_witness_wait"]
    assert "previous" not in service._results[key]
    assert service._preview_results[key]["error"]
    assert "previous" not in service._preview_results[key]
    assert service._live_cells == service._result_cells(service._results[key])
    assert not service.publish_live(
        [(key, service.live._configs[key], old_result["points"][-1])],
        source=clock[0],
        received=clock[0],
        serial=100,
        price=152,
        publication_epoch=old_publication,
        live_generation=service.live._generation,
        expected_epoch=provider.memory_epoch(),
    )
    clock[0] += 31
    assert service._next_job() is None  # This witness wait is not a history error.
    witness(service, key, clock)
    quote(service, key, clock, 153)
    current = service._results[key]
    assert current["points"][-1]["ready"]
    assert current["continuity"] != old_result["continuity"]
    assert current["previous"] is None
    assert not current.get("native_witness_wait")
    assert service._live_cells == service._result_cells(current)
    assert len(provider.calls) == 1
