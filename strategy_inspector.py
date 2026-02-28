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
        ("Momentum", ("RSI", "RSI_Fast", "RSI2", "CMO")),
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
TELEGRAM_TIMEFRAME_ALIASES: dict[str, str] = {
    "1D": "1D",
    "1G": "1D",
    "GUNLUK": "1D",
    "W-FRI": "W-FRI",
    "1W": "W-FRI",
    "1HF": "W-FRI",
    "HAFTALIK": "W-FRI",
    "2W-FRI": "2W-FRI",
    "2W": "2W-FRI",
    "2HF": "2W-FRI",
    "3W-FRI": "3W-FRI",
    "3W": "3W-FRI",
    "3HF": "3W-FRI",
    "ME": "ME",
    "1M": "ME",
    "1AY": "ME",
    "AYLIK": "ME",
}
TIMEFRAME_ORDER: dict[str, int] = {code: index for index, (code, _) in enumerate(TIMEFRAMES)}


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


def _normalize_timeframe_codes(codes: list[str] | tuple[str, ...] | None) -> list[str]:
    if not codes:
        return []

    normalized_codes: list[str] = []
    seen: set[str] = set()
    for code in codes:
        normalized_code = str(code).strip().upper()
        if normalized_code and normalized_code in TIMEFRAME_ORDER and normalized_code not in seen:
            normalized_codes.append(normalized_code)
            seen.add(normalized_code)

    normalized_codes.sort(key=lambda current_code: TIMEFRAME_ORDER[current_code])
    return normalized_codes


def _copy_timeframe_payload(timeframe: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": timeframe.get("code"),
        "label": timeframe.get("label"),
        "available": timeframe.get("available"),
        "signal_status": timeframe.get("signal_status"),
        "reason": timeframe.get("reason"),
        "price": timeframe.get("price"),
        "date": timeframe.get("date"),
        "active_indicators": timeframe.get("active_indicators"),
        "primary_score": timeframe.get("primary_score"),
        "primary_score_label": timeframe.get("primary_score_label"),
        "secondary_score": timeframe.get("secondary_score"),
        "secondary_score_label": timeframe.get("secondary_score_label"),
        "raw_score": timeframe.get("raw_score"),
        "indicators": dict(timeframe.get("indicators", {})),
    }


def build_strategy_ai_payload(
    report: dict[str, Any],
    signal_type: str,
    special_tag: str | None = None,
    trigger_rule: list[str] | tuple[str, ...] | None = None,
    matched_timeframes: list[str] | tuple[str, ...] | None = None,
    scenario_name: str | None = None,
) -> dict[str, Any]:
    normalized_trigger_rule = _normalize_timeframe_codes(list(trigger_rule or []))
    normalized_matched_codes = _normalize_timeframe_codes(
        list(matched_timeframes or normalized_trigger_rule)
    )

    timeframe_index = {
        timeframe["code"]: timeframe
        for timeframe in report.get("timeframes", [])
        if timeframe.get("code")
    }
    selected_timeframes = [
        _copy_timeframe_payload(timeframe_index[current_code])
        for current_code in normalized_matched_codes
        if current_code in timeframe_index
    ]

    return {
        "symbol": report["symbol"],
        "market_type": report["market_type"],
        "strategy": report["strategy"],
        "scenario_name": scenario_name,
        "signal_type": signal_type,
        "special_tag": special_tag,
        "trigger_rule": normalized_trigger_rule,
        "matched_timeframes": selected_timeframes,
        "indicator_order": list(report.get("indicator_order", [])),
        "indicator_labels": dict(report.get("indicator_labels", {})),
        "timeframes": [
            _copy_timeframe_payload(timeframe) for timeframe in report.get("timeframes", [])
        ],
        "generated_at": report.get("generated_at"),
        "source": "strategy_inspector",
    }


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


def normalize_inspector_timeframe(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip().upper()
    if not normalized:
        return None

    timeframe_code = TELEGRAM_TIMEFRAME_ALIASES.get(normalized)
    if timeframe_code is None:
        raise StrategyInspectorError("Periyot 1D, 1W, 2W, 3W veya 1M olmali.")
    return timeframe_code


def _select_report_timeframes(
    report: dict[str, Any],
    timeframe_code: str | None = None,
) -> list[dict[str, Any]]:
    if timeframe_code is None:
        return list(report["timeframes"])

    selected = [
        timeframe for timeframe in report["timeframes"] if timeframe["code"] == timeframe_code
    ]
    if not selected:
        raise StrategyInspectorError(f"Periyot bulunamadi: {timeframe_code}")
    return selected


def _build_indicator_lines(
    strategy: str,
    indicator_order: list[str],
    indicator_values: dict[str, Any],
) -> list[str]:
    groups = TELEGRAM_GROUP_ORDER.get(strategy, (("Veriler", tuple(indicator_order)),))
    rows: list[str] = []

    for group_label, group_indicators in groups:
        parts: list[str] = []
        for indicator_key in group_indicators:
            if indicator_key not in indicator_order:
                continue
            short_label = TELEGRAM_INDICATOR_LABELS.get(indicator_key, indicator_key)
            formatted_value = _format_indicator_value(indicator_values.get(indicator_key))
            parts.append(f"{short_label} {formatted_value}")

        if not parts:
            continue

        rows.append(
            f"<b>{html.escape(group_label)}</b> • "
            + " | ".join(html.escape(part) for part in parts)
        )

    return rows


def _build_telegram_header(
    report: dict[str, Any],
    mode_label: str,
    timeframe_code: str | None = None,
) -> str:
    if timeframe_code:
        timeframe = _select_report_timeframes(report, timeframe_code)[0]
        period_label = timeframe["label"]
    else:
        period_label = "1G / 1Hf / 2Hf / 3Hf / 1Ay"

    return (
        f"🔬 <b>STRATEJI INSPECTOR</b>\n"
        f"<b>{html.escape(report['symbol'])}</b> | "
        f"{html.escape(report['market_type'])} | "
        f"{html.escape(report['strategy'])}\n"
        f"Mod: {html.escape(mode_label)} | Periyot: {html.escape(period_label)}"
    )


def _chunk_telegram_blocks(header: str, blocks: list[str]) -> list[str]:
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


def _build_strategy_summary_chunks(
    report: dict[str, Any],
    timeframe_code: str | None = None,
) -> list[str]:
    header = _build_telegram_header(report, "OZET", timeframe_code)
    blocks: list[str] = []

    for timeframe in _select_report_timeframes(report, timeframe_code):
        title = (
            f"{_signal_emoji(timeframe['signal_status'])} "
            f"<b>{html.escape(timeframe['label'])}</b> | "
            f"<b>{html.escape(timeframe['signal_status'])}</b>"
        )
        if not timeframe["available"]:
            blocks.append(f"{title}\n• Sebep: {html.escape(str(timeframe['reason']))}")
            continue

        block_lines = [
            title,
            (
                f"• Tarih: {html.escape(str(timeframe['date']))} | "
                f"Fiyat {_format_indicator_value(timeframe['price'])} | "
                f"Dip {_format_indicator_value(timeframe['primary_score'])} | "
                f"Tepe {_format_indicator_value(timeframe['secondary_score'])} | "
                f"Aktif {html.escape(str(timeframe['active_indicators']))}"
            ),
        ]

        blocks.append("\n".join(block_lines))

    return _chunk_telegram_blocks(header, blocks)


def _build_strategy_detail_chunks(
    report: dict[str, Any],
    timeframe_code: str | None = None,
) -> list[str]:
    header = _build_telegram_header(report, "DETAY", timeframe_code)
    indicator_order = report["indicator_order"]
    blocks: list[str] = []

    for timeframe in _select_report_timeframes(report, timeframe_code):
        title = (
            f"{_signal_emoji(timeframe['signal_status'])} "
            f"<b>{html.escape(timeframe['label'])}</b> | "
            f"<b>{html.escape(timeframe['signal_status'])}</b>"
        )
        if not timeframe["available"]:
            blocks.append(f"{title}\n• Sebep: {html.escape(str(timeframe['reason']))}")
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

        indicator_lines = _build_indicator_lines(
            strategy=report["strategy"],
            indicator_order=indicator_order,
            indicator_values=timeframe["indicators"],
        )
        blocks.append("\n".join([title, *meta_lines, *indicator_lines]))

    return _chunk_telegram_blocks(header, blocks)


def build_strategy_inspector_chunks(
    report: dict[str, Any],
    detail: bool = False,
    timeframe_code: str | None = None,
) -> list[str]:
    """
    Convert structured inspector data into Telegram-friendly chunks.
    """
    if detail or timeframe_code is not None:
        return _build_strategy_detail_chunks(report, timeframe_code=timeframe_code)
    return _build_strategy_summary_chunks(report, timeframe_code=timeframe_code)
