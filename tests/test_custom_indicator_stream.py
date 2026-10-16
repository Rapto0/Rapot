"""Offline wire fixtures for native multiplexing; no account/network access."""

import json
import threading
from types import SimpleNamespace

import pytest

from infrastructure.providers.custom_indicator_stream import (
    MAX_CHARTS_PER_CONNECTION,
    MAX_LIVE_CONNECTIONS,
    MAX_PROVIDER_SERIES,
    MAX_SERIES_PER_RECONCILE,
    NativeStreamPool,
    plan_native_subscriptions,
    stream_class,
)


class Transport:
    def __init__(self, auth_token=None):
        self._auth_token = auth_token
        self._lock = threading.RLock()
        self._connected = threading.Event()
        self.sent = []
        self.sequence = 0

    @property
    def is_connected(self):
        return self._connected.is_set()

    def _generate_session_id(self, prefix):
        self.sequence += 1
        return f"{prefix}{self.sequence}"

    def _create_message(self, method, params):
        return {"m": method, "p": params}

    def _send(self, message):
        self.sent.append(message)
        return True

    def _parse_packets(self, message):
        return json.loads(message)

    def disconnect(self):
        self._connected.clear()

    def connect(self, timeout):
        self._on_open(SimpleNamespace(send=self.sent.append))


def connection():
    events = []
    clock = [1_800_000_000.0]
    stream = stream_class(Transport)("isolated-test-token", events.append, lambda: clock[0])
    stream._on_open(SimpleNamespace(send=stream.sent.append))
    return stream, events, clock


def packet(stream, method, params):
    payload = json.dumps({"m": method, "p": params})
    stream._on_message(None, f"~m~{len(payload)}~m~{payload}")


def fill(stream, sid, close):
    item = stream.series[sid]
    packet(
        stream,
        "timescale_update",
        [
            item["session"],
            {
                sid: {
                    "s": [
                        {"v": [1_799_000_000, 100, 110, 90, 101, None]},
                        {"v": [1_799_086_400, 100, 200, 80, close]},
                    ]
                }
            },
        ],
    )
    packet(stream, "series_completed", [item["session"], sid])


def test_native_series_have_unique_routing_and_no_daily_or_volume_fallback():
    stream, events, _ = connection()
    stream.reconcile(
        {("BIST", "THYAO", "2D"), ("BIST", "THYAO", "3W"), ("Kripto", "BTCUSDT", "3D")}
    )
    creates = [item for item in stream.sent if item["m"] == "create_series"]
    assert {item["p"][4] for item in creates} == {"2D", "3W", "3D"}
    assert len({item["p"][1] for item in creates}) == 3
    assert all(item["p"][-1] == 2 for item in creates)
    assert len({item["p"][0] for item in creates}) == 3
    for index, sid in enumerate(stream.series):
        fill(stream, sid, 120 + index)
    assert len(events) == 3
    assert {event["key"] for event in events} == {item["key"] for item in stream.series.values()}
    assert {event["rows"][-1][-1] for event in events} == {120, 121, 122}
    assert all(len(row) == 5 for event in events for row in event["rows"])
    # Wrong chart session must not update another symbol's same-named series.
    sid = next(iter(stream.series))
    packet(stream, "du", ["wrong-session", {sid: {"s": [{"v": [1_799_086_400, 1, 3, 1, 2]}]}}])
    assert len(events) == 3


def test_rejected_native_series_does_not_disconnect_other_symbols_or_quotes():
    stream, events, clock = connection()
    stream.reconcile({("BIST", "INVALID", "2D"), ("BIST", "THYAO", "1D")})
    bad = next((sid, item) for sid, item in stream.series.items() if item["key"][1] == "INVALID")
    packet(stream, "series_error", [bad[1]["session"], bad[0], "unsupported"])
    assert events[-1] == {"kind": "rejected", "key": ("BIST", "INVALID", "2D")}
    assert stream.healthy
    good = next(sid for sid, item in stream.series.items() if item["key"][1] == "THYAO")
    fill(stream, good, 125)
    packet(
        stream,
        "qsd",
        ["qs1", {"n": "BIST:THYAO", "s": "ok", "v": {"lp": 126, "lp_time": clock[0]}}],
    )
    assert events[-1]["kind"] == "quote" and events[-1]["price"] == 126
    packet(stream, "critical_error", ["authentication rejected"])
    assert not stream.healthy and stream.auth_failed


def test_subscription_removal_and_transport_timeout_are_latched():
    stream, events, clock = connection()
    stream.reconcile({("BIST", "THYAO", "6D"), ("BIST", "GARAN", "2W")})
    stream.reconcile({("BIST", "GARAN", "2W")})
    assert "BIST:THYAO" not in stream.members_by_full
    assert all(item["key"][1] == "GARAN" for item in stream.series.values())
    clock[0] += 91
    assert not stream.healthy
    packet(
        stream,
        "qsd",
        ["qs1", {"n": "BIST:GARAN", "s": "ok", "v": {"lp": 100, "lp_time": clock[0]}}],
    )
    assert events == []


def test_provider_one_series_per_chart_session_limit_preserves_shared_quote_socket():
    stream, events, _ = connection()
    chart_sessions = set()

    def provider_send(message):
        stream.sent.append(message)
        if message["m"] == "create_series":
            session = message["p"][0]
            if session in chart_sessions:
                packet(
                    stream,
                    "critical_error",
                    [session, "exceed limit of series in the session", "method: create_series"],
                )
            chart_sessions.add(session)

    stream._ws.send = provider_send
    wanted = {
        ("BIST", "THYAO", timeframe) for timeframe in ("1D", "2D", "3D", "6D", "1W", "2W", "3W")
    }
    stream.reconcile(wanted)
    assert stream.healthy
    assert len(chart_sessions) == len(wanted)
    assert len([item for item in stream.sent if item["m"] == "quote_add_symbols"]) == 1
    for sid in stream.series:
        fill(stream, sid, 120)
    assert {event["key"] for event in events} == wanted
    remaining = {("BIST", "THYAO", "1D")}
    stream.reconcile(remaining)
    assert set(stream.sessions) == remaining
    assert "BIST:THYAO" in stream.members_by_full
    assert not [item for item in stream.sent if item["m"] == "quote_remove_symbols"]
    stream.reconcile(set())
    assert not stream.sessions and not stream.sessions_by_id and not stream.members_by_full
    assert len([item for item in stream.sent if item["m"] == "quote_remove_symbols"]) == 1


def test_chart_session_protocol_limit_is_not_reported_as_authentication_failure():
    stream, _, _ = connection()
    packet(
        stream,
        "critical_error",
        ["cs_private", "exceed limit of series in the session", "method: create_series"],
    )
    assert not stream.healthy
    assert not stream.auth_failed


def test_close_only_native_updates_keep_quotes_and_latest_close_for_rollover():
    stream, events, clock = connection()
    stream.reconcile({("BIST", "THYAO", "1D")})
    sid, item = next(iter(stream.series.items()))
    fill(stream, sid, 120)
    for price in (130, 140, 125, 145):
        packet(
            stream,
            "du",
            [item["session"], {sid: {"st": [{"v": [1_799_086_400, 100, 200, 80, price]}]}}],
        )
        packet(
            stream,
            "qsd",
            ["qs1", {"n": "BIST:THYAO", "s": "ok", "v": {"lp": price, "lp_time": clock[0]}}],
        )
    assert len([event for event in events if event["kind"] == "bars"]) == 1
    assert [event["price"] for event in events if event["kind"] == "quote"] == [130, 140, 125, 145]
    assert item["rows"][1_799_086_400][-1] == 145
    # Providers may send only the new row. Its closed predecessor must carry
    # the final native close even though those close-only events were omitted.
    packet(
        stream,
        "du",
        [item["session"], {sid: {"st": [{"v": [1_799_172_800, 150, 160, 130, 155]}]}}],
    )
    assert events[-1]["kind"] == "bars"
    assert events[-1]["rows"][0][-1] == 145
    assert events[-1]["rows"][-1][0] == 1_799_172_800


@pytest.mark.parametrize(
    "row",
    [
        [1_799_000_000, 100, 110, 90, 102],  # Revised closed predecessor.
        [1_799_086_400, 101, 200, 80, 120],  # Revised opening.
        [1_799_086_400, 100, 201, 80, 120],  # New high.
        [1_799_086_400, 100, 200, 79, 120],  # New low.
    ],
)
def test_native_dedup_still_emits_predecessor_or_current_range_changes(row):
    stream, events, _ = connection()
    stream.reconcile({("BIST", "THYAO", "1D")})
    sid, item = next(iter(stream.series.items()))
    fill(stream, sid, 120)
    packet(stream, "du", [item["session"], {sid: {"st": [{"v": row}]}}])
    assert len(events) == 2
    assert tuple(float(value) for value in row) in events[-1]["rows"]
    packet(stream, "du", [item["session"], {sid: {"st": [{"v": row}]}}])
    packet(stream, "series_completed", [item["session"], sid])
    assert len(events) == 2


def test_native_metadata_changes_emit_without_waiting_for_price_or_ohl_change():
    stream, events, _ = connection()
    stream.reconcile({("BIST", "THYAO", "1D")})
    sid, item = next(iter(stream.series.items()))
    metadata = {"timezone": "Europe/Istanbul", "session": "0900-1810"}
    packet(stream, "symbol_resolved", [item["session"], "sym", metadata])
    assert not events  # Series completion is still required.
    fill(stream, sid, 120)
    packet(stream, "symbol_resolved", [item["session"], "sym", metadata])
    assert len(events) == 1
    revised = {**metadata, "session": "1000-1810"}
    packet(stream, "symbol_resolved", [item["session"], "sym", revised])
    assert len(events) == 2 and events[-1]["metadata"] == revised
    assert events[0]["metadata"] == metadata  # Earlier observation stays frozen.


def test_daily_rollover_requires_and_emits_first_real_unchanged_htf_witness():
    stream, events, _ = connection()
    stream.reconcile({("BIST", "THYAO", "1D"), ("BIST", "THYAO", "2D")})
    by_tf = {item["key"][2]: (sid, item) for sid, item in stream.series.items()}
    daily_sid, daily = by_tf["1D"]
    htf_sid, htf = by_tf["2D"]
    fill(stream, daily_sid, 120)
    fill(stream, htf_sid, 120)
    assert len(events) == 2
    packet(
        stream,
        "du",
        [daily["session"], {daily_sid: {"st": [{"v": [1_799_172_800, 120, 130, 110, 125]}]}}],
    )
    assert len(events) == 3 and events[-1]["key"][2] == "1D"
    # The daily update alone does not manufacture a new HTF witness.
    for index, price in enumerate((125, 126)):
        packet(
            stream,
            "du",
            [htf["session"], {htf_sid: {"st": [{"v": [1_799_086_400, 100, 200, 80, price]}]}}],
        )
        assert len(events) == 4
        assert events[-1]["key"][2] == "2D"
        if index == 0:
            assert events[-1]["rows"][-1][-1] == price


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("max sessions rate reached", "session_rate_limited"),
        ("unexpected protocol request", "provider_protocol_error"),
        ("authentication required", "authentication_failed"),
        ("session_start_error: max charts per connection reached", "chart_capacity_exceeded"),
    ],
)
def test_protocol_failure_is_latched_and_only_safe_category_is_exposed(message, expected, caplog):
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        lambda _: None,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    pool.configure({("BIST", "THYAO", "1D")})
    stream = next(iter(pool._streams.values()))
    private_marker = "PRIVATE_PROVIDER_SESSION_MARKER"
    packet(stream, "protocol_error", [message, private_marker])
    assert not stream.healthy and not pool.connected
    assert stream.auth_failed == (expected == "authentication_failed")
    assert pool.status()["failure_codes"] == [expected]
    assert pool.status()["protocol_errors"] == 1
    assert private_marker not in json.dumps(pool.status())
    assert private_marker not in caplog.text


def test_slow_subscription_send_does_not_block_receiver_metadata_or_quotes():
    stream, events, clock = connection()
    callback_completed = threading.Event()
    workers = []

    def provider_send(message):
        stream.sent.append(message)
        if message["m"] != "quote_add_symbols":
            return

        def receive():
            session = next(iter(stream.sessions_by_id))
            packet(stream, "symbol_resolved", [session, "sym", {"timezone": "Europe/Istanbul"}])
            packet(
                stream,
                "qsd",
                ["qs1", {"n": "BIST:THYAO", "s": "ok", "v": {"lp": 126, "lp_time": clock[0]}}],
            )
            callback_completed.set()

        worker = threading.Thread(target=receive, daemon=True)
        workers.append(worker)
        worker.start()
        # The socket sender may wait for the remote consumer to make progress.
        # Holding the receiver lock here used to deadlock until the send failed.
        if not callback_completed.wait(1):
            raise TimeoutError("Synthetic receiver starvation")

    stream._ws.send = provider_send
    try:
        stream.reconcile({("BIST", "THYAO", "1D"), ("BIST", "THYAO", "2D")})
    finally:
        for worker in workers:
            worker.join(timeout=2)
    assert stream.healthy
    assert callback_completed.is_set()
    assert events[0]["kind"] == "quote"
    assert next(iter(stream.sessions_by_id.values()))["metadata"]["timezone"] == "Europe/Istanbul"


def test_large_pool_admission_is_incremental_and_resumes_without_dropping_quotes():
    events = []
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        events.append,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    wanted = {
        ("BIST", f"SYM{index}", timeframe)
        for index in range(80)
        for timeframe in ("1D", "2D", "3W")
    }
    pool.configure(wanted)
    status = pool.status()
    assert status["connections"] == MAX_LIVE_CONNECTIONS
    assert status["subscriptions"] <= MAX_SERIES_PER_RECONCILE * MAX_LIVE_CONNECTIONS
    assert status["subscriptions_pending"] == len(wanted) - status["subscriptions"] > 0
    assert pool.needs_reconcile and pool.connected
    first_stream = next(iter(pool._streams.values()))
    full, member = next(iter(first_stream.members_by_full.items()))
    packet(first_stream, "qsd", ["qs1", {"n": full, "s": "ok", "v": {"lp": 126, "lp_time": 100}}])
    assert events[-1]["member"] == member
    for _ in range(20):
        if not pool.needs_reconcile:
            break
        before = pool.status()["subscriptions"]
        pool.configure(wanted)
        assert (
            0
            < pool.status()["subscriptions"] - before
            <= MAX_SERIES_PER_RECONCILE * MAX_LIVE_CONNECTIONS
        )
    assert not pool.needs_reconcile
    assert pool.status()["subscriptions"] == len(wanted)
    assert pool.status()["subscriptions_pending"] == 0
    assert all(pool.member_ready(key[:2]) for key in wanted)
    assert not pool.member_ready(("BIST", "ABSENT"))
    for stream in pool._streams.values():
        quotes = [message for message in stream.sent if message["m"] == "quote_add_symbols"]
        assert len(quotes) == len(stream.members_by_full)
    before = sum(len(stream.sent) for stream in pool._streams.values())
    pool.configure(wanted)
    assert sum(len(stream.sent) for stream in pool._streams.values()) == before
    pool.close()
    assert not pool.member_ready(member) and not pool.needs_reconcile


def test_partial_pool_reconfiguration_removes_old_members_without_admitting_cancelled_demand():
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        lambda _: None,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    initial = {("BIST", f"SYM{index}", "1D") for index in range(100)}
    pool.configure(initial)
    assert pool.needs_reconcile
    kept = {next(iter(initial))}
    pool.configure(kept)
    assert not pool.needs_reconcile
    assert pool.status()["subscriptions"] == 1
    assert pool.member_ready(next(iter(kept))[:2])
    assert not pool.member_ready(next(iter(initial - kept))[:2])
    pool.configure(set())
    assert not pool.needs_reconcile
    assert pool.status() == {
        "connections": 0,
        "connected": 0,
        "subscriptions": 0,
        "subscriptions_pending": 0,
        "protocol_errors": 0,
        "failure_codes": [],
    }


def test_member_readiness_checks_only_its_indexed_native_series():
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        lambda _: None,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    member = ("BIST", "THYAO")
    wanted = {(*member, timeframe) for timeframe in ("1D", "2D", "3W")}
    pool.configure(wanted)

    class UnscannableSet(set):
        def __iter__(self):
            raise AssertionError("A member readiness check must not scan its entire shard")

    class UnscannableDict(dict):
        def __iter__(self):
            raise AssertionError("A member readiness check must not copy all registered sessions")

    slot = pool._member_slots[member]
    pool._wanted_by_slot[slot] = UnscannableSet(pool._wanted_by_slot[slot])
    pool._streams[slot].sessions = UnscannableDict(pool._streams[slot].sessions)
    assert pool.member_ready(member)
    missing = next(iter(wanted))
    pool._streams[slot].sessions.pop(missing)
    assert not pool.member_ready(member)
    assert pool._wanted_by_member[member] == wanted
    pool.close()
    assert pool._wanted_by_member == {}


def test_verified_chart_capacity_plans_whole_members_across_balanced_sockets():
    timeframes = ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M")
    requested = {("BIST", f"SYM{index:04}", tf) for index in range(805) for tf in timeframes}
    groups, slots, refused = plan_native_subscriptions(requested, lease_long_timeframes=False)
    assert len(groups) == MAX_LIVE_CONNECTIONS
    assert all(len(keys) == MAX_CHARTS_PER_CONNECTION for keys in groups.values())
    assert sum(map(len, groups.values())) == MAX_PROVIDER_SERIES == 2000
    assert len(slots) == 200 and len(refused) == 605
    assert not (set(slots) & refused)
    for member, slot in slots.items():
        assert {key[2] for key in groups[slot] if key[:2] == member} == set(timeframes)
    assert plan_native_subscriptions(
        sorted(requested, reverse=True), lease_long_timeframes=False
    ) == (groups, slots, refused)
    # An added lexically earlier symbol cannot move existing ordered streams.
    extended = requested | {("BIST", "A", "1D")}
    _, new_slots, _ = plan_native_subscriptions(extended, slots, lease_long_timeframes=False)
    assert all(new_slots[member] == slot for member, slot in slots.items())


def test_oversized_member_is_refused_atomically_and_does_not_consume_other_capacity():
    requested = {("BIST", "HUGE", str(value)) for value in range(1, 502)}
    requested.add(("BIST", "THYAO", "1D"))
    groups, slots, refused = plan_native_subscriptions(requested, lease_long_timeframes=False)
    assert refused == {("BIST", "HUGE")}
    assert set(slots) == {("BIST", "THYAO")}
    assert sum(map(len, groups.values())) == 1


def test_invalid_or_overloaded_pool_plan_is_rejected_before_any_transport_change():
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        lambda _: None,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    requested = {("BIST", f"SYM{index:04}", "1D") for index in range(501)}
    with pytest.raises(ValueError, match="kapasitesi"):
        pool.configure(requested, member_slots={key[:2]: 0 for key in requested})
    assert not pool._streams and not pool._wanted_by_slot
    with pytest.raises(ValueError, match="eşleşmiyor"):
        pool.configure(requested, member_slots={})
    assert not pool._streams
    pool.configure({("BIST", "THYAO", "1D")})
    member, slot = next(iter(pool._member_slots.items()))
    before = pool.status()
    sent = sum(len(stream.sent) for stream in pool._streams.values())
    with pytest.raises(ValueError, match="devamlılık"):
        pool.configure({(*member, "1D")}, member_slots={member: (slot + 1) % 4})
    assert pool.status() == before
    assert sum(len(stream.sent) for stream in pool._streams.values()) == sent


def test_unplanned_pool_demand_over_provider_capacity_is_never_silently_truncated():
    pool = NativeStreamPool(
        Transport,
        "isolated-test-token",
        1,
        lambda _: None,
        clock=lambda: 100,
        lease_long_timeframes=False,
    )
    requested = {("BIST", f"SYM{index:04}", "1D") for index in range(MAX_PROVIDER_SERIES + 1)}
    with pytest.raises(ValueError, match="planlanamadı"):
        pool.configure(requested)
    assert not pool._streams and not pool._wanted_by_slot


def test_single_stream_capacity_guard_rejects_before_creating_chart_sessions():
    stream, _, _ = connection()
    before = len(stream.sent)
    with pytest.raises(ValueError, match="kapasitesi"):
        stream.reconcile({("BIST", f"SYM{index:04}", "1D") for index in range(501)})
    assert len(stream.sent) == before
    assert not stream.sessions and stream.healthy


def test_malformed_private_payload_and_send_error_are_never_logged(caplog):
    stream, _, _ = connection()
    private_marker = "SYNTHETIC_PRIVATE_PAYLOAD_NOT_FOR_LOGGING"
    stream._on_message(None, f"~m~{len(private_marker)}~m~{private_marker}")
    assert not stream.healthy
    assert private_marker not in caplog.text
    other, _, _ = connection()
    other._ws = SimpleNamespace(send=lambda *_: (_ for _ in ()).throw(RuntimeError(private_marker)))
    with pytest.raises(ValueError, match="gönderilemedi") as failure:
        other.reconcile({("BIST", "THYAO", "2D")})
    assert private_marker not in str(failure.value)
    assert not other.healthy and private_marker not in caplog.text
