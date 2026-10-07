"""Synthetic account, persistence, lease and auth-boundary regression tests."""

import json
import logging
import threading
import time
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.auth import User, get_current_admin_user
from api.routes import borsapy_connection_routes as routes
from application.services.borsapy_gateway import BorsapyGateway, BorsapyGatewayError

SESSION = "private-session-fixture-0123456789"
SIGN = "private-signature-fixture-0123456789"
TOKEN = "private-auth-fixture-0123456789"


class FakeStream:
    instances = []

    def __init__(self, auth_token):
        self.token = auth_token
        self._connected = threading.Event()
        self._lock = threading.RLock()
        self._chart_data = {}
        self.closed = False
        self.quote_callback = self.candle_callback = None
        self.quote = {"last": 100, "timestamp": 1710000000, "_raw": {"token": TOKEN}}
        self.instances.append(self)

    @property
    def is_connected(self):
        return self._connected.is_set()

    def on_quote(self, symbol, callback):
        self.quote_callback = callback

    def on_any_quote(self, callback):
        self.quote_callback = callback

    def unsubscribe(self, symbol, exchange="BIST"):
        self.unsubscribed = (symbol, exchange)

    def on_candle(self, symbol, interval, callback):
        self.candle_callback = callback

    def connect(self, timeout):
        self._connected.set()

    def subscribe(self, symbol, exchange="BIST"):
        self.exchange = exchange
        self.quote_callback(symbol, self.quote)

    def subscribe_chart(self, symbol, interval, exchange="BIST"):
        self.subscription = (symbol, interval)

    def add_study(self, symbol, interval, study, **inputs):
        self.study = study
        self.inputs = inputs

    def get_quote(self, symbol):
        return self.quote

    def get_candles(self, symbol, interval, count):
        return [
            {"time": 1710000000, "open": 100, "high": 103, "low": 98, "close": 101, "volume": 8}
        ]

    def get_study(self, *args):
        return {"value": 42, "bad": float("nan")}

    def disconnect(self):
        self.closed = True
        self._connected.clear()


class FakeBorsapy:
    TradingViewStream = FakeStream

    def __init__(self):
        self.auth = None
        self.auth_calls = 0
        self.fail_auth = False
        self.empty_token = False
        self.history_calls = 0
        self.frame = pd.DataFrame(
            {
                "Open": [100, 101],
                "High": [103, 104],
                "Low": [98, 99],
                "Close": [101, 102],
                "Volume": [8, 9],
            },
            index=pd.date_range("2026-01-01", periods=2, tz="Europe/Istanbul"),
        )

    def set_tradingview_auth(self, session, session_sign):
        self.auth_calls += 1
        logging.getLogger("httpx").info("POST https://upstream.test/%s/%s", session, session_sign)
        if self.fail_auth:
            raise ValueError(f"provider included {session} {session_sign}")
        self.auth = {"auth_token": None if self.empty_token else TOKEN}
        return self.auth

    def get_tradingview_auth(self):
        return self.auth

    def clear_tradingview_auth(self):
        self.auth = None

    def set_evds_key(self, key):
        self.evds_key = key

    def clear_evds_key(self):
        self.evds_key = None

    def set_twitter_auth(self, **kwargs):
        self.twitter = kwargs

    def clear_twitter_auth(self):
        self.twitter = None

    def Ticker(self, symbol):
        return self

    def history(self, **kwargs):
        self.history_calls += 1
        return self.frame


@pytest.fixture
def gateway(tmp_path):
    settings = SimpleNamespace(
        borsapy_credentials_path=str(tmp_path / ".borsapy/credentials.enc"),
        jwt_secret_key="synthetic-signing-key-with-more-than-32-characters",
        database_path=str(tmp_path / "main.sqlite3"),
        borsapy_max_streams=2,
        borsapy_stream_idle_seconds=120,
    )
    bp = FakeBorsapy()
    clock = [0.0]
    item = BorsapyGateway(
        settings, loader=lambda: bp, version_reader=lambda: "0.11.0", clock=lambda: clock[0]
    )
    item.fake, item.clock = bp, clock
    yield item
    item.close()


def connect(gateway):
    return gateway.configure({"session": SESSION, "session_sign": SIGN})


def test_write_only_encryption_survives_restart_and_wrong_key_fails(gateway):
    assert gateway.status()["configured"] is False
    assert gateway.fake.auth_calls == 0
    assert connect(gateway)["authenticated"] is True
    ciphertext = gateway._store.path.read_bytes()
    assert SESSION.encode() not in ciphertext and SIGN.encode() not in ciphertext
    reloaded = BorsapyGateway(
        gateway.settings, loader=lambda: gateway.fake, version_reader=lambda: "0.11.0"
    )
    assert reloaded.status()["configured"] and not reloaded.status()["authenticated"]
    assert gateway.fake.auth_calls == 1  # status/restart perform no provider call
    assert SESSION not in json.dumps(reloaded.status())
    gateway.settings.jwt_secret_key = "another-synthetic-signing-key-more-than-32-characters"
    wrong = BorsapyGateway(gateway.settings, version_reader=lambda: "0.11.0")
    assert wrong.status()["state"] == "storage_error"


def test_token_missing_does_not_fall_back_or_retry_automatically(gateway):
    gateway.fake.empty_token = True
    with pytest.raises(BorsapyGatewayError, match="doğrulanamadı"):
        connect(gateway)
    assert gateway.fake.get_tradingview_auth() is None
    assert gateway.status()["configured"] and not gateway.status()["authenticated"]
    with pytest.raises(BorsapyGatewayError):
        gateway.history("THYAO")
    with pytest.raises(BorsapyGatewayError):
        gateway.run(lambda bp: 1)
    assert gateway.fake.auth_calls == 1
    gateway.fake.empty_token = False
    assert gateway.verify()["authenticated"]
    assert gateway.fake.auth_calls == 2


def test_running_process_reloads_replaced_and_deleted_credentials(gateway):
    other_bp = FakeBorsapy()
    other = BorsapyGateway(
        gateway.settings, loader=lambda: other_bp, version_reader=lambda: "0.11.0"
    )
    try:
        connect(gateway)
        other.history("THYAO")
        other.stream_snapshot("THYAO")
        old_stream = next(iter(other._streams.values()))["stream"]
        assert other_bp.auth_calls == 1
        replacement = SESSION + "-renewed"
        gateway.configure({"session": replacement, "session_sign": SIGN})
        other.history("THYAO")
        assert other_bp.auth_calls == 2 and other._credentials["session"] == replacement
        assert old_stream.closed and not other._streams
        other.history("THYAO")
        assert other_bp.auth_calls == 2
        gateway.clear()
        with pytest.raises(BorsapyGatewayError, match="kaydedin"):
            other.history("THYAO")
        assert other_bp.auth is None and not other.status()["configured"]
    finally:
        other.close()


def test_failed_revision_retries_only_after_external_replacement(gateway):
    other_bp = FakeBorsapy()
    other = BorsapyGateway(
        gateway.settings, loader=lambda: other_bp, version_reader=lambda: "0.11.0"
    )
    try:
        connect(gateway)
        other_bp.fail_auth = True
        for _ in range(2):
            with pytest.raises(BorsapyGatewayError, match="doğrulanamadı"):
                other.history("THYAO")
        assert other_bp.auth_calls == 1
        gateway.configure({"session": SESSION + "-renewed", "session_sign": SIGN})
        other_bp.fail_auth = False
        other.history("THYAO")
        assert other_bp.auth_calls == 2 and other.status()["authenticated"]
    finally:
        other.close()


def test_non_tradingview_queries_use_aux_keys_without_retrying_failed_tv_auth(gateway):
    gateway.fake.fail_auth = True
    with pytest.raises(BorsapyGatewayError):
        gateway.configure({"session": SESSION, "session_sign": SIGN, "evds_key": "evds-test"})
    assert gateway.run(lambda bp: bp.evds_key, tradingview=False) == "evds-test"
    assert gateway.fake.auth_calls == 1
    assert gateway.status()["state"] == "auth_needed"
    with pytest.raises(BorsapyGatewayError):
        gateway.run(lambda bp: "must not run")
    with pytest.raises(BorsapyGatewayError):
        gateway.run(lambda bp: "must not run", require_auth=True, tradingview=False)
    assert gateway.fake.auth_calls == 1
    # A replacement by the API is picked up before a non-TV query, without TV login.
    gateway._store.save({"session": SESSION, "session_sign": SIGN, "evds_key": "new-evds"})
    assert gateway.run(lambda bp: bp.evds_key, tradingview=False) == "new-evds"
    assert gateway.fake.auth_calls == 1


def test_corrupted_storage_blocks_all_sources_and_closes_old_streams(gateway):
    connect(gateway)
    gateway.stream_snapshot("THYAO")
    old_stream = next(iter(gateway._streams.values()))["stream"]
    gateway._store.path.write_bytes(b"corrupted-ciphertext")
    for use_tv in (True, False):
        with pytest.raises(BorsapyGatewayError, match="çözülemedi"):
            gateway.run(
                lambda bp: pytest.fail("Provider callback must stay blocked"), tradingview=use_tv
            )
    assert old_stream.closed and not gateway._streams
    assert gateway.fake.auth is None and not gateway.status()["authenticated"]
    assert gateway.status()["state"] == "storage_error"
    assert gateway.fake.auth_calls == 1


def test_secrets_never_reach_errors_status_or_upstream_logs(gateway, caplog):
    caplog.set_level(logging.INFO)
    gateway.fake.fail_auth = True
    with pytest.raises(BorsapyGatewayError) as caught:
        connect(gateway)
    outputs = str(caught.value) + caplog.text + json.dumps(gateway.status())
    assert SESSION not in outputs and SIGN not in outputs
    assert "[REDACTED]" in caplog.text
    try:
        raise ValueError(f"synthetic provider failed {SIGN}")
    except ValueError:
        logging.getLogger("borsapy.new_lazy_child").exception("Failure details")
    assert SIGN not in caplog.text
    assert "ValueError: synthetic provider failed [REDACTED]" in caplog.text


def test_history_requires_auth_rejects_silent_timeframe_fallback_and_bad_data(gateway):
    with pytest.raises(BorsapyGatewayError):
        gateway.history("THYAO")
    connect(gateway)
    for interval in ("3m", "45m", "bad"):
        with pytest.raises(BorsapyGatewayError):
            gateway.history("THYAO", interval)
    assert gateway.fake.history_calls == 0
    frame = gateway.history("THYAO.IS")
    assert str(frame.index.tz) == "Europe/Istanbul"
    assert frame.attrs["adjustment"] == "splits"
    gateway.fake.frame.loc[gateway.fake.frame.index[0], "High"] = 50
    with pytest.raises(BorsapyGatewayError, match="OHLCV"):
        gateway.history("THYAO")


def test_each_symbol_interval_study_has_an_isolated_bounded_stream(gateway):
    connect(gateway)
    first = gateway.stream_snapshot("THYAO", "1m", "RSI")
    second = gateway.stream_snapshot("GARAN", "1h")
    entries = list(gateway._streams.values())
    assert entries[0]["stream"] is not entries[1]["stream"]
    assert entries[0]["stream"].token == TOKEN
    assert first["realtime_verified"] is False
    assert first["study"] == {"value": 42.0, "bad": None}
    assert "_raw" not in first["quote"] and TOKEN not in json.dumps(first)
    assert second["received_at"] is not None
    with pytest.raises(BorsapyGatewayError, match="sınır"):
        gateway.stream_snapshot("ASELS", "1d")
    gateway.clock[0] = 121
    gateway._cleanup()
    assert not gateway._streams and all(e["stream"].closed for e in entries)


def test_disconnected_cache_is_rejected_and_retry_is_cooled_down(gateway):
    connect(gateway)
    gateway.stream_snapshot("THYAO")
    entry = next(iter(gateway._streams.values()))
    entry["stream"]._connected.clear()
    with pytest.raises(BorsapyGatewayError, match="kesildi"):
        gateway.stream_snapshot("THYAO")
    with pytest.raises(BorsapyGatewayError) as error:
        gateway.stream_snapshot("THYAO")
    assert error.value.status_code == 429
    gateway.clock[0] += 31
    assert gateway.stream_snapshot("THYAO")["state"] == "active_unverified"


def test_derivative_exchange_and_distinct_study_inputs_are_preserved(gateway):
    connect(gateway)
    gateway.stream_snapshot("VIOP:F_XU0301026", "1m", "RSI", {"length": 7})
    gateway.stream_snapshot("VIOP:F_XU0301026", "1m", "RSI", {"length": 14})
    streams = [entry["stream"] for entry in gateway._streams.values()]
    assert streams[0].exchange == "VIOP"
    assert streams[0].inputs == {"length": 7}
    assert streams[1].inputs == {"length": 14}
    with pytest.raises(BorsapyGatewayError):
        gateway.history("VIOP:F_XU0301026")
    with pytest.raises(BorsapyGatewayError):
        gateway.stream_snapshot("THYAO", "1m", "RSI", {"length": float("nan")})


def test_independent_subscriber_leases_survive_reconnect_and_scoped_stop(gateway):
    connect(gateway)
    gateway.stream_snapshot("THYAO", subscriber_id="tab-a")
    gateway.stream_snapshot("THYAO", subscriber_id="tab-b")
    gateway.stream_snapshot("GARAN", subscriber_id="other-chart")
    first, other = list(gateway._streams.values())
    first["stream"]._connected.clear()
    with pytest.raises(BorsapyGatewayError):
        gateway.stream_snapshot("THYAO", subscriber_id="tab-a")
    gateway.clock[0] += 31
    gateway.stream_snapshot("THYAO", subscriber_id="tab-a")
    renewed = list(gateway._streams.values())[0]
    assert renewed["stream"] is not first["stream"]
    assert set(renewed["subscribers"]) == {"tab-a", "tab-b"}
    assert not gateway.close_stream("THYAO", subscriber_id="tab-a")["closed"]
    assert not renewed["stream"].closed
    assert gateway.close_stream("THYAO", subscriber_id="tab-b")["closed"]
    assert renewed["stream"].closed and not other["stream"].closed


def test_stale_stream_is_labeled_and_history_rejects_missing_timestamp(gateway):
    connect(gateway)
    gateway.stream_snapshot("THYAO")
    next(iter(gateway._streams.values()))["received"] = 1
    assert gateway.stream_snapshot("THYAO")["state"] == "stale"
    gateway.fake.frame.index = pd.DatetimeIndex([pd.NaT, pd.Timestamp("2026-01-02", tz="UTC")])
    with pytest.raises(BorsapyGatewayError):
        gateway.history("THYAO")


def test_clear_deletes_credentials_closes_stream_and_erases_global_auth(gateway):
    connect(gateway)
    gateway.stream_snapshot("THYAO")
    entry = next(iter(gateway._streams.values()))
    result = gateway.clear()
    assert not result["configured"] and not result["authenticated"]
    assert not gateway._store.path.exists()
    assert gateway.fake.auth is None and entry["stream"].closed


def test_global_lock_serializes_provider_callbacks(gateway):
    connect(gateway)
    entered, release, second = threading.Event(), threading.Event(), threading.Event()

    def callback(bp):
        entered.set()
        assert release.wait(2)

    a = threading.Thread(target=lambda: gateway.run(callback))
    b = threading.Thread(target=lambda: gateway.run(lambda bp: second.set()))
    a.start()
    assert entered.wait(2)
    b.start()
    assert not second.wait(0.05)
    assert gateway.status()["authenticated"]  # status must not wait for the provider lock
    release.set()
    a.join(2)
    b.join(2)
    assert second.is_set()


def test_routes_require_admin_and_never_echo_invalid_credentials(gateway, monkeypatch):
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "get_borsapy_gateway", lambda: gateway)
    monkeypatch.setattr(routes.limiter, "enabled", False)
    with TestClient(app) as client:
        unauthorized = client.get("/borsapy/connection")
        assert unauthorized.status_code in (401, 403)
        assert unauthorized.headers["cache-control"] == "private, no-store"
        app.dependency_overrides[get_current_admin_user] = lambda: User(
            username="admin", role="admin"
        )
        result = client.post("/borsapy/connection", json={"session": SESSION})
        assert result.status_code == 422 and SESSION not in result.text
        result = client.post(
            "/borsapy/connection", json={"session": [SESSION], "session_sign": SIGN}
        )
        assert result.status_code == 422 and SESSION not in result.text
        result = client.post("/borsapy/connection", json={"session": SESSION, "session_sign": SIGN})
        assert result.status_code == 200
        assert SESSION not in result.text and SIGN not in result.text
        assert client.get("/borsapy/connection").json()["authenticated"]
        assert client.get("/borsapy/connection").headers["cache-control"] == "private, no-store"
        assert client.delete("/borsapy/connection").json()["configured"] is False


def test_real_upstream_protocol_isolated_charts_corrections_and_bounds(gateway, monkeypatch):
    from borsapy.stream import TradingViewStream

    class Socket:
        def send(self, message):
            pass

        def close(self):
            pass

    def offline_connect(stream, timeout):
        stream._ws = Socket()
        stream._on_open(stream._ws)
        return True

    monkeypatch.setattr(TradingViewStream, "connect", offline_connect)
    gateway.fake.TradingViewStream = TradingViewStream
    connect(gateway)
    gateway.stream_snapshot("THYAO", "1m")
    gateway.stream_snapshot("GARAN", "1h")
    a, b = [entry["stream"] for entry in gateway._streams.values()]

    def candles(stream, values):
        packet = {
            "m": "timescale_update",
            "p": [stream._chart_session, {"$prices": {"s": [{"v": row} for row in values]}}],
        }
        stream._on_message(stream._ws, stream._format_packet(packet))

    candles(a, [[t, 100, 103, 98, 101, 8] for t in range(1000, 1401)])
    candles(b, [[5000, 200, 203, 198, 201, 9]])
    candles(a, [[1399, 100, 104, 98, 102, 10]])  # correction before the latest bar
    result_a = gateway.stream_snapshot("THYAO", "1m")
    result_b = gateway.stream_snapshot("GARAN", "1h")
    assert len(result_a["candles"]) == 300
    assert result_a["candles"][-2]["close"] == 102
    assert result_b["candles"][0]["close"] == 201
    assert result_b["candles"][0]["time"] == 5000
    packet = {
        "m": "qsd",
        "p": [
            a._quote_session,
            {"n": "BIST:THYAO", "s": "ok", "v": {"lp": 105, "lp_time": 1700000000, "volume": 15}},
        ],
    }
    a._on_message(a._ws, a._format_packet(packet))
    result_a = gateway.stream_snapshot("THYAO", "1m")
    assert result_a["quote"]["last"] == 105
    assert result_a["quote"]["timestamp"] == 1700000000
    assert result_a["realtime_verified"] is False
    error = {"m": "critical_error", "p": [SESSION]}
    a._on_message(a._ws, a._format_packet(error))
    with pytest.raises(BorsapyGatewayError):
        gateway.stream_snapshot("THYAO", "1m")
    assert gateway.status()["authenticated"] is False
    assert gateway.status()["state"] == "auth_needed"


def test_shared_quote_pool_auth_timestamps_reuse_and_account_clear(gateway):
    with pytest.raises(BorsapyGatewayError):
        gateway.quote_snapshot([("BIST", "THYAO")])
    connect(gateway)
    first = gateway.quote_snapshot([("BIST", "THYAO"), ("BIST", "GARAN")])
    stream = gateway._quotes["stream"]
    again = gateway.quote_snapshot([("BIST", "THYAO")])
    assert gateway._quotes["stream"] is stream
    assert first["BIST:THYAO"]["received_at"] == again["BIST:THYAO"]["received_at"]
    assert first["BIST:THYAO"]["provider_time"] != first["BIST:THYAO"]["received_at"]
    assert first["BIST:THYAO"]["realtime_verified"] is False
    assert TOKEN not in json.dumps(first)
    epoch = gateway.data_epoch()
    gateway.clear()
    assert stream.closed and gateway._quotes is None
    assert gateway.data_epoch() > epoch


def test_quote_pool_expiry_capacity_and_instrument_collision(gateway):
    connect(gateway)
    for start in range(0, 200, 50):
        gateway.quote_snapshot([("BIST", "A" + str(i)) for i in range(start, start + 50)])
    with pytest.raises(BorsapyGatewayError, match="200"):
        gateway.quote_snapshot([("BIST", "EXTRA")])
    with pytest.raises(BorsapyGatewayError, match="borsada"):
        gateway.quote_snapshot([("NASDAQ", "A0")])
    old = gateway._quotes["stream"]
    gateway.clock[0] += 121
    gateway.quote_snapshot([("BIST", "EXTRA")])
    assert old.closed
    assert len(gateway._quotes["symbols"]) == 1


def test_quote_pool_reconnect_backoff_and_bad_price_are_explicit(gateway):
    connect(gateway)
    gateway.quote_snapshot([("BIST", "THYAO")])
    stream = gateway._quotes["stream"]
    stream.quote = {"last": float("nan"), "timestamp": 99999999999999}
    result = gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]
    assert result["state"] == "waiting" and result["price"] is None
    assert result["provider_time"] is None
    stream._connected.clear()
    with pytest.raises(BorsapyGatewayError):
        gateway.quote_snapshot([("BIST", "THYAO")])
    gateway.clock[0] += 31
    gateway.quote_snapshot([("BIST", "THYAO")])
    assert gateway._quotes["stream"] is not stream


def test_quote_freshness_requires_provider_timestamp_not_just_new_metadata(gateway):
    connect(gateway)
    gateway.quote_snapshot([("BIST", "THYAO")])
    entry = gateway._quotes
    entry["received"]["THYAO"] = time.time()
    for stamp in [None, time.time() - 1000, time.time() + 1000]:
        entry["stream"].quote = {"last": 100, "timestamp": stamp}
        assert gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]["state"] == "stale"
    entry["stream"].quote = {"last": 100, "timestamp": time.time()}
    assert gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]["state"] == "ok"


def test_existing_quotes_read_during_history_lock_but_new_subscriptions_wait(gateway, monkeypatch):
    from application.services.borsapy_gateway import _AUTH_LOCK

    connect(gateway)
    gateway.quote_snapshot([("BIST", "THYAO")])
    entered, release = threading.Event(), threading.Event()

    def history():
        with _AUTH_LOCK:
            entered.set()
            release.wait(5)

    thread = threading.Thread(target=history)
    thread.start()
    try:
        assert entered.wait(2)
        assert gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]["price"] == 100
        with pytest.raises(BorsapyGatewayError) as result:
            gateway.quote_snapshot([("BIST", "GARAN")])
        assert result.value.status_code == 429
        assert "GARAN" not in gateway._quotes["symbols"]
        original = gateway._read_quotes

        def removed(entry, pairs):
            result = original(entry, pairs)
            entry["symbols"].pop("THYAO")
            return result

        monkeypatch.setattr(gateway, "_read_quotes", removed)
        with pytest.raises(BorsapyGatewayError):
            gateway.quote_snapshot([("BIST", "THYAO")])
        assert "THYAO" not in gateway._quotes["symbols"]
    finally:
        release.set()
        thread.join(2)


def test_public_calendar_callback_does_not_hold_account_lock(gateway):
    connect(gateway)
    entered, release = threading.Event(), threading.Event()

    def calendar(bp):
        entered.set()
        release.wait(3)

    thread = threading.Thread(target=lambda: gateway.run_public(calendar))
    thread.start()
    try:
        assert entered.wait(2)
        assert gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]["price"] == 100
    finally:
        release.set()
        thread.join(2)


def test_real_ticker_public_actions_never_use_tv_and_allow_quotes_during_slow_io(
    gateway, monkeypatch
):
    import borsapy.ticker as ticker_module

    from application.services.borsapy_research import run_operation

    connect(gateway)
    entered, release = threading.Event(), threading.Event()
    public_calls, results, errors = [], [], []

    class NoTradingViewAccess:
        def __getattr__(self, name):
            pytest.fail(f"Company actions must not use TradingView: {name}")

    class PublicProvider:
        def get_dividends(self, symbol):
            public_calls.append(("dividends", symbol))
            entered.set()
            assert release.wait(5)
            return pd.DataFrame({"Amount": [0.25]}, index=pd.to_datetime(["2025-07-02"]))

        def get_capital_increases(self, symbol):
            public_calls.append(("splits", symbol))
            return pd.DataFrame(
                {"BonusFromCapital": [100.0], "BonusFromDividend": [0.0]},
                index=pd.to_datetime(["2024-11-27"]),
            )

    monkeypatch.setattr(ticker_module, "get_tradingview_provider", NoTradingViewAccess)
    monkeypatch.setattr(ticker_module.Ticker, "_get_isyatirim", lambda self: PublicProvider())
    monkeypatch.setattr(gateway.fake, "Ticker", ticker_module.Ticker)
    auth_calls = gateway.fake.auth_calls

    def slow_actions():
        try:
            results.append(
                gateway.run_public(
                    lambda bp: run_operation(bp, "company.actions", {"symbol": "EREGL"})
                )
            )
        except BaseException as error:
            errors.append(error)

    thread = threading.Thread(target=slow_actions)
    thread.start()
    try:
        assert entered.wait(2)
        # New symbol subscription needs the account lock; this is not merely a
        # cached fast read. It must succeed while the public provider is blocked.
        assert gateway.quote_snapshot([("BIST", "THYAO")])["BIST:THYAO"]["price"] == 100
        assert gateway.fake.auth_calls == auth_calls
    finally:
        release.set()
        thread.join(2)
    assert not thread.is_alive()
    assert not errors
    assert public_calls == [("dividends", "EREGL"), ("splits", "EREGL")]
    assert results[0]["source"] == "İş Yatırım"
    assert {table["name"] for table in results[0]["tables"]} == {"dividends", "splits", "actions"}


def test_existing_chart_survives_slow_history_and_new_requests_fail_bounded(gateway):
    from application.services.borsapy_gateway import _AUTH_LOCK

    connect(gateway)
    first = gateway.stream_snapshot("THYAO")
    entered, release = threading.Event(), threading.Event()

    def history():
        with _AUTH_LOCK:
            entered.set()
            release.wait(8)

    thread = threading.Thread(target=history)
    thread.start()
    try:
        assert entered.wait(2)
        assert gateway.stream_snapshot("THYAO")["candles"] == first["candles"]
        for request in (
            lambda: gateway.stream_snapshot("GARAN"),
            lambda: gateway.stream_snapshot("THYAO", subscriber_id="new-client"),
            lambda: gateway.run(lambda _: pytest.fail("Must not run behind busy provider")),
        ):
            with pytest.raises(BorsapyGatewayError) as result:
                request()
            assert result.value.status_code == 429
    finally:
        release.set()
        thread.join(2)


def test_chart_fast_read_rejects_generation_change_during_read(gateway, monkeypatch):
    from application.services.borsapy_gateway import _AUTH_LOCK

    connect(gateway)
    gateway.stream_snapshot("THYAO")
    original = gateway._read_stream

    def invalidated(*args):
        result = original(*args)
        gateway._data_epoch += 1
        return result

    monkeypatch.setattr(gateway, "_read_stream", invalidated)
    entered, release = threading.Event(), threading.Event()

    def history():
        with _AUTH_LOCK:
            entered.set()
            release.wait(4)

    thread = threading.Thread(target=history)
    thread.start()
    try:
        assert entered.wait(2)
        with pytest.raises(BorsapyGatewayError) as result:
            gateway.stream_snapshot("THYAO")
        assert result.value.status_code == 429
    finally:
        release.set()
        thread.join(2)


def test_real_quote_packets_ignore_late_other_exchange_and_clear_symbol_errors(
    gateway, monkeypatch
):
    from borsapy.stream import TradingViewStream

    class Socket:
        def send(self, message):
            pass

        def close(self):
            pass

    def offline_connect(stream, timeout):
        stream._ws = Socket()
        stream._on_open(stream._ws)
        return True

    monkeypatch.setattr(TradingViewStream, "connect", offline_connect)
    gateway.fake.TradingViewStream = TradingViewStream
    connect(gateway)
    gateway.quote_snapshot([("BIST", "ABC"), ("BIST", "KEEP")])
    stream = gateway._quotes["stream"]

    def packet(full, value=100, status="ok"):
        message = {
            "m": "qsd",
            "p": [
                stream._quote_session,
                {"n": full, "s": status, "v": {"lp": value, "lp_time": time.time()}},
            ],
        }
        stream._on_message(stream._ws, stream._format_packet(message))

    packet("BIST:ABC")
    packet("NASDAQ:ABC", 999)
    assert gateway.quote_snapshot([("BIST", "ABC")])["BIST:ABC"]["price"] == 100
    packet("BIST:ABC", status="error")
    assert gateway.quote_snapshot([("BIST", "ABC")])["BIST:ABC"]["state"] == "error"
    gateway.clock[0] += 121
    gateway._quotes["symbols"]["KEEP"] = ("BIST", gateway.clock[0])
    gateway.quote_snapshot([("NASDAQ", "ABC")])
    assert "ABC" not in gateway._quotes["errors"]
    packet("BIST:ABC", 888)
    packet("NASDAQ:ABC", 200)
    assert gateway.quote_snapshot([("NASDAQ", "ABC")])["NASDAQ:ABC"]["price"] == 200
