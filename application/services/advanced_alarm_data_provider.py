"""Native provider I/O behind an injectable boundary; no anonymous BIST fallback."""

from __future__ import annotations

from typing import Any

import pandas as pd

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


class NativeMarketProvider:
    def __init__(self, gateway=None):
        self.gateway = gateway or get_borsapy_gateway()

    def epoch(self) -> int:
        return self.gateway.data_epoch()

    def memory_epoch(self) -> int:
        return self.gateway.memory_epoch()

    def universe(self) -> list[str]:
        frame = self.gateway.run_public(lambda bp: bp.companies())
        return frame["ticker"].tolist()

    def open_quotes(self, symbols: list[str], callback):
        return self.gateway.create_alarm_quote_stream(symbols, callback)

    def reset_auth(self, epoch: int) -> None:
        self.gateway.reset_alarm_auth(epoch)

    def history(self, symbol: str, market_type: str, timeframe: str) -> pd.DataFrame:
        if market_type == "BIST":
            frame = self.gateway.history(symbol, interval=timeframe, period=PERIODS[timeframe])
        else:
            # Binance is explicit: borsapy/BtcTurk is never a crypto substitute.
            from binance.client import Client

            interval = {"1wk": "1w", "1mo": "1M"}.get(timeframe, timeframe)
            client = Client(ping=False, requests_params={"timeout": (3.05, 10)})
            try:
                raw = client.get_klines(symbol=symbol, interval=interval, limit=500)
            finally:
                client.close_connection()
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
        from binance.client import Client

        client = Client(ping=False, requests_params={"timeout": (3.05, 10)})
        try:
            # One bounded batch; closeTime is a provider timestamp, not polling time.
            raw = client.get_ticker(symbols=symbols)
        finally:
            client.close_connection()
        return {
            item["symbol"]: {
                "price": float(item["lastPrice"]),
                "source_timestamp": float(item["closeTime"]) / 1000,
            }
            for item in raw
            if item.get("symbol") in symbols
        }
