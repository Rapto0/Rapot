"""Offline wire fixtures for native multiplexing; no account/network access."""

import json
import threading
from types import SimpleNamespace

import pytest

from infrastructure.providers.custom_indicator_stream import stream_class


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
