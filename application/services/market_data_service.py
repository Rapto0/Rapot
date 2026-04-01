from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException

from api.providers.market_data_provider import MarketDataProvider

_MARKET_OVERVIEW_SYMBOLS = {"bist": "XU100.IS", "crypto": "BTC-USD"}
_MARKET_INDEX_DISPLAY_NAMES = {
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "XU100.IS": "BIST 100",
    "^VIX": "VIX",
    "DX-Y.NYB": "DXY",
    "TRY=X": "USD/TRY",
    "XAUUSD=X": "XAUUSD",
    "XAGUSD=X": "XAGUSD",
    "GC=F": "XAUUSD",
    "SI=F": "XAGUSD",
}
_MARKET_TICKER_SYMBOLS = [
    {"symbol": "XU100.IS", "name": "BIST 100"},
    {"symbol": "THYAO.IS", "name": "THY"},
    {"symbol": "GARAN.IS", "name": "Garanti"},
    {"symbol": "AKBNK.IS", "name": "Akbank"},
    {"symbol": "BTC-USD", "name": "Bitcoin"},
    {"symbol": "ETH-USD", "name": "Ethereum"},
]


async def build_market_overview_payload(
    *,
    provider: MarketDataProvider,
) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}

    for key, symbol in _MARKET_OVERVIEW_SYMBOLS.items():
        df = await asyncio.to_thread(
            provider.fetch_history_with_fallback,
            symbol,
            period="1d",
            fallback_period="5d",
            interval="15m",
        )
        if df.empty:
            df = await asyncio.to_thread(
                provider.fetch_history_with_fallback,
                symbol,
                period="5d",
                fallback_period=None,
                interval="60m",
            )

        history = []
        if not df.empty:
            current_value = float(df["Close"].iloc[-1])
            first_value = float(df["Open"].iloc[0])
            change_percent = ((current_value - first_value) / first_value) * 100

            for index, row in df.iterrows():
                history.append({"time": index.strftime("%H:%M"), "value": float(row["Close"])})

            data[key] = {
                "currentValue": current_value,
                "change": change_percent,
                "history": history,
            }
        else:
            data[key] = {"currentValue": 0, "change": 0, "history": []}

    return data


async def build_market_indices_payload(
    *,
    symbols: list[str],
    market_index_cache: dict[str, tuple[datetime, dict[str, float | str]]],
    market_index_cache_ttl: timedelta,
    market_index_canonical: dict[str, str],
    market_index_fallbacks: dict[str, str],
    provider: MarketDataProvider,
) -> list[dict[str, float | str]]:
    unique_symbols = []
    for raw_symbol in symbols:
        normalized = raw_symbol.strip().upper().lstrip("$")
        if not normalized:
            continue
        if normalized in unique_symbols:
            continue
        unique_symbols.append(normalized)

    unique_symbols = unique_symbols[:30]

    items: list[dict[str, float | str]] = []
    now = datetime.now()
    for ticker_symbol in unique_symbols:
        cached = market_index_cache.get(ticker_symbol)
        if cached and now - cached[0] <= market_index_cache_ttl:
            items.append(dict(cached[1]))
            continue

        canonical_symbol = market_index_canonical.get(ticker_symbol, ticker_symbol)
        candidate_symbols = [canonical_symbol]
        fallback_symbol = market_index_fallbacks.get(canonical_symbol)
        if fallback_symbol and fallback_symbol not in candidate_symbols:
            candidate_symbols.append(fallback_symbol)

        hist = None
        for candidate in candidate_symbols:
            hist = await asyncio.to_thread(
                provider.fetch_history_with_fallback,
                candidate,
                period="2d",
                fallback_period="5d",
                interval=None,
            )
            if not hist.empty:
                break

        if hist is None or hist.empty:
            continue

        close_series = hist.get("Close")
        open_series = hist.get("Open")
        if close_series is None:
            continue

        close_values = close_series.dropna()
        if close_values.empty:
            continue

        current_price = float(close_values.iloc[-1])
        if not math.isfinite(current_price):
            continue

        if len(close_values) > 1:
            previous_close = float(close_values.iloc[-2])
        elif open_series is not None and not open_series.dropna().empty:
            previous_close = float(open_series.dropna().iloc[-1])
        else:
            previous_close = current_price

        if not math.isfinite(previous_close):
            previous_close = current_price

        change_percent = (
            ((current_price - previous_close) / previous_close) * 100 if previous_close else 0.0
        )

        item: dict[str, float | str] = {
            "symbol": ticker_symbol,
            "regularMarketPrice": current_price,
            "regularMarketChangePercent": change_percent,
            "shortName": _MARKET_INDEX_DISPLAY_NAMES.get(ticker_symbol, ticker_symbol),
        }
        market_index_cache[ticker_symbol] = (now, item)
        items.append(item)

    return items


async def build_market_ticker_payload(
    *,
    provider: MarketDataProvider,
) -> list[dict[str, float | str]]:
    tickers = []
    for item in _MARKET_TICKER_SYMBOLS:
        s_symbol = item["symbol"]
        hist = await asyncio.to_thread(
            provider.fetch_history_with_fallback,
            s_symbol,
            period="2d",
            fallback_period=None,
            interval=None,
        )

        if not hist.empty and len(hist) >= 1:
            current_price = float(hist["Close"].iloc[-1])
            prev_close = (
                float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(hist["Open"].iloc[0])
            )

            change = current_price - prev_close
            change_percent = (change / prev_close) * 100

            tickers.append(
                {
                    "symbol": s_symbol.replace(".IS", "").replace("-USD", "USDT"),
                    "name": item["name"],
                    "price": current_price,
                    "change": change,
                    "changePercent": change_percent,
                }
            )

    return tickers


async def build_market_metrics_payload(
    *,
    keys: list[str] | None,
    extract_close_series_from_download: Callable[..., Any],
    calculate_market_metric_payload: Callable[..., Any],
    provider: MarketDataProvider,
    logger: Any,
) -> dict[str, dict[str, float | None | str]]:
    normalized_keys = []
    for item in keys or []:
        if not item or ":" not in item:
            continue
        market_raw, symbol_raw = item.split(":", 1)
        market = "BIST" if market_raw.strip().upper() == "BIST" else "Kripto"
        symbol = symbol_raw.strip().upper()
        if not symbol:
            continue
        normalized_keys.append(f"{market}:{symbol}")

    normalized_keys = list(dict.fromkeys(normalized_keys))[:600]
    if not normalized_keys:
        return {}

    groups: dict[str, list[tuple[str, str]]] = {"BIST": [], "Kripto": []}
    for item in normalized_keys:
        market, symbol = item.split(":", 1)
        if market == "BIST":
            ticker = symbol if symbol.endswith(".IS") else f"{symbol}.IS"
            groups["BIST"].append((item, ticker))
        else:
            if symbol.endswith("USDT"):
                ticker = symbol.replace("USDT", "-USD")
            elif "-" in symbol:
                ticker = symbol
            else:
                ticker = f"{symbol}-USD"
            groups["Kripto"].append((item, ticker))

    metrics: dict[str, dict[str, float | None | str]] = {}

    for market, items in groups.items():
        if not items:
            continue
        tickers = [ticker for _, ticker in items]
        try:
            download_df = await asyncio.to_thread(
                provider.fetch_yfinance_download,
                tickers if len(tickers) > 1 else tickers[0],
            )
        except Exception:
            logger.exception("Market metrics download error (%s).", market)
            continue

        for key_name, ticker in items:
            close_series = extract_close_series_from_download(download_df, ticker)
            payload = calculate_market_metric_payload(close_series)
            if payload:
                payload["source"] = "yfinance_batch"
                metrics[key_name] = payload

        missing_items = [
            (key_name, ticker) for key_name, ticker in items if key_name not in metrics
        ]
        for key_name, ticker in missing_items:
            try:
                single_hist = await asyncio.to_thread(
                    provider.fetch_history_with_fallback,
                    ticker,
                    period="3mo",
                    fallback_period=None,
                    interval="1d",
                )
                close_series = extract_close_series_from_download(single_hist, ticker)
                payload = calculate_market_metric_payload(close_series)
                if payload:
                    payload["source"] = "yfinance_single"
                    metrics[key_name] = payload
            except Exception:
                continue

    missing_crypto = [item for item, _ in groups["Kripto"] if item not in metrics]
    if missing_crypto:
        symbols = [item.split(":", 1)[1] for item in missing_crypto]
        binance_metrics = await asyncio.to_thread(provider.fetch_binance_24h_metrics, symbols)
        for key_name in missing_crypto:
            symbol = provider.normalize_binance_symbol(key_name.split(":", 1)[1])
            payload = binance_metrics.get(symbol)
            if payload:
                metrics[key_name] = payload

    return metrics


async def build_candles_payload(
    *,
    symbol: str,
    market_type: str,
    timeframe: str,
    limit: int,
    provider: MarketDataProvider,
    logger: Any,
) -> dict[str, Any]:
    symbol = symbol.upper()
    limit = min(limit, 2000)

    raw_timeframe = timeframe.strip()
    timeframe_aliases = {
        "GUNLUK": "1d",
        "GÜNLÜK": "1d",
        "D": "1d",
        "HAFTALIK": "1wk",
        "W": "1wk",
        "2 HAFTALIK": "2wk",
        "3 HAFTALIK": "3wk",
        "AYLIK": "1mo",
        "M": "1mo",
    }
    timeframe = timeframe_aliases.get(raw_timeframe.upper(), raw_timeframe.lower())

    binance_interval_map = {
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "8h": "8h",
        "12h": "12h",
        "18h": "12h",
        "1d": "1d",
        "2d": "1d",
        "3d": "3d",
        "1wk": "1w",
        "2wk": "1w",
        "3wk": "1w",
        "1mo": "1M",
        "2mo": "1M",
        "3mo": "1M",
    }

    is_intraday = timeframe in ["15m", "30m", "1h", "2h", "4h", "8h", "12h"]
    binance_interval = binance_interval_map.get(timeframe, "1d")

    df = None
    source = "cache"

    try:
        if market_type == "BIST" and is_intraday:
            try:
                import pytz

                yf_symbol = symbol + ".IS" if not symbol.endswith(".IS") else symbol
                if timeframe in ["15m", "30m", "1h"]:
                    yf_interval = "15m"
                    period = "60d"
                else:
                    yf_interval = "1h"
                    period = "730d"

                df = await asyncio.to_thread(
                    provider.fetch_history_with_fallback,
                    yf_symbol,
                    period=period,
                    fallback_period=None,
                    interval=yf_interval,
                    auto_adjust=False,
                    actions=False,
                )

                if df is not None and not df.empty:
                    turkey_tz = pytz.timezone("Europe/Istanbul")
                    if hasattr(df.index, "tz") and df.index.tz is not None:
                        df.index = df.index.tz_convert(turkey_tz)
                    else:
                        with suppress(Exception):
                            df.index = df.index.tz_localize("UTC").tz_convert(turkey_tz)

                    df = df[df.index.dayofweek < 5]
                    session_mask = (
                        (df.index.hour > 10) | ((df.index.hour == 10) & (df.index.minute >= 0))
                    ) & (df.index.hour < 18)
                    df = df[session_mask]

                    agg_map = {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }

                    intraday_rule_map = {
                        "30m": "30min",
                        "1h": "1h",
                        "2h": "2h",
                        "4h": "4h",
                        "8h": "8h",
                        "12h": "12h",
                    }
                    rule = intraday_rule_map.get(timeframe)
                    if rule:
                        df = (
                            df.resample(
                                rule,
                                label="left",
                                closed="left",
                                origin="start_day",
                                offset="10h",
                            )
                            .agg(agg_map)
                            .dropna()
                        )

                    session_start_mask = (
                        (df.index.hour > 10) | ((df.index.hour == 10) & (df.index.minute >= 0))
                    ) & (df.index.hour < 18)
                    df = df[session_start_mask]

                    source = (
                        "yfinance_intraday_session_resampled"
                        if timeframe != yf_interval
                        else "yfinance_intraday_session"
                    )
            except Exception:
                logger.exception("yfinance intraday error for %s.", symbol)
                df = None

        elif market_type in ["Kripto", "CRYPTO"] and is_intraday:
            try:
                import pandas as pd

                klines = await asyncio.to_thread(
                    provider.fetch_binance_klines, symbol, binance_interval, limit
                )
                if klines:
                    df = pd.DataFrame(
                        klines,
                        columns=[
                            "timestamp",
                            "Open",
                            "High",
                            "Low",
                            "Close",
                            "Volume",
                            "close_time",
                            "quote_volume",
                            "trades",
                            "taker_buy_base",
                            "taker_buy_quote",
                            "ignore",
                        ],
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
                    source = "binance"
            except Exception:
                logger.exception("Binance intraday error for %s.", symbol)
                df = None

        if df is None or df.empty:
            try:
                from price_cache import price_cache

                df = price_cache.get(symbol, market_type)
                if df is not None and not df.empty:
                    if market_type == "BIST":
                        from data_loader import is_suspicious_bist_ohlcv

                        if is_suspicious_bist_ohlcv(df):
                            price_cache.invalidate(symbol, "BIST")
                            logger.warning("Invalidated suspicious BIST cache: %s", symbol)
                            df = None
                        else:
                            source = "cache"
                    else:
                        source = "cache"
            except Exception:
                logger.exception("Cache error for %s.", symbol)
                df = None

            if df is None or df.empty:
                if market_type == "BIST":
                    try:
                        from data_loader import get_bist_data

                        df = get_bist_data(symbol, start_date="01-01-2010")
                        source = str(getattr(df, "attrs", {}).get("source_hint", "isyatirim"))

                        if df is not None and not df.empty:
                            with suppress(Exception):
                                from data_loader import is_suspicious_bist_ohlcv
                                from price_cache import price_cache as pc

                                if is_suspicious_bist_ohlcv(df):
                                    pc.invalidate(symbol, market_type)
                                    logger.warning(
                                        "Skipped suspicious BIST cache write: %s", symbol
                                    )
                                else:
                                    pc.set(symbol, market_type, df)
                    except Exception:
                        logger.exception("BIST data error for %s.", symbol)
                        df = None
                elif market_type in ["Kripto", "CRYPTO"]:
                    try:
                        from data_loader import get_crypto_data

                        df = get_crypto_data(symbol, start_str="10 years ago")
                        source = "binance"

                        if df is not None and not df.empty:
                            with suppress(Exception):
                                from price_cache import price_cache as pc

                                pc.set(symbol, "Kripto", df)
                    except Exception:
                        logger.exception("Crypto data error for %s.", symbol)
                        df = None

        if df is None or df.empty:
            yf_symbol = symbol
            if market_type == "BIST" and not symbol.endswith(".IS"):
                yf_symbol = symbol + ".IS"
            elif symbol.endswith("USDT"):
                yf_symbol = symbol.replace("USDT", "-USD")

            df = await asyncio.to_thread(
                provider.fetch_history_with_fallback,
                yf_symbol,
                period="max",
                fallback_period=None,
                interval="1d",
            )
            source = "yfinance"

            if df.empty:
                raise HTTPException(status_code=404, detail=f"{symbol} için veri bulunamadı")

        if not is_intraday and df is not None and not df.empty:
            try:
                from data_loader import resample_market_data

                resampled = resample_market_data(df, timeframe, market_type)
                if resampled is not None and not resampled.empty:
                    df = resampled
                    if timeframe != "1d":
                        source = f"{source}_market_custom"
            except Exception:
                logger.exception("Resample error for %s (%s).", symbol, timeframe)

        import pytz

        turkey_tz = pytz.timezone("Europe/Istanbul")
        utc_tz = pytz.UTC
        candles = []
        if df is not None and not df.empty:
            df_tail = df.tail(limit)
            for index, row in df_tail.iterrows():
                ts = index
                if is_intraday:
                    if market_type == "BIST":
                        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                            ts = ts.astimezone(turkey_tz)
                        elif hasattr(ts, "tz_localize"):
                            with suppress(Exception):
                                ts = ts.tz_localize("UTC").tz_convert(turkey_tz)
                    else:
                        if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                            if hasattr(ts, "tz_convert"):
                                ts = ts.tz_convert(utc_tz)
                            else:
                                ts = ts.astimezone(utc_tz)
                            if hasattr(ts, "tz_localize"):
                                with suppress(Exception):
                                    ts = ts.tz_localize(None)
                        elif hasattr(ts, "tz_localize"):
                            with suppress(Exception):
                                ts = ts.tz_localize("UTC").tz_localize(None)
                    time_val = ts.strftime("%Y-%m-%d %H:%M")
                else:
                    time_val = ts.strftime("%Y-%m-%d")

                candles.append(
                    {
                        "time": time_val,
                        "open": float(row.get("Open", row.get("open", 0))),
                        "high": float(row.get("High", row.get("high", 0))),
                        "low": float(row.get("Low", row.get("low", 0))),
                        "close": float(row.get("Close", row.get("close", 0))),
                        "volume": int(row.get("Volume", row.get("volume", 0))),
                    }
                )

        return {
            "symbol": symbol,
            "market_type": market_type,
            "timeframe": timeframe,
            "source": source,
            "count": len(candles),
            "candles": candles,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Candle error for %s.", symbol)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
