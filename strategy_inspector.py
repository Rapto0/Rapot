"""
Strategy inspector service.

Reusable strategy and indicator inspection flow for Telegram, API and frontend.
"""

from __future__ import annotations

import datetime as dt
import html
from typing import Any

import pandas as pd

from config import TIMEFRAMES
from data_loader import get_bist_data, get_crypto_data, resample_data
from signals import calculate_combo_signal, calculate_hunter_signal

COMBO_INDICATORS: tuple[tuple[str, str], ...] = (
    ("MACD", "MACD"),
    ("RSI", "RSI (14)"),
    ("WR", "W%R"),
    ("CCI", "CCI (20)"),
)

HUNTER_INDICATORS: tuple[tuple[str, str], ...] = (
    ("RSI", "RSI (14)"),
    ("RSI_Fast", "RSI Fast"),
    ("CMO", "CMO"),
    ("BOP", "BOP"),
    ("MACD", "MACD"),
    ("W%R", "W%R"),
    ("CCI", "CCI"),
    ("ULT", "Ultimate"),
    ("BBP", "Boll %B"),
    ("ROC", "ROC"),
    ("DeM", "DeMarker"),
    ("PSY", "PSY"),
    ("ZScore", "Z-Score"),
    ("KeltPB", "Keltner %B"),
    ("RSI2", "RSI (2)"),
)

STRATEGY_CONFIG: dict[str, dict[str, Any]] = {
    "COMBO": {
        "calculator": calculate_combo_signal,
        "indicators": COMBO_INDICATORS,
        "primary_score_key": "BuyScore",
        "primary_score_label": "AL Skoru",
        "secondary_score_key": "SellScore",
        "secondary_score_label": "SAT Skoru",
    },
    "HUNTER": {
        "calculator": calculate_hunter_signal,
        "indicators": HUNTER_INDICATORS,
        "primary_score_key": "DipScore",
        "primary_score_label": "Dip Skoru",
        "secondary_score_key": "TopScore",
        "secondary_score_label": "Tepe Skoru",
    },
}

TELEGRAM_MESSAGE_LIMIT = 3500
TELEGRAM_GROUP_ORDER: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "COMBO": (("Cekirdek", ("MACD", "RSI", "WR", "CCI")),),
    "HUNTER": (
        ("Momentum", ("RSI", "RSI2", "CMO")),
        ("Trend", ("MACD", "ROC", "ZScore")),
        ("Range", ("W%R", "CCI", "ULT")),
        ("Band", ("BBP", "KeltPB", "DeM")),
        ("Akis", ("BOP", "PSY")),
    ),
}
TELEGRAM_INDICATOR_LABELS: dict[str, str] = {
    "RSI": "RSI14",
    "RSI_Fast": "RSIF",
    "CMO": "CMO",
    "BOP": "BOP",
    "MACD": "MACD",
    "W%R": "W%R",
    "CCI": "CCI",
    "ULT": "ULT",
    "BBP": "BB%",
    "ROC": "ROC",
    "DeM": "DeM",
    "PSY": "PSY",
    "ZScore": "Z",
    "KeltPB": "Kel%",
    "RSI2": "RSI2",
    "WR": "W%R",
}


class StrategyInspectorError(ValueError):
    """Raised when the inspector request cannot be fulfilled."""


def normalize_strategy(strategy: str) -> str:
    normalized = (strategy or "").strip().upper()
    if normalized not in STRATEGY_CONFIG:
        raise StrategyInspectorError("Gecersiz strateji. COMBO veya HUNTER kullanin.")
    return normalized


def normalize_market_type(market_type: str | None) -> str | None:
    if market_type is None:
        return None

    normalized = market_type.strip().upper()
    if normalized in {"", "AUTO"}:
        return None
    if normalized == "BIST":
        return "BIST"
    if normalized in {"KRIPTO", "KRYPTO"}:
        return "Kripto"

    raise StrategyInspectorError("Gecersiz piyasa tipi. BIST, Kripto veya AUTO kullanin.")


def _load_market_data(symbol: str, market_type: str) -> tuple[str, str, pd.DataFrame | None]:
    if market_type == "BIST":
        normalized_symbol = symbol.replace(".IS", "")
        return normalized_symbol, "BIST", get_bist_data(normalized_symbol)

    normalized_symbol = symbol
    if not normalized_symbol.endswith(("USDT", "BTC", "TRY")):
        normalized_symbol = f"{normalized_symbol}USDT"
    return normalized_symbol, "Kripto", get_crypto_data(normalized_symbol)


def resolve_market_data(
    symbol: str,
    market_type: str | None = None,
) -> tuple[str, str, pd.DataFrame]:
    """
    Resolve user input into symbol, market type and daily OHLCV dataframe.
    """
    normalized_symbol = (symbol or "").strip().upper()
    if not normalized_symbol:
        raise StrategyInspectorError("Sembol bos olamaz.")

    normalized_market = normalize_market_type(market_type)
    if normalized_market:
        resolved_symbol, resolved_market, df = _load_market_data(
            normalized_symbol, normalized_market
        )
        if df is None or df.empty:
            raise StrategyInspectorError(f"{resolved_market} verisi bulunamadi: {resolved_symbol}")
        return resolved_symbol, resolved_market, df

    candidate_markets: list[str] = []
    if normalized_symbol.endswith(("USDT", "BTC", "TRY")):
        candidate_markets = ["Kripto", "BIST"]
    else:
        candidate_markets = ["BIST", "Kripto"]

    for candidate_market in candidate_markets:
        resolved_symbol, resolved_market, df = _load_market_data(
            normalized_symbol, candidate_market
        )
        if df is not None and not df.empty:
            return resolved_symbol, resolved_market, df

    raise StrategyInspectorError(f"Veri bulunamadi: {normalized_symbol}")


def inspect_strategy_dataframe(
    df_daily: pd.DataFrame,
    symbol: str,
    market_type: str,
    strategy: str,
) -> dict[str, Any]:
    """
    Run one strategy across all configured timeframes and return structured output.
    """
    normalized_strategy = normalize_strategy(strategy)
    config = STRATEGY_CONFIG[normalized_strategy]
    calculator = config["calculator"]
    indicator_pairs: tuple[tuple[str, str], ...] = config["indicators"]

    timeframe_results: list[dict[str, Any]] = []
    for timeframe_code, timeframe_label in TIMEFRAMES:
        df_resampled = resample_data(df_daily.copy(), timeframe_code)
        if df_resampled is None or df_resampled.empty:
            timeframe_results.append(
                {
                    "code": timeframe_code,
                    "label": timeframe_label,
                    "available": False,
                    "signal_status": "YOK",
                    "reason": "Veri yok",
                    "price": None,
                    "date": None,
                    "active_indicators": None,
                    "primary_score": None,
                    "primary_score_label": config["primary_score_label"],
                    "secondary_score": None,
                    "secondary_score_label": config["secondary_score_label"],
                    "raw_score": None,
                    "indicators": {key: None for key, _ in indicator_pairs},
                }
            )
            continue

        result = calculator(df_resampled, timeframe_code)
        if not result:
            timeframe_results.append(
                {
                    "code": timeframe_code,
                    "label": timeframe_label,
                    "available": False,
                    "signal_status": "YOK",
                    "reason": "Yetersiz veri",
                    "price": None,
                    "date": None,
                    "active_indicators": None,
                    "primary_score": None,
                    "primary_score_label": config["primary_score_label"],
                    "secondary_score": None,
                    "secondary_score_label": config["secondary_score_label"],
                    "raw_score": None,
                    "indicators": {key: None for key, _ in indicator_pairs},
                }
            )
            continue

        details = result.get("details", {})
        signal_status = "AL" if result.get("buy") else ("SAT" if result.get("sell") else "NOTR")
        timeframe_results.append(
            {
                "code": timeframe_code,
                "label": timeframe_label,
                "available": True,
                "signal_status": signal_status,
                "reason": None,
                "price": details.get("PRICE"),
                "date": details.get("DATE"),
                "active_indicators": details.get("ActiveIndicators"),
                "primary_score": details.get(config["primary_score_key"]),
                "primary_score_label": config["primary_score_label"],
                "secondary_score": details.get(config["secondary_score_key"]),
                "secondary_score_label": config["secondary_score_label"],
                "raw_score": details.get("Score"),
                "indicators": {key: details.get(key) for key, _ in indicator_pairs},
            }
        )

    return {
        "symbol": symbol,
        "market_type": market_type,
        "strategy": normalized_strategy,
        "timeframes": timeframe_results,
        "indicator_order": [key for key, _ in indicator_pairs],
        "indicator_labels": dict(indicator_pairs),
        "generated_at": dt.datetime.now(dt.timezone.utc)  # noqa: UP017
        .isoformat()
        .replace("+00:00", "Z"),
    }


def inspect_strategy(
    symbol: str,
    strategy: str,
    market_type: str | None = None,
) -> dict[str, Any]:
    resolved_symbol, resolved_market_type, df_daily = resolve_market_data(symbol, market_type)
    return inspect_strategy_dataframe(
        df_daily=df_daily,
        symbol=resolved_symbol,
        market_type=resolved_market_type,
        strategy=strategy,
    )


def _signal_emoji(signal_status: str) -> str:
    if signal_status == "AL":
        return "🟢"
    if signal_status == "SAT":
        return "🔴"
    return "⚪"


def _format_indicator_value(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _build_indicator_grid(
    strategy: str,
    indicator_order: list[str],
    indicator_values: dict[str, Any],
) -> str:
    groups = TELEGRAM_GROUP_ORDER.get(strategy, (("Veriler", tuple(indicator_order)),))
    rows: list[str] = []

    for group_label, group_indicators in groups:
        parts: list[str] = []
        for indicator_key in group_indicators:
            if indicator_key not in indicator_order:
                continue
            short_label = TELEGRAM_INDICATOR_LABELS.get(indicator_key, indicator_key)
            formatted_value = _format_indicator_value(indicator_values.get(indicator_key))
            parts.append(f"{short_label:>5} {formatted_value:>8}")

        if not parts:
            continue

        rows.append(f"{group_label:<9} " + "  ".join(parts))

    return "\n".join(rows)


def build_strategy_inspector_chunks(report: dict[str, Any]) -> list[str]:
    """
    Convert structured inspector data into Telegram-friendly chunks.
    """
    header = (
        f"🔬 <b>STRATEJI INSPECTOR</b>\n"
        f"<b>{html.escape(report['symbol'])}</b> | "
        f"{html.escape(report['market_type'])} | "
        f"{html.escape(report['strategy'])}\n"
        f"Periyotlar: 1G / 1Hf / 2Hf / 3Hf / 1Ay"
    )

    indicator_order = report["indicator_order"]
    blocks: list[str] = []

    for timeframe in report["timeframes"]:
        title = (
            f"{_signal_emoji(timeframe['signal_status'])} "
            f"<b>{html.escape(timeframe['label'])}</b> | "
            f"<b>{html.escape(timeframe['signal_status'])}</b>"
        )
        if not timeframe["available"]:
            blocks.append(f"{title}\n" f"• Sebep: {html.escape(str(timeframe['reason']))}")
            continue

        score_line = (
            f"{timeframe['primary_score_label']}: "
            f"{_format_indicator_value(timeframe['primary_score'])} | "
            f"{timeframe['secondary_score_label']}: "
            f"{_format_indicator_value(timeframe['secondary_score'])}"
        )
        meta_lines = [
            (
                f"• Tarih: {html.escape(str(timeframe['date']))} | "
                f"Fiyat: {_format_indicator_value(timeframe['price'])}"
            ),
            (
                f"• {html.escape(score_line)} | "
                f"Aktif: {html.escape(str(timeframe['active_indicators']))}"
            ),
        ]
        if timeframe.get("raw_score"):
            meta_lines.append(f"• Ham Skor: {html.escape(str(timeframe['raw_score']))}")

        indicator_grid = _build_indicator_grid(
            strategy=report["strategy"],
            indicator_order=indicator_order,
            indicator_values=timeframe["indicators"],
        )
        block_lines = [title, *meta_lines]
        if indicator_grid:
            block_lines.append(f"<pre>{html.escape(indicator_grid)}</pre>")
        blocks.append("\n".join(block_lines))

    chunks: list[str] = []
    current_chunk = header
    for block in blocks:
        candidate = f"{current_chunk}\n\n{block}"
        if len(candidate) > TELEGRAM_MESSAGE_LIMIT:
            chunks.append(current_chunk)
            current_chunk = f"🔬 <b>STRATEJI INSPECTOR DEVAM</b>\n\n{block}"
        else:
            current_chunk = candidate

    if current_chunk:
        chunks.append(current_chunk)

    return chunks
