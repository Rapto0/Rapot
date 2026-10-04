"""The autonomous stream uses the existing authenticated credential boundary."""

import threading
from types import SimpleNamespace

import pytest

from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError


class Stream:
    def __init__(self, auth_token):
        self.token = auth_token
        self.callbacks = []
        self._connected = threading.Event()
        self.closed = False
        self.subscriptions = []

    @property
    def is_connected(self):
        return self._connected.is_set()

    def on_any_quote(self, callback):
        self.callbacks.append(callback)

    def connect(self, timeout):
        assert timeout == 3
        self._connected.set()

    def subscribe(self, symbol, exchange):
        self.subscriptions.append((symbol, exchange))

    @staticmethod
    def _parse_packets(message):
        return [message]

    def _on_message(self, ws, message):
        self.last_message = message

    def disconnect(self):
        self.closed = True
        self._connected.clear()


class Module:
    TradingViewStream = Stream

    def __init__(self):
        self.auth = None

    def set_tradingview_auth(self, **_):
        self.auth = {"auth_token": "synthetic-private-token"}
        return self.auth

    def get_tradingview_auth(self):
        return self.auth

    def clear_tradingview_auth(self):
        self.auth = None

    def clear_evds_key(self):
        pass

    def clear_twitter_auth(self):
        pass


@pytest.fixture
def gateway(tmp_path):
    settings = SimpleNamespace(
        borsapy_credentials_path=str(tmp_path / "credentials.enc"),
        jwt_secret_key="synthetic-encryption-key-at-least-32-chars",
        database_path=str(tmp_path / "main.sqlite3"),
        borsapy_max_streams=3,
        borsapy_stream_idle_seconds=120,
    )
    module = Module()
    clock = [0.0]
    result = BorsapyGateway(
        settings, loader=lambda: module, version_reader=lambda: "0.11.0", clock=lambda: clock[0]
    )
    result.monotonic = clock
    yield result
    result.close()


def authenticate(gateway):
    gateway.configure(
        {"session": "synthetic-session-123456", "session_sign": "synthetic-sign-123456"}
    )


def test_no_anonymous_feed_and_separate_2000_symbol_capacity(gateway):
    with pytest.raises(BorsapyGatewayError):
        gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    authenticate(gateway)
    handle = gateway.create_alarm_quote_stream([f"S{i}" for i in range(2000)], lambda *_: None)
    assert handle.connected
    assert len(handle._entry["stream"].subscriptions) == 2000
    assert gateway._quotes is None  # Dashboard/browser pool is independent.
    with pytest.raises(BorsapyGatewayError):
        gateway.create_alarm_quote_stream(["OTHER"], lambda *_: None)


def test_callback_only_numeric_fields_and_credential_edit_closes_handle(gateway):
    authenticate(gateway)
    observations = []
    handle = gateway.create_alarm_quote_stream(["THYAO"], lambda *args: observations.append(args))
    callback = handle._entry["stream"].callbacks[-1]
    callback("THYAO", {"last": 12.5, "timestamp": 1791187200, "private": "must-not-cross"})
    assert len(observations) == 1
    assert set(observations[0][1]) == {"price", "source_timestamp", "received_at"}
    assert "must-not-cross" not in str(observations)
    epoch = gateway.memory_epoch()
    gateway.clear()
    assert gateway.memory_epoch() != epoch and not handle.connected
    callback("THYAO", {"last": 99, "timestamp": 1791187200})
    assert len(observations) == 1


def test_dead_handle_is_closed_before_replacement(gateway):
    authenticate(gateway)
    first = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    first._entry["error"] = True
    second = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    assert first._entry["stream"].closed and second.connected


@pytest.mark.parametrize(
    "symbols", [[], ["THYAO", "THYAO"], ["../x"], ["a"], [f"S{i}" for i in range(2001)]]
)
def test_invalid_universe_rejected_before_authentication(gateway, symbols):
    with pytest.raises(BorsapyGatewayError) as error:
        gateway.create_alarm_quote_stream(symbols, lambda *_: None)
    assert error.value.status_code == 422


def test_transport_silence_grace_and_monotonic_expiry_replace_half_open_socket(
    gateway, monkeypatch
):
    authenticate(gateway)
    handle = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    epoch = gateway.memory_epoch()
    monkeypatch.setattr("application.services.borsapy_gateway.time.time", lambda: 1e12)
    gateway.monotonic[0] = 89.999
    assert handle.connected
    gateway.monotonic[0] = 90
    assert handle._entry["stream"].is_connected  # Socket never reported a close/error.
    assert not handle.connected
    assert gateway.memory_epoch() == epoch
    replacement = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    assert handle._entry["stream"].closed and replacement.connected
    assert gateway.memory_epoch() == epoch  # Reconnect does not alter account identity.


def test_heartbeat_and_control_frames_keep_transport_alive_without_market_quotes(gateway):
    authenticate(gateway)
    observed = []
    handle = gateway.create_alarm_quote_stream(["THYAO"], lambda *args: observed.append(args))
    stream = handle._entry["stream"]
    for seconds, message in [(80, "~h~1"), (160, {"m": "quote_completed"}), (240, "~h~2")]:
        gateway.monotonic[0] = seconds
        stream._on_message(None, message)
        assert handle.connected and stream.last_message == message
    assert observed == [] and handle._entry["received"] == {}
    gateway.monotonic[0] = 329.999
    assert handle.connected
    gateway.monotonic[0] = 330
    assert not handle.connected


@pytest.mark.parametrize("poll_before_frame", [False, True])
def test_late_frame_cannot_revive_expired_generation(gateway, poll_before_frame):
    authenticate(gateway)
    observed = []
    handle = gateway.create_alarm_quote_stream(["THYAO"], lambda *args: observed.append(args))
    stream = handle._entry["stream"]
    gateway.monotonic[0] = 91
    if poll_before_frame:
        assert not handle.connected
    stream._on_message(None, "~h~late")
    stream.callbacks[-1]("THYAO", {"last": 100, "timestamp": 1791187200})
    assert not handle.connected and observed == []
