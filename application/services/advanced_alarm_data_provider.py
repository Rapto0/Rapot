"""Native provider I/O behind an injectable boundary; no anonymous BIST fallback."""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import pandas as pd

from application.services.bist_share_universe import share_universe
from application.services.borsapy_gateway import get_borsapy_gateway

PERIODS = {
    "1m": "5d",
    "5m": "1mo",
    "15m": "3mo",
    "30m": "6mo",
    "1h": "6mo",
    "4h": "6mo",
    "1d": "2y",
    "1wk": "10y",
    "1mo": "max",
}
MAX_PUBLIC_CLIENTS = 5  # Four fixed history workers plus the quote/connection worker.


class NativeMarketProvider:
    def __init__(self, gateway=None, *, client_factory: Callable | None = None):
        self.gateway = gateway or get_borsapy_gateway()
        self._client_factory = client_factory
        self._clients: dict[threading.Thread, Any] = {}
        self._clients_lock = threading.Lock()
        self._share_universe = share_universe()
        self._share_symbols = frozenset(self._share_universe.symbols)

    @staticmethod
    def _close_client(client) -> None:
        # Shutdown must not mask the original provider error.
        with suppress(Exception):
            client.close_connection()

    def _public_client(self):
        """A requests session is owned by one fixed worker, never shared concurrently."""
        current = threading.current_thread()
        with self._clients_lock:
            for thread in list(self._clients):
                if not thread.is_alive():
                    self._close_client(self._clients.pop(thread))
            client = self._clients.get(current)
            if client is None:
                if len(self._clients) >= MAX_PUBLIC_CLIENTS:
                    raise RuntimeError("Piyasa veri worker kapasitesi aşıldı.")
                factory = self._client_factory
                if factory is None:
                    from binance.client import Client

                    factory = Client
                client = factory(
                    api_key=None,
                    api_secret=None,
                    ping=False,
                    requests_params={"timeout": (3.05, 10)},
                )
                self._clients[current] = client
            return client

    def _public_request(self, method: str, **params):
        client = self._public_client()
        try:
            return getattr(client, method)(**params)
        except Exception:
            with self._clients_lock:
                current = threading.current_thread()
                if self._clients.get(current) is client:
                    self._clients.pop(current)
            self._close_client(client)
            raise

    def close(self) -> None:
        """Release sessions after all workers join; a later start creates fresh sessions."""
        with self._clients_lock:
            clients = list(self._clients.values())
            self._clients.clear()
        for client in clients:
            self._close_client(client)

    def epoch(self) -> int:
        return self.gateway.data_epoch()

    def memory_epoch(self) -> int:
        return self.gateway.memory_epoch()

    def tradingview_paused(self) -> bool:
        return not self.gateway.tradingview_enabled

    def universe(self) -> list[str]:
        return list(self._share_universe.symbols)

    def filter_universe(self, symbols) -> list[str]:
        """Discard old issuer candidates only from the automatic universe cache."""
        return [
            symbol
            for symbol in symbols
            if isinstance(symbol, str) and symbol in self._share_symbols
        ]

    def universe_metadata(self) -> dict:
        return self._share_universe.metadata()

    def open_quotes(self, symbols: list[str], callback):
        return self.gateway.create_alarm_quote_stream(symbols, callback)

    def reset_auth(self, epoch: int) -> None:
        self.gateway.reset_alarm_auth(epoch)

    def history(self, symbol: str, market_type: str, timeframe: str) -> pd.DataFrame:
        if market_type == "BIST":
            frame = self.gateway.alarm_history(
                symbol, interval=timeframe, period=PERIODS[timeframe]
            )
        else:
            # Binance is explicit: borsapy/BtcTurk is never a crypto substitute.
            interval = {"1wk": "1w", "1mo": "1M"}.get(timeframe, timeframe)
            raw = self._public_request("get_klines", symbol=symbol, interval=interval, limit=500)
            frame = pd.DataFrame(
                [[row[1], row[2], row[3], row[4], row[5]] for row in raw],
                index=pd.to_datetime([row[0] for row in raw], unit="ms", utc=True),
                columns=["Open", "High", "Low", "Close", "Volume"],
                dtype=float,
            )
            frame.attrs["source"] = "binance"
        frame.attrs["timeframe"] = timeframe
        return frame

    def crypto_quotes(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        # One bounded batch; closeTime is a provider timestamp, not polling time.
        raw = self._public_request("get_ticker", symbols=symbols)
        return {
            item["symbol"]: {
                "price": float(item["lastPrice"]),
                "source_timestamp": float(item["closeTime"]) / 1000,
            }
            for item in raw
            if item.get("symbol") in symbols
        }
