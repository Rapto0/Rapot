"""Closed-candle server alarms, using the Python backend calculation contract.

Pine/TypeScript equivalence is not implied. Binance uses native UTC intervals;
BIST exposes only native Istanbul daily bars. Daily BIST bars close
conservatively at the next local midnight. There is no holiday calendar:
unexpected missing sessions become unavailable, never a delayed signal replay.
Intraday BIST requests are rejected until a verified session calendar exists.
"""

from __future__ import annotations

import asyncio
import math
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any, Protocol
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from ta.momentum import rsi, williams_r

from signals import calculate_combo_signal, calculate_hunter_signal

_ISTANBUL = ZoneInfo("Europe/Istanbul")
_OHLCV = ["Open", "High", "Low", "Close", "Volume"]
_DURATIONS = {"1h": pd.Timedelta(hours=1), "4h": pd.Timedelta(hours=4), "1d": pd.Timedelta(days=1)}
_INDICATOR_FIELDS = {
    "combo": ["MACD", "RSI", "WR", "CCI"],
    "hunter": [
        "RSI",
        "RSI_Fast",
        "CMO",
        "BOP",
        "MACD",
        "W%R",
        "CCI",
        "ULT",
        "BBP",
        "ROC",
        "DeM",
        "PSY",
        "ZScore",
        "KeltPB",
        "RSI2",
    ],
}


class AlarmEvaluationError(ValueError):
    """A safe, user-visible evaluation failure, with no provider response text."""


class AlarmDataProvider(Protocol):
    def fetch_bars(self, *, symbol: str, market_type: str, timeframe: str) -> pd.DataFrame:
        """Return OHLCV indexed by timezone-aware bar opens, with timeframe metadata."""
        ...


class PublicAlarmDataProvider:
    """Bounded public-data calls; no exchange account or order API is used."""

    def fetch_bars(self, *, symbol: str, market_type: str, timeframe: str) -> pd.DataFrame:
        if market_type == "Kripto":
            from binance.client import Client

            client = Client(ping=False, requests_params={"timeout": (3.05, 10)})
            try:
                rows = client.get_klines(symbol=symbol, interval=timeframe, limit=301)
            finally:
                client.close_connection()
            if not rows:
                raise AlarmEvaluationError("Sağlayıcı mum verisi döndürmedi.")
            frame = pd.DataFrame(rows)
            if len(frame.columns) != 12:
                raise AlarmEvaluationError("Sağlayıcı mum biçimi geçersiz.")
            index = pd.to_datetime(frame.iloc[:, 0], unit="ms", utc=True)
            # Explicit Binance close timestamps detect an accidental wrong interval.
            ends = pd.to_datetime(frame.iloc[:, 6], unit="ms", utc=True)
            if not ((ends - index) == _DURATIONS[timeframe] - pd.Timedelta(milliseconds=1)).all():
                raise AlarmEvaluationError("Sağlayıcı mum periyodu istenen periyotla uyuşmuyor.")
            frame = frame.iloc[:, 1:6].copy()
            frame.columns = _OHLCV
            frame.index = pd.DatetimeIndex(index)
            frame.attrs["source"] = "binance"
        else:
            import yfinance as yf

            ticker = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
            frame = yf.Ticker(ticker).history(
                period="2y" if timeframe == "1d" else "60d",
                interval=timeframe,
                auto_adjust=False,
                actions=False,
                timeout=10,
                raise_errors=True,
            )
            if frame is None or frame.empty:
                raise AlarmEvaluationError("Sağlayıcı mum verisi döndürmedi.")
            frame = frame.copy()
            frame.attrs["source"] = "yfinance_bist"
        frame.attrs["timeframe"] = timeframe
        return frame.tail(301).copy()


def _validate_request(
    symbol: str, market_type: str, timeframe: str, indicator: str, side: str, threshold: float
) -> None:
    if market_type not in {"BIST", "Kripto"} or timeframe not in _DURATIONS:
        raise AlarmEvaluationError("Piyasa veya periyot desteklenmiyor.")
    if market_type == "BIST" and timeframe != "1d":
        raise AlarmEvaluationError("BIST sunucu alarmları yalnız 1d periyodunu destekler.")
    pattern = r"[A-Z0-9]{2,20}USDT" if market_type == "Kripto" else r"[A-Z0-9]{1,20}(?:\.IS)?"
    if not isinstance(symbol, str) or not re.fullmatch(pattern, symbol):
        raise AlarmEvaluationError("Alarm sembolü geçersiz; kriptoda USDT çifti kullanın.")
    if indicator not in {"rsi", "wr", "combo", "hunter"} or side not in {"dip", "top"}:
        raise AlarmEvaluationError("Gösterge veya koşul desteklenmiyor.")
    if not isinstance(threshold, (int, float)) or not math.isfinite(threshold):
        raise AlarmEvaluationError("Alarm eşiği sonlu bir sayı olmalıdır.")
    lower, upper = {"rsi": (0, 100), "wr": (-100, 0), "combo": (1, 4), "hunter": (1, 15)}[indicator]
    if not lower <= threshold <= upper:
        raise AlarmEvaluationError("Alarm eşiği gösterge aralığı dışında.")
    if indicator in {"combo", "hunter"} and not float(threshold).is_integer():
        raise AlarmEvaluationError("Skor eşiği tam sayı olmalıdır.")


def _previous_weekday(day: pd.Timestamp) -> pd.Timestamp:
    day -= pd.Timedelta(days=1)
    while day.dayofweek >= 5:
        day -= pd.Timedelta(days=1)
    return day


def _expected_latest_open(now: pd.Timestamp, market_type: str, timeframe: str) -> pd.Timestamp:
    if market_type == "Kripto":
        return now.floor(_DURATIONS[timeframe]) - _DURATIONS[timeframe]
    local = now.tz_convert(_ISTANBUL)
    day = local.normalize()
    if timeframe == "1d":
        return _previous_weekday(day).tz_convert("UTC")
    if local.dayofweek < 5 and local.hour >= 11:
        return (day + pd.Timedelta(hours=min(local.hour - 1, 17))).tz_convert("UTC")
    return (_previous_weekday(day) + pd.Timedelta(hours=17)).tz_convert("UTC")


def _closed_bars(
    raw: pd.DataFrame, *, market_type: str, timeframe: str, now: datetime
) -> pd.DataFrame:
    if raw is None or not isinstance(raw, pd.DataFrame) or raw.empty:
        raise AlarmEvaluationError("Sağlayıcı mum verisi döndürmedi.")
    if raw.attrs.get("timeframe") != timeframe:
        raise AlarmEvaluationError("Sağlayıcı periyodu doğrulanamadı; günlük veriye geçilmedi.")
    if not isinstance(raw.index, pd.DatetimeIndex) or raw.index.tz is None:
        raise AlarmEvaluationError("Mum saat dilimi doğrulanamadı.")
    if raw.index.hasnans or raw.index.has_duplicates or not raw.index.is_monotonic_increasing:
        raise AlarmEvaluationError("Mum zamanları tekrarlı veya sırasız.")
    if not all(column in raw for column in _OHLCV):
        raise AlarmEvaluationError("OHLCV mum alanları eksik.")
    frame = raw.loc[:, _OHLCV].copy()
    frame.index = frame.index.tz_convert("UTC")
    instant = pd.Timestamp(now)
    if (frame.index > instant).any():
        raise AlarmEvaluationError("Sağlayıcı geleceğe ait mum zamanı döndürdü.")
    if market_type == "BIST":
        local = frame.index.tz_convert(_ISTANBUL)
        if timeframe == "1h":
            # yfinance may return the separate 18:00 closing-auction fragment.
            frame = frame[(local.dayofweek < 5) & (local.hour >= 10) & (local.hour < 18)]
            local = frame.index.tz_convert(_ISTANBUL)
            if ((local.minute != 0) | (local.second != 0) | (local.microsecond != 0)).any():
                raise AlarmEvaluationError("BIST saatlik mum başlangıçları geçersiz.")
        elif ((local != local.normalize()) | (local.dayofweek >= 5)).any():
            raise AlarmEvaluationError("BIST günlük mum başlangıçları geçersiz.")
    elif (frame.index != frame.index.floor(_DURATIONS[timeframe])).any():
        raise AlarmEvaluationError("Kripto mum başlangıçları periyotla uyuşmuyor.")
    # The exact boundary is closed; current/forming OHLCV never enters an indicator.
    frame = frame[frame.index + _DURATIONS[timeframe] <= instant]
    if len(frame) < 120:
        raise AlarmEvaluationError("En az 120 kapanmış mum gerekli.")
    expected = _expected_latest_open(instant, market_type, timeframe)
    if frame.index[-1] != expected:
        message = "Son kapanmış mum eksik veya eski; alarm değerlendirilmedi."
        if market_type == "BIST":
            message += " Tatil/yarım gün takvimi doğrulanmıyor."
        raise AlarmEvaluationError(message)
    if market_type == "Kripto":
        if (frame.index.to_series().diff().iloc[1:] != _DURATIONS[timeframe]).any():
            raise AlarmEvaluationError("Mum serisinde eksik periyot var.")
    elif timeframe == "1h":
        local = frame.index.tz_convert(_ISTANBUL)
        for day in local.normalize().unique():
            hours = local[local.normalize() == day].hour.to_list()
            if hours != list(range(hours[0], hours[-1] + 1)):
                raise AlarmEvaluationError("BIST seansı içinde eksik saatlik mum var.")
            if day != local[0].normalize() and hours[0] != 10:
                raise AlarmEvaluationError("BIST seansının ilk saatlik mumu eksik.")
            # A truncated final session must never masquerade as a completed day.
            if day != local[-1].normalize() and hours[-1] != 17:
                raise AlarmEvaluationError("BIST önceki seansı eksik; yarım gün doğrulanmıyor.")
    try:
        frame = frame.astype(float)
    except (TypeError, ValueError) as exc:
        raise AlarmEvaluationError("OHLCV verisi sayısal değil.") from exc
    if not np.isfinite(frame.to_numpy()).all():
        raise AlarmEvaluationError("OHLCV verisinde eksik veya sonlu olmayan değer var.")
    if (frame[["Open", "High", "Low", "Close"]] <= 0).any().any() or (frame.Volume < 0).any():
        raise AlarmEvaluationError("OHLCV fiyat/hacim aralığı geçersiz.")
    if (frame.High < frame[["Open", "Close", "Low"]].max(axis=1)).any() or (
        frame.Low > frame[["Open", "Close", "High"]].min(axis=1)
    ).any():
        raise AlarmEvaluationError("OHLC mum fiyatları tutarsız.")
    return frame


def _indicator_value(frame: pd.DataFrame, indicator: str, side: str, timeframe: str) -> float:
    if indicator == "rsi":
        value = float(rsi(frame.Close, window=14, fillna=False).iloc[-1])
    elif indicator == "wr":
        value = float(williams_r(frame.High, frame.Low, frame.Close, lbp=14, fillna=False).iloc[-1])
    else:
        calculator = calculate_combo_signal if indicator == "combo" else calculate_hunter_signal
        result = calculator(frame, "1D" if timeframe == "1d" else timeframe)
        fields = _INDICATOR_FIELDS[indicator]
        details = (result or {}).get("details", {})
        if details.get("ActiveIndicators") != f"{len(fields)}/{len(fields)}":
            raise AlarmEvaluationError("Gösterge bileşenleri eksik; kısmi skor kullanılmadı.")
        try:
            if not all(math.isfinite(float(details[field])) for field in fields):
                raise ValueError
            key = (
                ("BuyScore" if side == "dip" else "SellScore")
                if indicator == "combo"
                else ("DipScore" if side == "dip" else "TopScore")
            )
            value = float(details[key].split("/", 1)[0])
        except (TypeError, ValueError, KeyError, AttributeError) as exc:
            raise AlarmEvaluationError(
                "Gösterge bileşenleri sonlu değil veya skor geçersiz."
            ) from exc
        if not value.is_integer() or not 0 <= value <= len(fields):
            raise AlarmEvaluationError("Hesaplanan gösterge skoru geçersiz.")
    if not math.isfinite(value):
        raise AlarmEvaluationError("Gösterge değeri hesaplanamadı.")
    return value


def evaluate_closed_alarm_bars(
    raw: pd.DataFrame,
    *,
    market_type: str,
    timeframe: str,
    indicator: str,
    side: str,
    threshold: float,
    now: datetime,
) -> dict[str, Any]:
    """Pure evaluation seam for offline fixtures; caller validates rule arguments."""
    frame = _closed_bars(raw, market_type=market_type, timeframe=timeframe, now=now)
    previous = _indicator_value(frame.iloc[:-1], indicator, side, timeframe)
    value = _indicator_value(frame, indicator, side, timeframe)

    def matches(number: float) -> bool:
        return (
            number >= threshold
            if indicator in {"combo", "hunter"} or side == "top"
            else number <= threshold
        )

    label = "Python backend COMBO/HUNTER" if indicator in {"combo", "hunter"} else "Python ta (14)"
    return {
        "bar_time": frame.index[-1].isoformat().replace("+00:00", "Z"),
        "bar_closed_at": (frame.index[-1] + _DURATIONS[timeframe])
        .isoformat()
        .replace("+00:00", "Z"),
        "matched": matches(value),
        "previous_matched": matches(previous),
        "value": value,
        "detail": f"{label}; kapanmış mum; {indicator.upper()}={value:.4f}; eşik={threshold:g}",
    }


class ServerAlarmEvaluator:
    """Bound active provider calls to two even when a timed-out thread cannot stop.

    Cache entries are bounded, expire in 30 seconds, and are rechecked against the
    requested wall-clock time on every evaluation. No stale-value fallback exists.
    """

    def __init__(
        self,
        provider: AlarmDataProvider | None = None,
        *,
        timeout_seconds: float = 25,
        cache_seconds: float = 30,
    ) -> None:
        self.provider = provider or PublicAlarmDataProvider()
        self.timeout_seconds = timeout_seconds
        self.cache_seconds = min(max(cache_seconds, 0), 30)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="alarm-data")
        self._lock = threading.Lock()
        self._inflight: dict[tuple[str, str, str], Future] = {}
        self._cache: OrderedDict[tuple[str, str, str], tuple[float, pd.DataFrame]] = OrderedDict()

    def close(self) -> None:
        """Stop accepting work; HTTP timeouts bound already running provider calls."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _complete(self, key: tuple[str, str, str], future: Future) -> None:
        with self._lock:
            if self._inflight.get(key) is future:
                self._inflight.pop(key, None)

    async def _fetch(self, symbol: str, market_type: str, timeframe: str) -> pd.DataFrame:
        key = (symbol, market_type, timeframe)
        with self._lock:
            cached = self._cache.get(key)
            if cached and time.monotonic() - cached[0] < self.cache_seconds:
                return cached[1].copy(deep=True)
            future = self._inflight.get(key)
            if future is None:
                if len(self._inflight) >= 2:
                    raise AlarmEvaluationError(
                        "Veri sağlayıcı meşgul; sonraki kontrolde denenecek."
                    )
                future = self._executor.submit(
                    self.provider.fetch_bars,
                    symbol=symbol,
                    market_type=market_type,
                    timeframe=timeframe,
                )
                self._inflight[key] = future
        # Outside lock: callbacks can execute inline when a future already completed.
        future.add_done_callback(lambda done: self._complete(key, done))
        try:
            wrapped = asyncio.wrap_future(future)
            # Timed-out/cancelled callers leave native work running. Consume any
            # eventual error so asyncio does not emit an unhandled-future warning.
            wrapped.add_done_callback(
                lambda done: done.exception() if not done.cancelled() else None
            )
            raw = await asyncio.wait_for(asyncio.shield(wrapped), self.timeout_seconds)
        except TimeoutError as exc:
            raise AlarmEvaluationError("Veri sağlayıcı zaman aşımına uğradı.") from exc
        except AlarmEvaluationError:
            raise
        except Exception as exc:
            raise AlarmEvaluationError(
                "Veri sağlayıcıya erişilemedi; sonraki kontrolde denenecek."
            ) from exc
        if not isinstance(raw, pd.DataFrame) or raw.empty:
            raise AlarmEvaluationError("Sağlayıcı mum verisi döndürmedi.")
        with self._lock:
            self._cache[key] = (time.monotonic(), raw.copy(deep=True))
            self._cache.move_to_end(key)
            while len(self._cache) > 128:
                self._cache.popitem(last=False)
        return raw.copy(deep=True)

    async def evaluate(
        self,
        *,
        symbol: str,
        market_type: str,
        timeframe: str,
        indicator: str,
        side: str,
        threshold: float,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        _validate_request(symbol, market_type, timeframe, indicator, side, threshold)
        instant = now or datetime.now(UTC)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise AlarmEvaluationError("Değerlendirme zamanı saat dilimli olmalıdır.")
        raw = await self._fetch(symbol, market_type, timeframe)
        return evaluate_closed_alarm_bars(
            raw,
            market_type=market_type,
            timeframe=timeframe,
            indicator=indicator,
            side=side,
            threshold=threshold,
            now=instant.astimezone(UTC),
        )


_evaluator = ServerAlarmEvaluator()


async def evaluate_alarm_symbol(
    *,
    symbol: str,
    market_type: str,
    timeframe: str,
    indicator: str,
    side: str,
    threshold: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    return await _evaluator.evaluate(
        symbol=symbol,
        market_type=market_type,
        timeframe=timeframe,
        indicator=indicator,
        side=side,
        threshold=threshold,
        now=now,
    )
