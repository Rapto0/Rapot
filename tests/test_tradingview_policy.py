"""Offline account protection: no provider traffic or real credentials."""

import json
import threading
from types import SimpleNamespace

import pytest

from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError
from infrastructure.providers.custom_indicator_stream import NativeStreamPool
from infrastructure.providers.native_indicator_history import NativeIndicatorHistory, _message
from infrastructure.providers.tradingview_policy import (
    TradingViewPolicy,
    TradingViewPolicyError,
    packet_restriction,
    restriction_reason,
)
from tests.test_borsapy_gateway import SESSION, SIGN, connect
from tests.test_borsapy_gateway import gateway as gateway_fixture
from tests.test_custom_indicator_stream import Transport, packet
from tests.test_native_indicator_history import Wire

gateway = gateway_fixture


@pytest.mark.parametrize("status", [401, 403, 429])
def test_structured_http_restrictions_only(status):
    assert restriction_reason(SimpleNamespace(status_code=status)) == "http_rejected"
    assert (
        restriction_reason(SimpleNamespace(response=SimpleNamespace(status_code=status)))
        == "http_rejected"
    )


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("403"),
        RuntimeError("429"),
        SimpleNamespace(status_code=500),
        SimpleNamespace(status_code="403"),
        SimpleNamespace(protection_reason=[]),
        SimpleNamespace(status_code={}),
    ],
)
def test_generic_errors_and_untrusted_text_do_not_latch(error):
    assert restriction_reason(error) is None


def test_pinned_legacy_wrapper_preserves_handshake_denial_only():
    from borsapy.exceptions import APIError

    assert (
        restriction_reason(APIError("TradingView error: Handshake status 429 Too Many Requests"))
        == "http_rejected"
    )
    assert restriction_reason(APIError("TradingView error: timeout 429")) is None
    assert (
        restriction_reason(RuntimeError("TradingView error: Handshake status 403 Forbidden"))
        is None
    )


@pytest.mark.parametrize(
    "method,detail,expected",
    [
        ("auth_error", "", "authentication_failed"),
        ("critical_error", "invalid_auth_token", "authentication_failed"),
        ("protocol_error", "max sessions rate reached", "provider_rate_limited"),
        ("protocol_error", "max charts per connection reached", "provider_rate_limited"),
        ("critical_error", "suspicious activity on your account", "account_restricted"),
        ("protocol_error", "permission_denied", "authentication_failed"),
        ("symbol_error", "permission_denied", None),
        ("symbol_error", "not authorized", None),
        ("symbol_error", "unknown symbol", None),
        ("protocol_error", "temporary timeout", None),
        ("critical_error", "provider unavailable", None),
        ("qsd", "suspicious activity", None),
    ],
)
def test_packet_signals_are_explicit_and_scoped(method, detail, expected):
    assert packet_restriction({"m": method, "p": [detail]}) == expected


def test_durable_marker_contains_no_payload_and_never_auto_resets(tmp_path):
    path = tmp_path / "protection.json"
    policy = TradingViewPolicy(path)
    assert policy.trip("account_restricted")
    record = json.loads(path.read_text())
    assert set(record) == {"version", "reason", "recorded_at"}
    assert record["reason"] == "account_restricted"
    assert not policy.trip("authentication_failed")
    restarted = TradingViewPolicy(path)
    assert restarted.blocked
    path.unlink()
    assert restarted.blocked  # Removing the marker never changes a running process.
    with pytest.raises(TradingViewPolicyError):
        restarted.before_request("connect")


@pytest.mark.parametrize("content", ["invalid", '{"version":1,"reason":"unexpected"}', "x" * 4097])
def test_corrupt_marker_fails_closed(tmp_path, content):
    path = tmp_path / "protection.json"
    path.write_text(content)
    assert TradingViewPolicy(path).status()["reason"] == "policy_storage_error"


def test_failed_persistence_still_closes_current_process(tmp_path, monkeypatch):
    policy = TradingViewPolicy(tmp_path / "protection.json")
    monkeypatch.setattr(
        "infrastructure.providers.tradingview_policy.os.replace",
        lambda *_: (_ for _ in ()).throw(OSError()),
    )
    assert policy.trip("http_rejected")
    assert policy.blocked and policy.status()["reason"] == "policy_storage_error"
    assert not list(tmp_path.glob(".tv-protection-*"))


def test_shared_budget_and_auth_floor_use_one_clock_without_sleep(tmp_path, monkeypatch):
    clock = [0.0]
    policy = TradingViewPolicy(
        tmp_path / "protection.json", rate=4, burst=4, clock=lambda: clock[0]
    )
    waits = []

    def advance(delay):
        waits.append(delay)
        clock[0] += delay

    monkeypatch.setattr(policy._wake, "wait", advance)
    for kind in ("auth", "connect", "history", "chart", "request"):
        policy.before_request(kind)
    assert clock[0] == pytest.approx(0.25)
    assert waits and policy.status()["requests_admitted"] == 5
    with pytest.raises(TradingViewPolicyError) as error:
        policy.before_request("auth")
    assert error.value.status_code == 429 and error.value.retry_after_seconds == 300
    assert not policy.blocked
    clock[0] = 300
    policy.before_request("auth")


def test_latch_interrupts_waiting_budget_without_admitting_request(tmp_path):
    policy = TradingViewPolicy(tmp_path / "protection.json", burst=1, clock=lambda: 0)
    policy.before_request("connect")
    result = []

    def wait():
        try:
            policy.before_request("chart")
        except TradingViewPolicyError:
            result.append("blocked")

    thread = threading.Thread(target=wait)
    thread.start()
    policy.trip("provider_rate_limited")
    thread.join(timeout=1)
    assert not thread.is_alive() and result == ["blocked"]
    assert policy.status()["requests_admitted"] == 1


def test_gateway_latch_closes_every_transport_and_survives_edits_and_restart(gateway):
    connect(gateway)
    quote = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    gateway.stream_snapshot("THYAO")
    chart = next(iter(gateway._streams.values()))["stream"]
    closed = []
    gateway._custom_history = SimpleNamespace(close=lambda: closed.append("history"))
    gateway._custom_streams.append(SimpleNamespace(close=lambda: closed.append("native")))
    gateway._trip_tradingview("account_restricted")
    assert not gateway.tradingview_enabled
    gateway._protection_close_thread.join(timeout=2)
    assert not quote.connected and chart.closed
    assert set(closed) == {"history", "native"}
    auth_calls = gateway.fake.auth_calls
    assert (
        gateway.configure({"session": SESSION, "session_sign": SIGN})["state"] == "provider_paused"
    )
    with pytest.raises(BorsapyGatewayError) as error:
        gateway.verify()
    assert error.value.status_code == 503
    gateway.reset_alarm_auth(gateway.memory_epoch())
    assert gateway.fake.auth_calls == auth_calls
    restarted = BorsapyGateway(
        gateway.settings,
        loader=lambda: gateway.fake,
        version_reader=lambda: "0.11.0",
        policy=TradingViewPolicy(gateway._provider_policy.path),
    )
    try:
        assert not restarted.tradingview_enabled
        assert restarted.status()["configured"]
        assert restarted.run(lambda _: 42, tradingview=False) == 42
        assert restarted.run_public(lambda _: "calendar") == "calendar"
        with pytest.raises(BorsapyGatewayError):
            restarted.quote_snapshot([("BIST", "THYAO")])
    finally:
        restarted.close()


def test_quote_restriction_packet_trips_gateway_without_exposing_payload(gateway):
    connect(gateway)
    handle = gateway.create_alarm_quote_stream(["THYAO"], lambda *_: None)
    stream = handle._entry["stream"]
    stream._parse_packets = json.loads
    stream._on_message(
        None,
        json.dumps(
            [{"m": "protocol_error", "p": ["max sessions rate reached", "private-payload"]}]
        ),
    )
    assert not gateway.tradingview_enabled
    assert "private-payload" not in json.dumps(gateway.status())


def test_native_stream_budget_and_restriction_callbacks():
    admissions, denied = [], []
    pool = NativeStreamPool(
        Transport,
        "fake-token",
        1,
        lambda _: None,
        before_request=lambda kind, **_: admissions.append(kind),
        on_restriction=denied.append,
    )
    try:
        pool.configure([("BIST", "THYAO", "1D")])
        assert admissions == ["connect", "chart"]
        stream = next(iter(pool._streams.values()))
        packet(stream, "protocol_error", ["max sessions rate reached"])
        assert denied == ["provider_rate_limited"] and not pool.connected
    finally:
        pool.close()


def test_native_history_budget_and_restriction_callbacks():
    wire = Wire()
    admissions, denied = [], []
    history = NativeIndicatorHistory(
        ws_factory=wire,
        before_request=lambda kind, **_: admissions.append(kind),
        on_restriction=denied.append,
    )
    try:
        history.get_history(
            "THYAO", exchange="BIST", timeframe="1D", bars=2, token="fake-token", epoch=1
        )
        assert admissions == ["connect", "chart"]
        history._on_message(history._generation, wire.sockets[0], _message("auth_error", []))
        assert denied == ["authentication_failed"]
        assert not history.status()["connected"]
    finally:
        history.close()
