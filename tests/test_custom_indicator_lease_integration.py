"""Real native pool + live worker lease proofs, with offline wire/history fixtures."""

from datetime import UTC, datetime

import pandas as pd
import pytest

from application.services.custom_indicator_data import CustomIndicatorData
from infrastructure.providers.custom_indicator_stream import NativeStreamPool
from tests.test_custom_indicator_data import NOW, SESSION, Provider, rule
from tests.test_custom_indicator_stream import Transport, packet

MEMBER = ("BIST", "THYAO")
DAY = (*MEMBER, "1D")
LONG = (*MEMBER, "2D")


def drain(service):
    for _ in range(100):
        if not service.live.process_event():
            return
    pytest.fail("Native worker failed to drain a bounded synthetic wire batch")


def stream_and_series(pool, native_key):
    for stream in pool._streams.values():
        for sid, item in stream.series.items():
            if item["key"] == native_key:
                return stream, sid, item
    pytest.fail(f"Required offline native chart was not scheduled: {native_key}")


def frame_rows(provider):
    return [
        (stamp.timestamp(), row.Open, row.High, row.Low, row.Close)
        for stamp, row in provider.data.iloc[-2:].iterrows()
    ]


def send_bars(pool, native_key, rows, *, complete=True):
    stream, sid, item = stream_and_series(pool, native_key)
    packet(stream, "symbol_resolved", [item["session"], "sym", SESSION])
    packet(
        stream,
        "timescale_update",
        [item["session"], {sid: {"s": [{"v": list(row)} for row in rows]}}],
    )
    if complete:
        packet(stream, "series_completed", [item["session"], sid])
    return stream


def send_quote(service, pool, clock, price, *, source=None):
    stream, _, _ = stream_and_series(pool, DAY)
    packet(
        stream,
        "qsd",
        [
            stream._quote_session,
            {
                "n": "BIST:THYAO",
                "s": "ok",
                "v": {
                    "lp": price,
                    "lp_time": clock[0] if source is None else source,
                },
            },
        ],
    )
    drain(service)


def setup_native(*, bootstrap=True, long=True):
    clock = [NOW + 0.2]
    provider = Provider()
    service = CustomIndicatorData(provider=provider, clock=lambda: clock[0])
    selected = rule()
    selected["trigger"] = "intrabar"
    selected["condition"]["left"]["indicator"] = "smi_votes"
    selected["condition"]["left"]["inputs"]["en2"] = long
    selected["condition"]["left"]["inputs"]["onlyFirst"] = True
    service.configure([selected])
    service._running = True
    service.live._enabled = True
    pool = NativeStreamPool(
        Transport,
        "offline-token",
        provider.generation,
        lambda event, generation=service.live._generation: service.live.enqueue(event, generation),
        clock=lambda: clock[0],
    )
    service.live._connection = pool
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    key = next(iter(service.live._configs))
    if bootstrap:
        send_bars(pool, DAY, frame_rows(provider))
        drain(service)
        pool.configure(service.live._wanted, member_slots=service.live._member_slots)
        if long:
            send_bars(pool, LONG, frame_rows(provider))
            drain(service)
            pool.configure(service.live._wanted, member_slots=service.live._member_slots)
        job = service._next_job()
        assert job is not None
        service.process(*job)
        assert key in service.live._compiled
    return clock, provider, service, pool, key


def test_real_pool_closes_only_semantically_acked_long_chart_and_keeps_quotes():
    clock, provider, service, pool, key = setup_native(bootstrap=False)
    assert service._next_job() is None
    send_bars(pool, DAY, frame_rows(provider))
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    stream = send_bars(pool, LONG, frame_rows(provider))
    assert not pool.member_ready(MEMBER)  # Receiving bytes is not semantic acceptance.
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    drain(service)
    assert pool.member_ready(MEMBER)
    assert service.live.history_ready(MEMBER, {"1D", "2D"})
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    assert {item["key"] for item in stream.series.values()} == {DAY}
    assert "BIST:THYAO" in stream.members_by_full
    assert not any(item["m"] == "quote_remove_symbols" for item in stream.sent)
    service.process(*service._next_job())
    assert key in service.live._compiled
    assert not service._results[key]["points"]  # A history seed is not a live signal.
    clock[0] += 2
    send_quote(service, pool, clock, 150)
    assert service._results[key]["points"][-1]["ready"]


def test_ready_two_period_job_is_not_blocked_by_another_jobs_pending_native_period():
    clock, provider, service, pool, key = setup_native()
    pool.configure(
        service.live._wanted | {(*MEMBER, "7D")}, member_slots=service.live._member_slots
    )
    assert not pool.member_ready(MEMBER)
    assert service.live.history_ready(MEMBER, {"1D", "2D"})
    assert not service.live.history_ready(MEMBER, {"1D", "7D"})
    clock[0] += 2
    send_quote(service, pool, clock, 150)
    assert service._read(key, clock[0])[1] == "ready"
    # The readiness subset cannot reuse a certificate across an actual daily revision.
    rows = frame_rows(provider)
    rows[0] = (*rows[0][:-1], rows[0][-1] + 0.1)
    send_bars(pool, DAY, rows)
    drain(service)
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    assert service._read(key, clock[0])[1] != "ready"


def test_daily_extreme_after_lease_close_cannot_leak_into_older_quote():
    clock, provider, service, pool, key = setup_native()
    rows = frame_rows(provider)
    rows[-1] = (*rows[-1][:2], 2000, *rows[-1][3:])
    clock[0] = NOW + 2.2
    send_bars(pool, DAY, rows)
    drain(service)
    certificate = service.live._witness_certificates[LONG]
    assert pool.witness_valid(LONG, certificate)
    send_quote(service, pool, clock, 150, source=NOW + 2)
    assert not service._results[key]["points"][-1]["ready"]
    assert service.live._compiled[key]["buckets"]["2D"].high < 2000
    clock[0] = NOW + 3
    send_quote(service, pool, clock, 160)
    assert service._results[key]["points"][-1]["ready"]
    assert service.live._compiled[key]["buckets"]["2D"].high == 2000
    assert pool.witness_valid(LONG, certificate)


def test_daily_revision_invalidates_real_pool_certificate_and_all_history():
    clock, provider, service, pool, key = setup_native()
    clock[0] += 2
    send_quote(service, pool, clock, 150)
    assert service._results[key]["points"][-1]["ready"]
    certificate = service.live._witness_certificates[LONG]
    rows = frame_rows(provider)
    rows[0] = (*rows[0][:-1], rows[0][-1] + 0.1)  # Revised prior daily close.
    send_bars(pool, DAY, rows)
    drain(service)
    assert not pool.witness_valid(LONG, certificate)
    assert key not in service.live._compiled
    assert LONG not in service.live._buckets
    assert not service._native
    assert service._results[key]["error"]
    assert "previous" not in service._results[key]
    assert service._next_job() is None


def test_revision_during_history_bootstrap_cannot_restore_a_stale_live_seed(monkeypatch):
    clock, provider, service, pool, key = setup_native(bootstrap=False)
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    send_bars(pool, LONG, frame_rows(provider))
    drain(service)
    original = provider.custom_indicator_history
    revised = False

    def history(symbol, **kwargs):
        nonlocal revised
        result = original(symbol, **kwargs)
        if not revised:
            revised = True
            rows = frame_rows(provider)
            rows[0] = (*rows[0][:-1], rows[0][-1] + 0.1)
            send_bars(pool, DAY, rows)
            drain(service)
        return result

    monkeypatch.setattr(provider, "custom_indicator_history", history)
    service.process(*service._next_job())
    assert revised
    assert key not in service.live._compiled
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    assert not service._results.get(key, {}).get("live")


def test_daily_only_historical_adjustment_reopens_anchor_without_a_long_lease():
    _, provider, service, pool, _ = setup_native(long=False)
    assert service.live.history_ready(MEMBER, {"1D"})
    _, old_sid, _ = stream_and_series(pool, DAY)
    service.live.invalidate_witnesses(MEMBER)
    assert not service.live.history_ready(MEMBER, {"1D"})
    assert pool.needs_reconcile
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    _, new_sid, _ = stream_and_series(pool, DAY)
    assert new_sid != old_sid
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    assert service.live.history_ready(MEMBER, {"1D"})


def test_daily_rollover_requires_new_long_witness_before_any_new_day_signal():
    clock, provider, service, pool, key = setup_native()
    clock[0] += 2
    send_quote(service, pool, clock, float(provider.data.iloc[-1].Close))
    compiled = service.live._compiled[key]
    history_calls = len(provider.calls)
    continuity = service._results[key]["continuity"]
    certificate = service.live._witness_certificates[LONG]
    next_day = datetime(2026, 10, 14, 7, tzinfo=UTC).timestamp()
    next_row = [125.0, 127.0, 124.0, 126.0, 100.0]
    provider.data.loc[pd.Timestamp(next_day, unit="s", tz="UTC")] = next_row
    clock[0] = next_day + 2
    # Heartbeats are irrelevant to the candle-boundary proof. Keep the fake
    # socket alive across this explicit fixture time jump.
    for stream in pool._streams.values():
        stream.last_message = clock[0]
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    assert not pool.witness_valid(LONG, certificate)
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    assert service.live._compiled[key] is compiled
    assert service._read(key, clock[0])[1] == "unknown"
    assert not service._seed_due and not service._seed_queue
    send_quote(service, pool, clock, 126)
    assert not service._results[key]["points"][-1]["ready"]
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    send_bars(pool, LONG, frame_rows(provider))
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    assert service.live.history_ready(MEMBER, {"1D", "2D"})
    assert service.live._compiled[key] is compiled
    clock[0] += 2
    send_quote(service, pool, clock, 126.5)
    latest = service._results[key]["points"][-1]
    assert latest["ready"], latest.get("reason")
    assert service._results[key]["continuity"] != continuity
    assert latest["outputs"]["buy_signal"] == latest["outputs"]["sell_signal"] == 0
    assert len(provider.calls) == history_calls


def test_old_queued_lease_and_closed_pool_callback_cannot_restore_a_witness():
    _, provider, service, pool, _ = setup_native(bootstrap=False)
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    send_bars(pool, LONG, frame_rows(provider))
    old_event = next(event for event in service.live._queue if event["key"] == LONG)
    service.live.invalidate_witnesses(MEMBER)
    drain(service)
    assert LONG not in service.live._buckets
    assert not service.live.history_ready(MEMBER, {"1D", "2D"})
    pool.close()
    service.live.invalidate()
    pool._callback(old_event)
    assert not service.live._queue
    assert pool.confirm_native_witness(old_event) == {"accepted": False, "invalidated": False}


def test_wire_callback_never_holds_provider_receiver_or_lease_book_lock():
    _, provider, service, pool, _ = setup_native(bootstrap=False)
    calls = []
    enqueue = pool._callback

    def callback(event):
        calls.append(event["kind"])
        assert not pool._leases._lock._is_owned()
        assert all(not stream._lock._is_owned() for stream in pool._streams.values())
        enqueue(event)

    pool._callback = callback
    send_bars(pool, DAY, frame_rows(provider))
    drain(service)
    pool.configure(service.live._wanted, member_slots=service.live._member_slots)
    send_bars(pool, LONG, frame_rows(provider))
    drain(service)
    assert calls.count("bars") >= 2
