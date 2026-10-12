"""Public Binance sessions remain bounded, worker-owned and disposable after errors."""

import threading
from types import SimpleNamespace

import pytest

from application.services.advanced_alarm_data_provider import (
    MAX_PUBLIC_CLIENTS,
    NativeMarketProvider,
)


class PublicClient:
    def __init__(self, **params):
        assert params == {
            "api_key": None,
            "api_secret": None,
            "ping": False,
            "requests_params": {"timeout": (3.05, 10)},
        }
        self.owner = threading.current_thread()
        self.calls = []
        self.closed = 0
        self.failure = None

    def request(self, method, params):
        assert threading.current_thread() is self.owner
        assert not self.closed
        self.calls.append((method, params))
        if self.failure:
            raise self.failure

    def get_klines(self, **params):
        self.request("get_klines", params)
        return [[1760000000000, "10", "12", "9", "11", "0"]]

    def get_ticker(self, **params):
        self.request("get_ticker", params)
        return [
            {"symbol": "BTCUSDT", "lastPrice": "11", "closeTime": 1760000001234},
            {"symbol": "UNREQUESTED", "lastPrice": "99", "closeTime": 1760000001234},
        ]

    def close_connection(self):
        self.closed += 1


@pytest.fixture
def provider():
    clients = []

    def factory(**kwargs):
        client = PublicClient(**kwargs)
        clients.append(client)
        return client

    result = NativeMarketProvider(SimpleNamespace(), client_factory=factory)
    yield result, clients
    result.close()


def test_history_and_quotes_reuse_one_public_session_without_changing_native_data(provider):
    adapter, clients = provider
    assert not clients  # Construction has no Binance I/O or client/TLS setup.
    daily = adapter.history("BTCUSDT", "Kripto", "1d")
    weekly = adapter.history("BTCUSDT", "Kripto", "1wk")
    monthly = adapter.history("BTCUSDT", "Kripto", "1mo")
    quote = adapter.crypto_quotes(["BTCUSDT"])
    assert len(clients) == 1 and clients[0].closed == 0
    assert clients[0].calls == [
        ("get_klines", {"symbol": "BTCUSDT", "interval": "1d", "limit": 500}),
        ("get_klines", {"symbol": "BTCUSDT", "interval": "1w", "limit": 500}),
        ("get_klines", {"symbol": "BTCUSDT", "interval": "1M", "limit": 500}),
        ("get_ticker", {"symbols": ["BTCUSDT"]}),
    ]
    assert daily.index[0].timestamp() == 1760000000
    assert str(daily.index.tz) == "UTC"
    assert daily.iloc[0].to_dict() == {
        "Open": 10.0,
        "High": 12.0,
        "Low": 9.0,
        "Close": 11.0,
        "Volume": 0.0,
    }
    assert daily.attrs == {"source": "binance", "timeframe": "1d"}
    assert weekly.attrs["timeframe"] == "1wk"
    assert monthly.attrs["timeframe"] == "1mo"
    assert quote == {"BTCUSDT": {"price": 11.0, "source_timestamp": 1760000001.234}}


@pytest.mark.parametrize("method", ["history", "quotes"])
def test_failed_request_discards_only_its_client_and_next_request_can_recover(provider, method):
    adapter, clients = provider
    adapter.crypto_quotes(["BTCUSDT"])
    failure = TimeoutError("synthetic provider timeout")
    clients[0].failure = failure
    with pytest.raises(TimeoutError) as raised:
        if method == "history":
            adapter.history("BTCUSDT", "Kripto", "1m")
        else:
            adapter.crypto_quotes(["BTCUSDT"])
    assert raised.value is failure
    assert clients[0].closed == 1
    adapter.crypto_quotes(["BTCUSDT"])
    assert len(clients) == 2
    assert clients[1].closed == 0


def test_fixed_workers_have_separate_bounded_sessions_and_dead_workers_are_reaped(provider):
    adapter, clients = provider
    entered = threading.Barrier(MAX_PUBLIC_CLIENTS + 1, timeout=5)
    finish = threading.Event()
    failures = []

    def worker():
        try:
            for _ in range(3):
                adapter.crypto_quotes(["BTCUSDT"])
            entered.wait()
            assert finish.wait(5)
        except BaseException as exc:
            failures.append(exc)

    workers = [threading.Thread(target=worker) for _ in range(MAX_PUBLIC_CLIENTS)]
    for thread in workers:
        thread.start()
    try:
        entered.wait()
        assert len(clients) == MAX_PUBLIC_CLIENTS
        assert len({client.owner for client in clients}) == MAX_PUBLIC_CLIENTS
        assert all(len(client.calls) == 3 for client in clients)
        with pytest.raises(RuntimeError, match="kapasitesi"):
            adapter.crypto_quotes(["BTCUSDT"])
        assert len(clients) == MAX_PUBLIC_CLIENTS
    finally:
        finish.set()
        for thread in workers:
            thread.join(5)
    assert not failures and not any(thread.is_alive() for thread in workers)
    adapter.crypto_quotes(["BTCUSDT"])
    assert all(client.closed == 1 for client in clients[:-1])
    assert len(adapter._clients) == 1


def test_close_is_idempotent_and_later_worker_lifecycle_uses_new_session(provider):
    adapter, clients = provider
    adapter.crypto_quotes(["BTCUSDT"])
    adapter.close()
    adapter.close()
    assert clients[0].closed == 1
    assert not adapter._clients
    adapter.crypto_quotes(["BTCUSDT"])
    assert len(clients) == 2 and clients[1].closed == 0


def test_bist_gateway_failure_does_not_create_anonymous_binance_fallback(provider):
    adapter, clients = provider

    def fail(*args, **kwargs):
        raise ValueError("synthetic BIST failure")

    adapter.gateway.alarm_history = fail
    with pytest.raises(ValueError, match="synthetic BIST failure"):
        adapter.history("THYAO", "BIST", "1m")
    assert not clients
