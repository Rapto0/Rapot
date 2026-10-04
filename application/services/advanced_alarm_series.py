"""Pure native-candle validation and shared Python indicator observations.

BIST finality is witnessed by a following provider bar, never a guessed holiday
or session close. Consequently the last session bar can remain unconfirmed until
the next session. Crypto uses its native continuous UTC interval boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd
from ta.momentum import rsi, williams_r
from ta.trend import ema_indicator, macd, macd_signal, sma_indicator
from ta.volatility import average_true_range

from application.services.advanced_alarm_conditions import field_key
from application.services.advanced_alarm_data_cache import MAX_BARS
from application.services.server_alarm_evaluator import AlarmEvaluationError, _indicator_value

OHLCV = ["Open", "High", "Low", "Close", "Volume"]
SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400}


class SeriesError(ValueError):
    pass


def utc(value: float | None) -> str | None:
    return datetime.fromtimestamp(value, UTC).isoformat().replace("+00:00", "Z") if value else None


def bar_end(timestamp: pd.Timestamp, timeframe: str, market: str) -> float:
    local = timestamp.tz_convert("Europe/Istanbul" if market == "BIST" else "UTC")
    if timeframe in SECONDS:
        return timestamp.timestamp() + SECONDS[timeframe]
    if timeframe == "1d":
        end = local.normalize() + pd.DateOffset(days=1)
    elif timeframe == "1wk":
        end = local.normalize() + pd.DateOffset(days=7)
    else:
        end = local.normalize() + pd.DateOffset(months=1)
    return end.timestamp()


def validate_frame(raw: pd.DataFrame, timeframe: str, market: str, now: float) -> pd.DataFrame:
    if not isinstance(raw, pd.DataFrame) or raw.empty or len(raw) > 10000:
        raise SeriesError("Sağlayıcı mum verisi yok veya boyutu geçersiz.")
    if raw.attrs.get("timeframe") != timeframe:
        raise SeriesError("Sağlayıcı periyodu istenen periyotla eşleşmiyor.")
    if not isinstance(raw.index, pd.DatetimeIndex) or raw.index.tz is None:
        raise SeriesError("Sağlayıcının mum saat dilimi doğrulanamadı.")
    if not raw.index.is_unique or not raw.index.is_monotonic_increasing or raw.index.hasnans:
        raise SeriesError("Mum zamanları yineleniyor veya sıralı değil.")
    if any(column not in raw for column in OHLCV):
        raise SeriesError("OHLCV alanları eksik.")
    try:
        frame = raw[OHLCV].tail(MAX_BARS).astype(float).copy()
    except (ValueError, TypeError, OverflowError):
        raise SeriesError("OHLCV alanları sayısal değil.") from None
    frame.index = frame.index.tz_convert("UTC")
    if not np.isfinite(frame.to_numpy()).all():
        raise SeriesError("OHLCV alanları eksik veya sonlu değil.")
    if (frame[OHLCV[:4]] <= 0).any().any() or (frame.Volume < 0).any():
        raise SeriesError("OHLCV fiyat/hacim aralığı geçersiz.")
    if (frame.High < frame[["Open", "Close", "Low"]].max(axis=1)).any() or (
        frame.Low > frame[["Open", "Close", "High"]].min(axis=1)
    ).any():
        raise SeriesError("Mum fiyatları birbiriyle tutarsız.")
    if frame.index[-1].timestamp() > now + 5:
        raise SeriesError("Mum zamanı gelecekte.")
    local = frame.index.tz_convert("Europe/Istanbul" if market == "BIST" else "UTC")
    for previous, current in zip(local[:-1], local[1:], strict=True):
        if market == "BIST" and previous.date() != current.date():
            # Actual provider session sequence, not an invented holiday calendar.
            continue
        if (
            timeframe in SECONDS
            and current.timestamp() - previous.timestamp() != SECONDS[timeframe]
        ):
            raise SeriesError("Mum dizisinde periyot boşluğu var.")
        if (
            market == "Kripto"
            and timeframe not in SECONDS
            and current.timestamp() != bar_end(previous, timeframe, market)
        ):
            raise SeriesError("Mum dizisinde periyot boşluğu var.")
    return frame


@dataclass(frozen=True, slots=True)
class Point:
    time: float
    end: float
    confirmed: bool
    values: dict[str, float | None]


@dataclass(frozen=True, slots=True)
class Series:
    points: tuple[Point, ...]
    received: float
    source_time: float
    source: str
    version: str
    changed: float


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def calculate_series(
    frame: pd.DataFrame,
    timeframe: str,
    market: str,
    refs: list[dict],
    now: float,
    *,
    anchors: tuple[float, ...] = (),
) -> Series:
    """Compute each field once per series refresh, outside the alarm evaluation loop."""
    tail_start = max(0, len(frame) - 4)
    selected = set(range(tail_start, len(frame)))
    ends = [bar_end(stamp, timeframe, market) for stamp in frame.index]
    for anchor in anchors:
        eligible = [i for i, end in enumerate(ends) if end <= anchor]
        if eligible:
            selected.add(eligible[-1])
    indices = sorted(selected)
    values = [{} for _ in indices]
    for ref in refs:
        field, key = ref["field"], field_key(ref, timeframe)
        period = ref.get("period", 14)
        series = None
        if field in {"price", "open", "high", "low", "close", "volume"}:
            series = frame["Close" if field == "price" else field.title()]
        elif field == "rsi":
            series = rsi(frame.Close, window=period, fillna=False)
        elif field == "wr":
            series = williams_r(frame.High, frame.Low, frame.Close, lbp=period, fillna=False)
        elif field == "ema":
            series = ema_indicator(frame.Close, window=period, fillna=False)
        elif field == "sma":
            series = sma_indicator(frame.Close, window=period, fillna=False)
        elif field == "macd":
            series = macd(frame.Close, fillna=False)
        elif field == "macd_signal":
            series = macd_signal(frame.Close, fillna=False)
        elif field == "atr" and len(frame) >= period:
            series = average_true_range(frame.High, frame.Low, frame.Close, window=period)
            series.iloc[: period - 1] = np.nan
        if series is not None:
            for offset, index in enumerate(indices):
                values[offset][key] = _finite(series.iloc[index])
        elif field in {"combo", "hunter"}:
            for offset, index in enumerate(indices):
                try:
                    value = _indicator_value(
                        frame.iloc[: index + 1],
                        field,
                        "dip" if ref.get("side", "buy") == "buy" else "top",
                        {"1wk": "W-FRI", "1mo": "ME"}.get(timeframe, timeframe),
                    )
                except (AlarmEvaluationError, IndexError, ValueError, TypeError):
                    value = None
                values[offset][key] = value
        else:
            for item in values:
                item[key] = None
    points = []
    for offset, index in enumerate(indices):
        stamp = frame.index[index]
        end = bar_end(stamp, timeframe, market)
        following = index + 1 < len(frame) and frame.index[index + 1].timestamp() >= end
        confirmed = end <= now and (following or market == "Kripto")
        points.append(Point(stamp.timestamp(), end, confirmed, values[offset]))
    # Values, not receipt time, identify a genuine provider update.
    import hashlib

    version = hashlib.sha256(frame.tail(4).to_numpy().tobytes()).hexdigest()[:16]
    return Series(
        tuple(points),
        now,
        frame.index[-1].timestamp(),
        "borsapy_tradingview" if market == "BIST" else "binance",
        version,
        now,
    )


def candles(frame: pd.DataFrame, limit: int = MAX_BARS) -> list[dict]:
    return [
        {"time": int(stamp.timestamp()), **dict(zip((c.lower() for c in OHLCV), row, strict=True))}
        for stamp, row in zip(
            frame.tail(limit).index, frame.tail(limit).to_numpy().tolist(), strict=True
        )
    ]
