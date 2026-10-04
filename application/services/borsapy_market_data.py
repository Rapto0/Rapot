"""Personal market read model shared by dashboard, watchlists and scan results.

Quotes use one leased TradingView connection. Performance history is loaded by a
bounded single worker, never by an unbounded fan-out of HTTP request threads.
Nothing in this module writes the public price cache or persists account prices.
"""

from __future__ import annotations

import math
import queue
import re
import threading
import time
from collections import OrderedDict
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from application.services.borsapy_gateway import BorsapyGatewayError

# Explicit instrument identity: never substitute a futures contract for spot,
# or BtcTurk for a Binance pair. All vendor targets are from this allowlist.
_ALIASES = {
    "XU100.IS": ("BIST", "XU100", "BIST 100"),
    "^GSPC": ("SP", "SPX", "S&P 500"),
    "^NDX": ("NASDAQ", "NDX", "Nasdaq 100"),
    "^VIX": ("CBOE", "VIX", "VIX"),
    "DX-Y.NYB": ("TVC", "DXY", "Dolar endeksi"),
    "TRY=X": ("FX", "USDTRY", "USD/TRY"),
    "XAUUSD=X": ("OANDA", "XAUUSD", "Altın / USD"),
    "XAGUSD=X": ("OANDA", "XAGUSD", "Gümüş / USD"),
    "WTI": ("TVC", "USOIL", "WTI referans fiyatı"),
    **{symbol: ("NASDAQ", symbol, symbol) for symbol in ("NVDA", "AAPL", "TSLA", "GOOGL")},
}
_MESSAGES = {
    "ok": "Fiyat akışı alınıyor; gecikmesiz erişim henüz doğrulanmadı.",
    "waiting": "İlk fiyat bekleniyor.",
    "stale": "Son fiyat güncellemesi iki dakikadan eski; işlem saatini kontrol edin.",
    "error": "Veri alınamadı; yeniden denenecek.",
    "auth_required": "TradingView bağlantısını Bağlantılar bölümünden tamamlayın.",
    "unsupported": "Bu enstrüman için tanımlı Borsapy eşlemesi yok.",
}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _finite(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError, OverflowError):
        return None


def instrument(symbol: str) -> tuple[str, str, str] | None:
    if symbol in _ALIASES:
        return _ALIASES[symbol]
    if symbol.endswith(".IS") or symbol.startswith("BIST:"):
        name = symbol.removesuffix(".IS").removeprefix("BIST:")
        if re.fullmatch(r"[A-Z0-9]{1,20}", name):
            return "BIST", name, name
    return None


def _empty(symbol: str, state: str, message: str | None = None) -> dict:
    mapped = instrument(symbol)
    return {
        "symbol": symbol,
        "regularMarketPrice": None,
        "regularMarketChangePercent": None,
        "change": None,
        "shortName": mapped[2] if mapped else symbol,
        "source": "borsapy_tradingview" if mapped else None,
        "provider_time": None,
        "received_at": None,
        "state": state,
        "message": message or _MESSAGES[state],
        "realtime_verified": False,
    }


def performance_anchors(frame: pd.DataFrame) -> dict:
    """Calendar-day return anchors, no future prices and no invented zero return."""
    closes = frame.Close.sort_index()
    if closes.empty:
        raise ValueError("No history")
    if (
        closes.index.has_duplicates
        or closes.index.hasnans
        or any(_finite(value) is None or value <= 0 for value in closes)
    ):
        raise ValueError("Invalid history prices")
    latest = pd.Timestamp(closes.index[-1])
    if latest.tzinfo is None or latest > pd.Timestamp.now(tz="UTC") + pd.Timedelta(days=1):
        raise ValueError("Invalid history time")
    result: dict = {
        "history_time": latest.isoformat(),
        "history_received_at": _now(),
        "closes": [(pd.Timestamp(t).isoformat(), float(v)) for t, v in closes.tail(100).items()],
        "history": [
            {"time": pd.Timestamp(t).isoformat(), "value": float(v)}
            for t, v in closes.tail(30).items()
        ],
    }
    for days in (7, 30):
        earlier = closes[closes.index <= latest - pd.Timedelta(days=days)]
        value = _finite(earlier.iloc[-1]) if len(earlier) else None
        result[f"anchor_{days}"] = value if value is not None and value > 0 else None
    return result


def quote_performance(price: float | None, as_of: str | None, history: dict) -> dict:
    """Select each prior close relative to the quote's date, never a stale history end."""
    result = {"perf_7d": None, "perf_30d": None, "performance_as_of": as_of}
    if _finite(price) is None or price <= 0 or not as_of:
        return result
    try:
        stamp = pd.Timestamp(as_of)
        if stamp.tzinfo is None:
            return result
        values = [(pd.Timestamp(t), v) for t, v in history.get("closes", [])]
        if not values or any(t.tzinfo is None or _finite(v) is None or v <= 0 for t, v in values):
            return result
        stamp = stamp.tz_convert(values[0][0].tzinfo)
        for days in (7, 30):
            cutoff = stamp.normalize() - pd.Timedelta(days=days)
            eligible = [(t, v) for t, v in values if t.normalize() <= cutoff]
            if eligible:
                base_time, base = eligible[-1]
                # Missing whole weeks must not masquerade as a 7-day return.
                if cutoff - base_time.normalize() <= pd.Timedelta(days=7):
                    value = (price / base - 1) * 100
                    result[f"perf_{days}d"] = _finite(value)
    except (ValueError, TypeError, OverflowError, ZeroDivisionError):
        return result
    return result


class BorsapyMarketData:
    def __init__(self, gateway=None, *, clock=None):
        self._gateway = gateway
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._jobs: queue.Queue = queue.Queue(maxsize=100)
        self._pending: set[tuple] = set()
        self._history: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def gateway(self):
        from application.services.borsapy_gateway import get_borsapy_gateway

        return self._gateway or get_borsapy_gateway()

    def quotes(self, symbols: list[str]) -> list[dict]:
        if not symbols or len(symbols) > 50:
            raise BorsapyGatewayError("Bir istekte 1–50 sembol gerekir.", 422)
        symbols = list(dict.fromkeys(value.strip().upper() for value in symbols))
        result = [
            _empty(symbol, "waiting" if instrument(symbol) else "unsupported") for symbol in symbols
        ]
        pairs = list(
            dict.fromkeys(instrument(symbol)[:2] for symbol in symbols if instrument(symbol))
        )
        if not pairs:
            return result
        try:
            quotes = self.gateway.quote_snapshot(pairs)
        except BorsapyGatewayError as exc:
            # An unauthenticated Rapot request never reaches this service. This
            # describes vendor connection state while keeping other page data usable.
            state = "auth_required" if exc.status_code == 409 else "error"
            return [
                _empty(symbol, state, str(exc))
                if instrument(symbol)
                else _empty(symbol, "unsupported")
                for symbol in symbols
            ]
        for item in result:
            target = instrument(item["symbol"])
            if not target:
                continue
            raw = quotes.get(f"{target[0]}:{target[1]}")
            if raw:
                item.update(
                    {
                        key: raw[key]
                        for key in (
                            "state",
                            "source",
                            "provider_time",
                            "received_at",
                            "realtime_verified",
                        )
                    }
                )
                item.update(
                    regularMarketPrice=raw["price"],
                    regularMarketChangePercent=raw["change_pct"],
                    change=raw["change"],
                    message=_MESSAGES.get(raw["state"], _MESSAGES["error"]),
                )
        return result

    def _history_for(self, symbol: str, epoch: int, market: str = "BIST") -> dict:
        key = (epoch, symbol, market)
        with self._lock:
            cached = self._history.get(key)
            if cached and self._clock() - cached[0] < (
                300 if cached[1]["history_state"] == "ok" else 60
            ):
                self._history.move_to_end(key)
                return dict(cached[1])
            if key not in self._pending and not self._stop.is_set():
                try:
                    self._jobs.put_nowait(key)
                    self._pending.add(key)
                    if not self._worker or not self._worker.is_alive():
                        self._worker = threading.Thread(
                            target=self._work, daemon=True, name="market-history"
                        )
                        self._worker.start()
                except queue.Full:
                    pass
        return {"history_state": "waiting", "history_time": None, "history_received_at": None}

    def _work(self) -> None:
        while not self._stop.is_set():
            try:
                key = self._jobs.get(timeout=1)
            except queue.Empty:
                continue
            epoch, symbol, market = key
            payload = None
            try:
                if market == "BIST" and self.gateway.data_epoch() != epoch:
                    payload = None
                    continue
                if market == "BIST":
                    frame = self.gateway.history(symbol, interval="1d", period="3mo")
                else:
                    from data_loader import get_crypto_data

                    frame = get_crypto_data(symbol, start_str="3 months ago")
                    if frame is None or frame.empty:
                        raise ValueError("No crypto history")
                    frame = frame.copy()
                    if frame.index.tz is None:
                        frame.index = frame.index.tz_localize("UTC")
                payload = {**performance_anchors(frame), "history_state": "ok"}
                if market == "BIST" and self.gateway.data_epoch() != epoch:
                    payload = None
                    continue
            except Exception:
                # Never persist raw provider errors or response bodies.
                payload = {
                    "history_state": "error",
                    "history_time": None,
                    "history_received_at": None,
                }
            finally:
                with self._lock:
                    if payload is not None and not self._stop.is_set():
                        self._history[key] = (self._clock(), payload)
                        self._history.move_to_end(key)
                        while len(self._history) > 200:
                            self._history.popitem(last=False)
                    self._pending.discard(key)
                self._jobs.task_done()

    def metrics(self, keys: list[str]) -> dict[str, dict]:
        if not 1 <= len(keys) <= 50:
            raise BorsapyGatewayError("Bir istekte 1–50 metrik gerekir.", 422)
        keys = list(dict.fromkeys(keys))
        if any(not re.fullmatch(r"BIST:[A-Z0-9]{1,20}(?:\.IS)?", key) for key in keys):
            raise BorsapyGatewayError("Bu metrik servisi BIST sembollerini kabul eder.", 422)
        mapping = {key: key.split(":", 1)[1].removesuffix(".IS") + ".IS" for key in keys}
        quotes = {item["symbol"]: item for item in self.quotes(list(mapping.values()))}
        result = {}
        epoch = self.gateway.data_epoch()
        for key, symbol in mapping.items():
            quote = quotes[symbol]
            value = quote["regularMarketPrice"]
            history = (
                self._history_for(symbol.removesuffix(".IS"), epoch)
                if quote["state"] in {"ok", "stale", "waiting"}
                else {"history_state": "waiting", "history_time": None, "history_received_at": None}
            )
            payload = {
                name: quote[name]
                for name in (
                    "source",
                    "provider_time",
                    "received_at",
                    "state",
                    "message",
                    "realtime_verified",
                )
            }
            payload.update(
                latest_price=value,
                change_pct=quote["regularMarketChangePercent"],
                perf_7d=None,
                perf_30d=None,
                history_state=history["history_state"],
                history_time=history["history_time"],
                history_received_at=history["history_received_at"],
                adjustment="splits",
            )
            payload.update(quote_performance(value, quote["provider_time"], history))
            result[key] = payload
        return result

    def crypto_metrics(self, keys: list[str]) -> dict[str, dict]:
        """Explicit Binance instrument path, using the already shared ticker feed."""
        from websocket_manager import ws_manager

        if not 1 <= len(keys) <= 50 or any(
            not re.fullmatch(r"Kripto:[A-Z0-9]{2,20}USDT", key) for key in keys
        ):
            raise BorsapyGatewayError("1–50 Binance USDT sembolü gerekir.", 422)
        result = {}
        for key in dict.fromkeys(keys):
            symbol = key.split(":", 1)[1]
            quote = ws_manager.get_ticker(symbol) or {}
            price = _finite(quote.get("price"))
            price = price if price and price > 0 else None
            stamp = quote.get("timestamp")
            # Existing Binance runtime emits host-local receipt timestamps. Convert
            # with the host's timezone, never label them as exchange timestamps.
            try:
                received = datetime.fromisoformat(stamp).astimezone(UTC)
                age = (datetime.now(UTC) - received).total_seconds()
                received_at = received.isoformat()
                if age < -300:
                    received_at, age = None, None
            except (TypeError, ValueError):
                received_at, age = None, None
            state = "waiting" if price is None else "stale" if age is None or age > 120 else "ok"
            history = self._history_for(symbol, 0, "Kripto") if price is not None else {}
            payload = {
                "latest_price": price,
                "change_pct": _finite(quote.get("priceChangePercent")),
                "perf_7d": None,
                "perf_30d": None,
                "source": "binance",
                "provider_time": None,
                "received_at": received_at,
                "state": state,
                "realtime_verified": False,
                "message": "Binance fiyat akışı.",
                "history_state": history.get("history_state", "waiting"),
                "history_time": history.get("history_time"),
                "history_received_at": history.get("history_received_at"),
            }
            payload.update(quote_performance(price, received_at, history))
            result[key] = payload
        return result

    def overview(self) -> dict:
        quote = self.quotes(["XU100.IS"])[0]
        history = (
            self._history_for("XU100", self.gateway.data_epoch())
            if quote["state"] in {"ok", "stale", "waiting"}
            else {}
        )
        crypto = self.crypto_metrics(["Kripto:BTCUSDT"])["Kripto:BTCUSDT"]
        crypto_history = (
            self._history_for("BTCUSDT", 0, "Kripto") if crypto["latest_price"] is not None else {}
        )
        return {
            "bist": {
                **quote,
                "currentValue": quote["regularMarketPrice"],
                "change": quote["regularMarketChangePercent"],
                "history": history.get("history", []),
                "history_interval": "1d",
                "history_state": history.get("history_state", "waiting"),
            },
            "crypto": {
                **crypto,
                "currentValue": crypto["latest_price"],
                "change": crypto["change_pct"],
                "history": crypto_history.get("history", []),
                "history_interval": "1d",
            },
        }

    def candles(self, symbol: str, interval: str, limit: int = 1000) -> dict:
        from application.services.borsapy_gateway import INTERVALS
        from data_loader import resample_bist_data

        grouped = {"2d", "3d", "4d", "5d", "6d", "2wk", "3wk", "2mo", "3mo"}
        if interval not in INTERVALS | grouped or not 1 <= limit <= 2000:
            raise BorsapyGatewayError("Desteklenmeyen BIST periyodu veya mum sayısı.", 422)
        period = {"1m": "5d", "5m": "1mo", "15m": "3mo", "30m": "6mo", "1h": "1y", "4h": "2y"}.get(
            interval, "10y"
        )
        frame = self.gateway.history(
            symbol, interval="1d" if interval in grouped else interval, period=period
        )
        if interval in grouped:
            frame = resample_bist_data(frame, interval)
            if frame is None or frame.empty:
                raise BorsapyGatewayError("Mumlar seçilen periyoda dönüştürülemedi.", 502)
            frame.index = frame.index.tz_localize("Europe/Istanbul")
        bars = [
            {
                "time": pd.Timestamp(t).isoformat(),
                "open": float(row.Open),
                "high": float(row.High),
                "low": float(row.Low),
                "close": float(row.Close),
                "volume": float(row.Volume),
            }
            for t, row in frame.tail(limit).iterrows()
        ]
        return {
            "symbol": symbol.upper().removesuffix(".IS"),
            "market_type": "BIST",
            "timeframe": interval,
            "source": "borsapy_tradingview",
            "count": len(bars),
            "candles": bars,
            "provider_time": bars[-1]["time"] if bars else None,
            "received_at": _now(),
            "state": "ok" if bars else "waiting",
            "realtime_verified": False,
            "adjustment": "splits",
            "open_quality": "provider",
            "message": "TradingView mumları; son mum henüz kapanmamış olabilir.",
        }

    def close(self) -> None:
        self._stop.set()
        with self._lock:
            self._history.clear()
        if self._worker:
            self._worker.join(timeout=1)


_market = BorsapyMarketData()
_market_lock = threading.Lock()


def get_borsapy_market_data() -> BorsapyMarketData:
    global _market
    with _market_lock:
        if _market._stop.is_set():
            _market = BorsapyMarketData()
        return _market
