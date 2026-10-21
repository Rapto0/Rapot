"""Bounded dedicated history transport; no network or account credentials."""

import queue
import threading
import time

import pandas as pd
import pytest

from infrastructure.providers.native_indicator_history import (
    NativeIndicatorHistory,
    _message,
    _packets,
)

META = {"timezone": "Europe/Istanbul", "session": "1000-1805:23456", "session_holidays": "20261029"}


class Wire:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.sockets = []
        self.created = threading.Event()
        self.max_charts = 0

    def __call__(self, url, **callbacks):
        assert not any(not socket.closed.is_set() for socket in self.sockets)
        socket = Socket(self, callbacks)
        self.sockets.append(socket)
        return socket

    def sent(self, socket, packet):
        if isinstance(packet, str):
            return
        method, params = packet["m"], packet["p"]
        if method == "chart_create_session":
            socket.charts.add(params[0])
            self.max_charts = max(self.max_charts, len(socket.charts))
            self.created.set()
        elif method == "chart_delete_session":
            socket.charts.remove(params[0])
        elif method == "resolve_symbol":
            if self.mode != "missing_metadata":
                socket.push("symbol_resolved", [params[0], params[1], META])
        elif method == "create_series":
            session, series, _, _, _, count, _ = params
            socket.incoming.put("~m~6~m~~h~123")
            if self.mode in {"critical_error", "protocol_error", "series_error", "symbol_error"}:
                socket.push(self.mode, [session, series, "synthetic private provider error"])
                return
            if self.mode == "close":
                socket.close()
                return
            if self.mode == "malformed":
                socket.incoming.put("~m~999~m~{}")
                return
            if self.mode == "wrong_session":
                session = "old_session"
            if self.mode == "wrong_series":
                series = "old_series"
            if self.mode == "over_capacity":
                count += 1
            rows = [
                {"v": [1700000000 + i * 86400, 100 + i, 102 + i, 98 + i, 101 + i]}
                for i in range(count)
            ]
            for first in range(0, count, 127):
                socket.push(
                    "timescale_update", [session, {series: {"s": rows[first : first + 127]}}]
                )
            if self.mode != "half":
                socket.push("series_completed", [session, series])


class Socket:
    def __init__(self, wire, callbacks):
        self.wire, self.callbacks = wire, callbacks
        self.incoming = queue.Queue()
        self.closed = threading.Event()
        self.sent = []
        self.charts = set()

    def push(self, method, params):
        self.incoming.put(_message(method, params))

    def send(self, raw):
        if self.closed.is_set():
            raise ValueError("closed")
        for packet in _packets(raw):
            self.sent.append(packet)
            self.wire.sent(self, packet)
        return True

    def run_forever(self, **kwargs):
        assert kwargs == {"origin": "https://www.tradingview.com", "reconnect": 0}
        self.run_options = kwargs
        self.callbacks["on_open"](self)
        while not self.closed.is_set():
            try:
                item = self.incoming.get(timeout=0.01)
            except queue.Empty:
                continue
            self.callbacks["on_message"](self, item)
        self.callbacks["on_close"](self, None, None)

    def close(self):
        self.closed.set()
        self.charts.clear()


def request(history, timeframe="1D", *, bars=519, token="synthetic-token", epoch=1):
    return history.get_history(
        "THYAO", exchange="BIST", timeframe=timeframe, bars=bars, token=token, epoch=epoch
    )


def test_ten_native_histories_share_one_socket_and_retire_each_chart():
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        for tf in ("1D", "2D", "3D", "4D", "5D", "6D", "1W", "2W", "3W", "1M"):
            result = request(history, tf)
            assert result.attrs == {"native_timeframe": tf, "session_metadata": META}
            assert str(result.index.tz) == "Europe/Istanbul"
            assert list(result.columns) == ["Open", "High", "Low", "Close"]
            assert result["Close"].tolist() == [101 + i for i in range(519)]
            assert not wire.sockets[0].charts
        status = history.status()
        assert len(wire.sockets) == status["connections_opened"] == 1
        assert (
            status["requests_completed"]
            == status["charts_created"]
            == status["charts_retired"]
            == 10
        )
        assert status["requests_failed"] == status["active_requests"] == 0
        assert status["heartbeats"] == 10 and wire.max_charts == 1
        auth = [
            p for p in wire.sockets[0].sent if isinstance(p, dict) and p["m"] == "set_auth_token"
        ]
        assert len(auth) == 1
    finally:
        history.close()


def test_full_capacity_native_history_has_exact_values_and_no_manufactured_volume():
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        result = request(history, "3W", bars=12000)
        expected = pd.DataFrame(
            [[100 + i, 102 + i, 98 + i, 101 + i] for i in range(12000)],
            columns=["Open", "High", "Low", "Close"],
            index=pd.to_datetime(
                [1700000000 + i * 86400 for i in range(12000)], unit="s", utc=True
            ).tz_convert("Europe/Istanbul"),
        )
        pd.testing.assert_frame_equal(result, expected)
    finally:
        history.close()


def test_websocket_client_handshake_has_one_canonical_origin():
    from websocket._handshake import _get_handshake_headers

    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        request(history, bars=3)
        socket = wire.sockets[0]
        options = {**socket.run_options}
        if "header" in socket.callbacks:
            options["header"] = socket.callbacks["header"]
        headers, _ = _get_handshake_headers(
            "/socket.io/websocket?type=chart",
            "wss://data.tradingview.com/socket.io/websocket?type=chart",
            "data.tradingview.com",
            443,
            options,
        )
        assert [header for header in headers if header.lower().startswith("origin:")] == [
            "Origin: https://www.tradingview.com"
        ]
    finally:
        history.close()


@pytest.mark.parametrize(
    "mode",
    [
        "half",
        "missing_metadata",
        "wrong_session",
        "wrong_series",
        "critical_error",
        "protocol_error",
        "series_error",
        "symbol_error",
        "over_capacity",
        "malformed",
        "close",
    ],
)
def test_incomplete_or_invalid_response_closes_socket_and_next_request_reconnects(mode):
    wire = Wire(mode)
    history = NativeIndicatorHistory(ws_factory=wire, timeout=0.3)
    try:
        with pytest.raises(ValueError, match="Native indicator history unavailable"):
            request(history, bars=12)
        assert wire.sockets[0].closed.is_set()
        assert history.status()["requests_completed"] == 0
        wire.mode = "ok"
        result = request(history, bars=12)
        assert len(result) == 12 and len(wire.sockets) == 2
        assert history.status()["requests_failed"] == 1
        assert history.status()["active_requests"] == 0
    finally:
        history.close()


def test_token_refresh_reuses_socket_but_account_epoch_reconnects():
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    try:
        request(history, bars=3)
        request(history, bars=3, token="synthetic-refresh")
        assert len(wire.sockets) == 1
        auth = [
            p["p"]
            for p in wire.sockets[0].sent
            if isinstance(p, dict) and p["m"] == "set_auth_token"
        ]
        assert auth == [["synthetic-token"], ["synthetic-refresh"]]
        request(history, bars=3, token="synthetic-account-two", epoch=2)
        assert wire.sockets[0].closed.is_set() and len(wire.sockets) == 2
        # A late callback from the retired connection cannot fail the new one.
        wire.sockets[0].callbacks["on_message"](
            wire.sockets[0], _message("critical_error", ["old account"])
        )
        assert history.status()["connected"]
    finally:
        history.close()


def test_account_close_cancels_inflight_history_without_waiting_for_timeout():
    wire = Wire("half")
    history = NativeIndicatorHistory(ws_factory=wire, timeout=5)
    errors = []

    def run():
        try:
            request(history, bars=12)
        except ValueError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=run)
    thread.start()
    assert wire.created.wait(1)
    start = time.monotonic()
    history.close()
    thread.join(timeout=1)
    assert not thread.is_alive() and time.monotonic() - start < 1
    assert errors == ["Native indicator history unavailable"]
    assert history.status()["active_requests"] == 0
    with pytest.raises(ValueError):
        request(history, bars=12)
    assert len(wire.sockets) == 1


def test_invalid_request_never_starts_transport():
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire)
    with pytest.raises(ValueError):
        request(history, bars=12001)
    with pytest.raises(ValueError):
        request(history, token="unauthorized_user_token")
    assert not wire.sockets


def test_old_chart_packets_do_not_complete_the_next_request():
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=0.3)
    try:
        request(history, bars=3)
        old = next(
            p["p"]
            for p in wire.sockets[0].sent
            if isinstance(p, dict) and p["m"] == "create_series"
        )
        wire.mode = "half"
        wire.sockets[0].push("series_completed", old[:2])
        with pytest.raises(ValueError):
            request(history, "2D", bars=3)
        assert history.status()["requests_completed"] == 1
    finally:
        history.close()


def test_byte_bound_closes_transport_without_publishing_partial_rows(monkeypatch):
    monkeypatch.setattr("infrastructure.providers.native_indicator_history.MAX_WIRE_BYTES", 512)
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=0.3)
    try:
        with pytest.raises(ValueError):
            request(history, bars=12)
        assert history.status()["requests_completed"] == 0
        assert wire.sockets[0].closed.is_set()
    finally:
        history.close()


def test_concurrent_caller_cannot_create_another_socket_or_chart():
    wire = Wire("half")
    history = NativeIndicatorHistory(ws_factory=wire, timeout=5)
    errors = []

    def run():
        try:
            request(history, bars=12)
        except ValueError as exc:
            errors.append(str(exc))

    thread = threading.Thread(target=run)
    thread.start()
    try:
        assert wire.created.wait(1)
        with pytest.raises(ValueError, match="worker busy"):
            request(history, bars=12)
        assert len(wire.sockets) == wire.max_charts == 1
    finally:
        history.close()
        thread.join(timeout=1)
    assert not thread.is_alive() and len(errors) == 1


def test_chart_creation_spacing_is_bounded_even_for_instant_provider_replies(monkeypatch):
    spacing = 0.025
    monkeypatch.setattr(
        "infrastructure.providers.native_indicator_history.MIN_REQUEST_INTERVAL", spacing
    )
    wire = Wire()
    history = NativeIndicatorHistory(ws_factory=wire, timeout=2)
    starts = []
    original = wire.sent

    def sent(socket, packet):
        if isinstance(packet, dict) and packet["m"] == "chart_create_session":
            starts.append(time.monotonic())
        original(socket, packet)

    wire.sent = sent
    try:
        for _ in range(4):
            request(history, bars=3)
        assert all(right - left >= spacing * 0.95 for left, right in zip(starts, starts[1:]))
    finally:
        history.close()


@pytest.mark.parametrize("cancel", [True, False])
def test_late_handshake_after_close_or_timeout_cannot_leave_an_orphan_socket(cancel):
    entered, resume, exited = threading.Event(), threading.Event(), threading.Event()
    sockets = []

    class DelayedSocket(Socket):
        def run_forever(self, **kwargs):
            entered.set()
            assert resume.wait(3)
            # websocket-client starts a fresh socket after setting its own
            # keep_running=True, even if close happened before startup.
            self.closed.clear()
            self.keep_running = True
            try:
                super().run_forever(**kwargs)
            finally:
                exited.set()

    def factory(_url, **callbacks):
        socket = DelayedSocket(Wire("half"), callbacks)
        sockets.append(socket)
        return socket

    history = NativeIndicatorHistory(ws_factory=factory, timeout=0.05 if not cancel else 5)
    errors = []

    def run():
        try:
            request(history, bars=3)
        except ValueError as exc:
            errors.append(str(exc))

    caller = threading.Thread(target=run)
    caller.start()
    try:
        assert entered.wait(1)
        if cancel:
            history.close()
        caller.join(timeout=2)
        assert not caller.is_alive() and errors == ["Native indicator history unavailable"]
        assert not exited.is_set()  # The handshake is still intentionally held.
        resume.set()
        assert exited.wait(1)
        assert sockets[0].closed.is_set()
        assert not history.status()["connected"]
        assert history.status()["requests_completed"] == 0
        assert sockets[0].sent == []
    finally:
        resume.set()
        history.close()
        caller.join(timeout=1)
