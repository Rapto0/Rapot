"""
Market Scanner Modülü
Piyasa tarama ve sinyal işleme fonksiyonları.
"""

import html
import textwrap
import time
import unicodedata
from typing import Any

import pandas as pd

from ai_analyst import analyze_with_gemini
from ai_schema import AIResponseSchemaError, parse_ai_response
from config import TIMEFRAMES, rate_limits, signal_guard_settings
from data_loader import (
    get_all_binance_symbols,
    get_all_bist_symbols,
    get_bist_data,
    get_bist_data_secondary,
    get_dataframe_age_seconds,
    is_dataframe_fresh,
    resample_market_data,
)
from database import save_signal as db_save_signal
from database import set_signal_special_tag as db_set_signal_special_tag
from logger import get_logger
from news_manager import fetch_market_news
from price_cache import cached_get_crypto_data, price_cache
from signals import calculate_combo_signal, calculate_hunter_signal
from strategy_inspector import build_strategy_ai_payload, inspect_strategy_dataframe
from telegram_notify import send_message

logger = get_logger(__name__)


SPECIAL_TAG_DISPLAY: dict[str, tuple[str, str]] = {
    "BELES": ("BELEŞ", "Tarihi Fırsat"),
    "COK_UCUZ": ("ÇOK UCUZ", "Dip Bölgesi"),
    "PAHALI": ("PAHALI", "Tepe Bölgesi"),
    "FAHIS_FIYAT": ("FAHİŞ FİYAT", "Aşırı Tepe"),
}

SPECIAL_TAG_TARGET_TIMEFRAME = {
    "COK_UCUZ": "3W-FRI",
    "BELES": "ME",
    "PAHALI": "W-FRI",
    "FAHIS_FIYAT": "ME",
}

TIMEFRAME_DISPLAY_LABELS = {
    "1D": "1 Günlük",
    "W-FRI": "1 Haftalık",
    "2W-FRI": "2 Haftalık",
    "3W-FRI": "3 Haftalık",
    "ME": "1 Aylık",
}

NEUTRAL_TOKEN_DISPLAY = {
    "VALUE_COMPRESSION_EXTREME_BUY": "BELEŞ",
    "VALUE_COMPRESSION_BUY": "ÇOK UCUZ",
    "VALUE_EXTENSION_SELL": "PAHALI",
    "VALUE_EXTENSION_EXTREME_SELL": "FAHİŞ FİYAT",
    "LONG_BIAS": "AL",
    "SHORT_BIAS": "SAT",
    "RSI_Fast": "Hızlı RSI",
    "TopScore": "Tepe Skoru",
    "DipScore": "Dip Skoru",
}


class ScannerState:
    """
    Thread-safe tarama durumu yönetimi.
    Global değişkenler yerine class içinde durum tutar.
    """

    def __init__(self):
        self._scan_count = 0
        self._signal_count = 0
        import threading

        self._lock = threading.Lock()

    @property
    def scan_count(self) -> int:
        """Toplam tarama sayısını döndürür."""
        with self._lock:
            return self._scan_count

    @property
    def signal_count(self) -> int:
        """Üretilen sinyal sayısını döndürür."""
        with self._lock:
            return self._signal_count

    def increment_scan(self) -> int:
        """Tarama sayacını artırır ve yeni değeri döndürür."""
        with self._lock:
            self._scan_count += 1
            return self._scan_count

    def increment_signal(self) -> int:
        """Sinyal sayacını artırır ve yeni değeri döndürür."""
        with self._lock:
            self._signal_count += 1
            return self._signal_count


# Singleton instance
_scanner_state = ScannerState()


def get_scan_count() -> int:
    """Toplam tarama sayısını döndürür."""
    return _scanner_state.scan_count


def get_signal_count() -> int:
    """Üretilen sinyal sayısını döndürür."""
    return _scanner_state.signal_count


def increment_scan_count() -> int:
    """Tarama sayacını artırır."""
    return _scanner_state.increment_scan()


def increment_signal_count() -> int:
    """Sinyal sayacını artırır."""
    return _scanner_state.increment_signal()


def format_combo_debug(d: dict[str, Any]) -> str:
    """
    COMBO stratejisi debug raporu formatlar.

    Args:
        d: İndikator değerlerini iceren sozluk (MACD, RSI, WR, CCI vb.)

    Returns:
        Formatlanmıs rapor metni
    """

    def fmt(val, decimals=2):
        """Güvenli float formatlama."""
        try:
            return f"{float(val):.{decimals}f}"
        except (ValueError, TypeError):
            return str(val)

    return (
        f"📊 --- COMBO RAPORU ---\n"
        f"📅 Tarih: {d.get('DATE', 'Yok')} | Fiyat: {d.get('PRICE', 'Yok')}\n"
        f"-----------------------------\n"
        f"1. MACD: {fmt(d.get('MACD', 0), 4)}\n"
        f"2. RSI (14): {fmt(d.get('RSI', 0))}\n"
        f"3. W%R: {fmt(d.get('WR', 0))}\n"
        f"4. CCI (20): {fmt(d.get('CCI', 0))}\n"
        f"-----------------------------"
    )


def format_hunter_debug(d: dict[str, Any]) -> str:
    """
    HUNTER stratejisi debug raporu formatlar.

    Args:
        d: 15 indikator degerini iceren sozluk

    Returns:
        Formatlanmıs rapor metni
    """
    return (
        f"📊 --- HUNTER RAPORU ---\n"
        f"📅 Tarih: {d.get('DATE', 'Yok')} | Fiyat: {d.get('PRICE', 'Yok')}\n"
        f"-----------------------------\n"
        f"1.  RSI (14): {d.get('RSI', 'N/A')}\n"
        f"2.  RSI Fast: {d.get('RSI_Fast', 'N/A')}\n"
        f"3.  CMO: {d.get('CMO', 'N/A')}\n"
        f"4.  BOP: {d.get('BOP', 'N/A')}\n"
        f"5.  MACD %: {d.get('MACD', 'N/A')}\n"
        f"6.  W%R: {d.get('W%R', 'N/A')}\n"
        f"7.  CCI: {d.get('CCI', 'N/A')}\n"
        f"8.  ULT: {d.get('ULT', 'N/A')}\n"
        f"9.  %B (Boll): {d.get('BBP', 'N/A')}\n"
        f"10. ROC: {d.get('ROC', 'N/A')}\n"
        f"11. DeM: {d.get('DeM', 'N/A')}\n"
        f"12. PSY: {d.get('PSY', 'N/A')}\n"
        f"13. Z-Score: {d.get('ZScore', 'N/A')}\n"
        f"14. Keltner %B: {d.get('KeltPB', 'N/A')}\n"
        f"15. RSI(2): {d.get('RSI2', 'N/A')}\n"
        f"-----------------------------"
    )


def generate_manual_report(
    symbol: str, market_type: str, combo_res: dict[str, Any], hunter_res: dict[str, Any]
) -> str:
    """
    Manuel analiz icin detayli rapor olusturur.

    Args:
        symbol: Hisse veya kripto sembolu (orn: THYAO, BTCUSDT)
        market_type: Piyasa turu (BIST veya KRIPTO)
        combo_res: COMBO stratejisi sonuclari
        hunter_res: HUNTER stratejisi sonuclari

    Returns:
        Telegram'a gonderilecek HTML formatli rapor
    """
    # Null-check: eksik veri durumu
    if not combo_res or not hunter_res:
        return f"⚠️ {symbol} için analiz verisi eksik."

    cd = combo_res.get("details", {})
    hd = hunter_res.get("details", {})
    c_signal = (
        "🟢 AL" if combo_res.get("buy") else ("🔴 SAT" if combo_res.get("sell") else "⚪️ NÖTR")
    )
    h_signal = (
        "🟢 DİP" if hunter_res.get("buy") else ("🔴 TEPE" if hunter_res.get("sell") else "⚪️ NÖTR")
    )

    msg = (
        f"🔎 <b>DETAYLI ANALİZ RAPORU: #{symbol}</b>\n"
        f"Piyasa: {market_type} | Periyot: GÜNLÜK\n"
        f"Fiyat: {cd.get('PRICE', 'N/A')}\n"
        f"-----------------------------------\n"
        f"🎯 <b>GENEL DURUM</b>\n"
        f"• Combo Sinyali: <b>{c_signal}</b> ({cd.get('Score', 'N/A')})\n"
        f"• Hunter Sinyali: <b>{h_signal}</b> (Dip: {hd.get('DipScore', 'N/A')} - Tepe: {hd.get('TopScore', 'N/A')})\n"
        f"-----------------------------------\n"
        f"📈 <b>TEMEL İNDİKATÖRLER</b>\n"
        f"• RSI (14): {cd.get('RSI', 'N/A')}\n"
        f"• MACD: {cd.get('MACD', 'N/A')}\n"
    )
    return msg


def _replace_internal_ai_tokens(text: str) -> str:
    normalized = str(text or "")
    for raw, clean in NEUTRAL_TOKEN_DISPLAY.items():
        normalized = normalized.replace(raw, clean)
        normalized = normalized.replace(f"'{raw}'", clean)
        normalized = normalized.replace(f'"{raw}"', clean)
    return " ".join(normalized.split())


def _fold_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    ascii_like = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return ascii_like.lower()


def _parse_fraction_score(score_value: Any) -> tuple[str, str, int] | None:
    if score_value is None:
        return None
    text = str(score_value).strip()
    if "/" not in text:
        return None
    left, right = text.split("/", 1)
    try:
        numerator = float(left.strip())
        denominator = float(right.strip())
    except ValueError:
        return None
    if denominator <= 0:
        return None
    percentage = max(0, min(100, int(round((numerator / denominator) * 100))))
    if numerator.is_integer() and denominator.is_integer():
        return str(int(numerator)), str(int(denominator)), percentage
    return f"{numerator:g}", f"{denominator:g}", percentage


def _display_sentiment_label(label: str | None) -> str:
    upper = str(label or "NOTR").upper()
    mapping = {
        "AL": "AL",
        "GUCLU AL": "GÜÇLÜ AL",
        "SAT": "SAT",
        "GUCLU SAT": "GÜÇLÜ SAT",
        "NOTR": "NÖTR",
    }
    return mapping.get(upper, upper.replace("_", " "))


def _display_risk_level(level: str | None) -> str:
    upper = str(level or "Belirsiz").upper()
    mapping = {
        "DUSUK": "Düşük",
        "ORTA": "Orta",
        "YUKSEK": "Yüksek",
        "BELIRSIZ": "Belirsiz",
    }
    return mapping.get(upper, str(level or "Belirsiz"))


def _signal_meta(
    strategy_name: str | None,
    signal_dir: str | None,
    special_tag: str | None,
    report: dict[str, Any] | None,
    payload: Any,
) -> dict[str, str]:
    display_name, display_hint = SPECIAL_TAG_DISPLAY.get(
        str(special_tag or "").upper(),
        (str(special_tag or strategy_name or "BILINMIYOR"), "Standart Kurgu"),
    )

    upper_signal = str(signal_dir or payload.sentiment_label or "NOTR").upper()
    if upper_signal == "AL":
        direction_label = "\U0001f7e2 AL"
    elif upper_signal == "SAT":
        direction_label = "\U0001f534 SAT"
    else:
        direction_label = "\u26aa NÖTR"

    return {
        "display_name": display_name,
        "display_hint": display_hint,
        "direction_label": direction_label,
    }


def _format_explanatory_score(score_value: Any) -> str:
    parsed_score = _parse_fraction_score(score_value)
    if parsed_score:
        actual_score, threshold_score, _ = parsed_score
        return f"{actual_score} puan / {threshold_score} eşik"
    return str(score_value)


def _build_trigger_score_lines(
    report: dict[str, Any] | None,
    signal_dir: str | None,
    trigger_rule: list[str] | None,
    payload: Any,
) -> list[str]:
    if not report or not trigger_rule:
        return [f"AI Güveni: {int(payload.sentiment_score or 50)} / 100"]

    timeframes = {item.get("code"): item for item in report.get("timeframes", [])}
    score_key = "secondary_score" if str(signal_dir or "").upper() == "SAT" else "primary_score"
    lines: list[str] = []

    for timeframe_code in trigger_rule:
        timeframe = timeframes.get(timeframe_code)
        if not timeframe:
            continue
        score_value = timeframe.get(score_key)
        if score_value in (None, ""):
            continue
        label = TIMEFRAME_DISPLAY_LABELS.get(timeframe_code, timeframe_code)
        lines.append(f"{label}: {_format_explanatory_score(score_value)}")

    return lines or [f"AI Güveni: {int(payload.sentiment_score or 50)} / 100"]


def _wrap_box_text(text: str, width: int = 46, max_lines: int = 10) -> list[str]:
    cleaned = _replace_internal_ai_tokens(text)
    wrapped = textwrap.wrap(cleaned, width=width, break_long_words=False, break_on_hyphens=False)
    if not wrapped:
        return ["Detaylı yorum üretilemedi."]
    return wrapped[:max_lines]


def _extract_primary_comment(text: str) -> str:
    normalized = _replace_internal_ai_tokens(text)
    compact = " ".join(normalized.split()).strip()
    if not compact:
        return "Detaylı yorum üretilemedi."

    for separator in [". ", ".\n", "! ", "!\n", "? ", "?\n"]:
        if separator in compact:
            sentence = compact.split(separator, 1)[0].strip()
            if sentence:
                return sentence.rstrip(".!?") + "."

    return compact


def _shorten_summary_item(text: str, max_chars: int = 220) -> str:
    normalized = _replace_internal_ai_tokens(text)
    compact = " ".join(normalized.split())
    if len(compact) <= max_chars:
        if compact and compact[-1] not in ".!?":
            compact += "."
        return compact
    compact = compact[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:")
    if compact and compact[-1] not in ".!?":
        compact += "."
    return compact


def _classify_summary_item(text: str) -> str:
    lowered = _fold_text(text)
    if any(
        token in lowered
        for token in [
            "haber",
            "akisi",
            "news",
            "kap",
            "tedbir",
            "aciklama",
            "gozalti",
            "operasyon",
            "sermaye",
            "regulasyon",
        ]
    ):
        return "news"
    return "general"


def _build_news_lines(summary_items: list[str]) -> str:
    picked: list[str] = []
    used_texts: set[str] = set()

    for item in summary_items:
        if _classify_summary_item(item) != "news":
            continue
        normalized = _replace_internal_ai_tokens(item)
        normalized = " ".join(normalized.split()).strip()
        lowered = _fold_text(normalized)
        if "haber" in lowered and (
            "yok" in lowered
            or "mevcut degil" in lowered
            or "bulunmam" in lowered
            or "gelisme bulunm" in lowered
        ):
            normalized = "Haber teyidi yok; analiz teknik veriye dayanıyor."
        else:
            normalized = _shorten_summary_item(normalized, max_chars=220)
        text_key = normalized.lower()
        if text_key in used_texts:
            continue
        picked.append(normalized)
        used_texts.add(text_key)
        if len(picked) >= 2:
            break

    if not picked:
        picked = ["Haber teyidi yok; analiz teknik veriye dayanıyor."]

    return "\n".join(f"• {html.escape(item)}" for item in picked[:2])


def _build_level_block(levels: list[str], prefix: str) -> str | None:
    cleaned = [str(level).strip() for level in levels if str(level).strip()]
    if not cleaned:
        return None
    return f"{prefix}{' | '.join(cleaned)}"


def _format_level_value(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    if value >= 100:
        return f"{value:.2f}"
    if value >= 1:
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _select_recent_levels(values: list[float], *, reverse: bool) -> list[str]:
    ordered = sorted(values, reverse=reverse)
    selected: list[str] = []
    seen_keys: set[float] = set()
    for value in ordered:
        rounded_key = round(value, 4)
        if rounded_key in seen_keys:
            continue
        selected.append(_format_level_value(value))
        seen_keys.add(rounded_key)
        if len(selected) >= 2:
            break
    return selected


def _derive_technical_levels(
    df_daily: pd.DataFrame | None, special_tag: str | None, market_type: str
) -> dict[str, list[str]]:
    if df_daily is None or df_daily.empty or "Close" not in df_daily.columns:
        return {"support": [], "resistance": []}

    current_price = float(df_daily["Close"].iloc[-1])
    support_candidates: list[float] = []
    resistance_candidates: list[float] = []

    for timeframe_code in ("W-FRI", "ME"):
        df_source = resample_market_data(df_daily.copy(), timeframe_code, market_type)
        if (
            df_source is None
            or df_source.empty
            or len(df_source) < 2
            or not {"Open", "Close"}.issubset(df_source.columns)
        ):
            continue

        recent = df_source.tail(16)
        for column in ("Open", "Close"):
            for value in recent[column].dropna().tolist():
                numeric = float(value)
                if numeric < current_price:
                    support_candidates.append(numeric)
                elif numeric > current_price:
                    resistance_candidates.append(numeric)

    return {
        "support": _select_recent_levels(support_candidates, reverse=True),
        "resistance": _select_recent_levels(resistance_candidates, reverse=False),
    }


def _strategy_matches_direction(
    strategy_name: str,
    df_resampled: pd.DataFrame,
    timeframe_code: str,
    signal_dir: str,
) -> bool:
    normalized_strategy = str(strategy_name or "").upper()
    normalized_dir = str(signal_dir or "").upper()

    if normalized_strategy == "COMBO":
        result = calculate_combo_signal(df_resampled, timeframe_code)
    elif normalized_strategy == "HUNTER":
        result = calculate_hunter_signal(df_resampled, timeframe_code)
    else:
        return False

    if not result:
        return False
    if normalized_dir == "AL":
        return bool(result.get("buy"))
    if normalized_dir == "SAT":
        return bool(result.get("sell"))
    return False


def _verify_bist_second_source(
    symbol: str,
    strategy_name: str,
    signal_dir: str,
    trigger_rule: list[str],
    secondary_df: pd.DataFrame | None,
) -> tuple[bool, str]:
    if secondary_df is None or secondary_df.empty:
        return False, "ikincil_kaynak_bos"

    if not is_dataframe_fresh(secondary_df, signal_guard_settings.BIST_MAX_DATA_AGE_SECONDS):
        age = get_dataframe_age_seconds(secondary_df)
        if age is None:
            return False, "ikincil_kaynak_tarihsiz"
        return False, f"ikincil_kaynak_bayat ({age:.1f}s)"

    for timeframe_code in trigger_rule:
        df_resampled = resample_market_data(secondary_df.copy(), timeframe_code, "BIST")
        if df_resampled is None or len(df_resampled) < 20:
            return False, f"ikincil_{timeframe_code}_veri_yetersiz"
        if not _strategy_matches_direction(strategy_name, df_resampled, timeframe_code, signal_dir):
            return False, f"ikincil_{timeframe_code}_uyumsuz"

    return True, "ok"


def _resolve_levels_heading(has_support: bool, has_resistance: bool) -> str:
    if has_support and has_resistance:
        return "<b>\U0001f4cd KRİTİK SEVİYELER</b>"
    if has_support:
        return "<b>\U0001f4cd DESTEK BÖLGESİ</b>"
    return "<b>\U0001f4cd DİRENÇ BÖLGESİ</b>"


def _build_risk_note(header: str, payload: Any) -> str:
    reason = str(payload.error or "AI analizi üretilemedi.").strip()
    error_code = str(payload.error_code or "").strip().lower()
    if reason.lower() in {"", "null", "none", "nan"}:
        reason = "Model geçerli bir yanıt döndürmedi."
    if error_code in {"invalid_json", "empty_response", "schema_validation"}:
        reason = "Model geçerli bir yanıt döndürmedi."
    return (
        f"{header}\n"
        f"\u26a0\ufe0f AI analizi şu anda üretilemedi.\n"
        f"Neden: {html.escape(reason)}"
    )


def format_ai_message_for_telegram(
    symbol: str,
    ai_response: str,
    *,
    strategy_name: str | None = None,
    signal_dir: str | None = None,
    special_tag: str | None = None,
    report: dict[str, Any] | None = None,
    technical_levels: dict[str, list[str]] | None = None,
    trigger_rule: list[str] | None = None,
) -> str:
    """
    AI JSON ciktisini Telegram icin okunabilir ve hiyerarsik metne cevirir.
    JSON degilse ham metni korur.
    """
    safe_symbol = html.escape(str(symbol))
    header = f"\U0001f9e0 <b>AI KARARI ({safe_symbol}):</b>"

    try:
        payload = parse_ai_response(ai_response)
    except AIResponseSchemaError:
        return f"{header}\n{html.escape(str(ai_response))}"

    if payload.error or payload.error_code:
        return _build_risk_note(header, payload)

    sentiment_label = payload.sentiment_label or "NOTR"
    upper_label = sentiment_label.upper()
    if "AL" in upper_label:
        sentiment_icon = "\U0001f7e2"
    elif "SAT" in upper_label:
        sentiment_icon = "\U0001f534"
    else:
        sentiment_icon = "\u26aa"

    sentiment_display = _display_sentiment_label(sentiment_label)
    explanation = _replace_internal_ai_tokens(
        payload.explanation or "Detaylı açıklama üretilemedi."
    )
    summary_items = payload.summary or []
    risk_level = _display_risk_level(payload.risk_level or "Belirsiz")

    signal_meta = _signal_meta(strategy_name, signal_dir, special_tag, report, payload)
    score_lines = _build_trigger_score_lines(report, signal_dir, trigger_rule, payload)
    primary_comment = _extract_primary_comment(explanation)
    box_lines = _wrap_box_text(primary_comment)
    summary_lines = _build_news_lines(summary_items)

    level_source = technical_levels or {}
    support_line = _build_level_block(
        list(level_source.get("support", [])),
        "│ 🟢 Destek  : ",
    )
    resistance_line = _build_level_block(
        list(level_source.get("resistance", [])),
        "│ 🔴 Direnç  : ",
    )
    has_support = bool(support_line)
    has_resistance = bool(resistance_line)

    sections = [
        header,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "<b>📊 TEKNİK DURUM</b>",
        f"├─ Strateji: {html.escape(signal_meta['display_name'])} ({html.escape(signal_meta['display_hint'])})",
        f"├─ Yön: {html.escape(signal_meta['direction_label'])}",
    ]

    if len(score_lines) == 1:
        sections.append(f"└─ Skor: {html.escape(score_lines[0])}")
    else:
        sections.append("├─ Koşul Skorları:")
        for index, score_line in enumerate(score_lines):
            branch = "└─" if index == len(score_lines) - 1 else "├─"
            sections.append(f"{branch} {html.escape(score_line)}")

    sections.extend(
        [
            "",
            "<b>🧠 AI ANALİZİ</b>",
            "┌─────────────────────────────",
            f"│ {sentiment_icon} <b>{html.escape(str(sentiment_display))}</b> • Risk: {html.escape(str(risk_level))}",
            "│",
            *[f"│ {html.escape(line)}" for line in box_lines],
            "└─────────────────────────────",
            "",
            "<b>📌 ÖNE ÇIKANLAR</b>",
            summary_lines,
        ]
    )

    if has_support or has_resistance:
        sections.extend(
            [
                "",
                _resolve_levels_heading(has_support, has_resistance),
                "┌─────────────────────────────",
            ]
        )
        if support_line:
            sections.append(html.escape(support_line))
        if resistance_line:
            sections.append(html.escape(resistance_line))
        sections.append("└─────────────────────────────")

    return "\n".join(sections)


def process_symbol(
    df_daily: pd.DataFrame | None, symbol: str, market_type: str, check_commands_callback=None
) -> None:
    """
    Tek bir sembol icin tum timeframe'lerde sinyal analizi yapar.

    COMBO ve HUNTER stratejilerini 5 farkli zaman diliminde calistirir.
    Ozel sinyal kombinasyonlari tespit edilirse AI analizi tetikler.

    Args:
        df_daily: Gunluk OHLCV verisi iceren DataFrame
        symbol: Hisse veya kripto sembolu
        market_type: Piyasa turu (BIST veya Kripto)
        check_commands_callback: Komut kontrol fonksiyonu (opsiyonel)
    """
    if df_daily is None or df_daily.empty:
        return

    combo_hits = {"buy": {}, "sell": {}}
    hunter_hits = {"buy": {}, "sell": {}}
    strategy_reports: dict[str, dict[str, Any]] = {}

    for tf_code, tf_label in TIMEFRAMES:
        try:
            df_resampled = resample_market_data(df_daily.copy(), tf_code, market_type)
            if df_resampled is None or len(df_resampled) < 20:
                continue

            # --- COMBO ---
            res_combo = calculate_combo_signal(df_resampled, tf_code)
            if res_combo:
                if res_combo["buy"]:
                    combo_hits["buy"][tf_code] = res_combo["details"]
                    print(f">>> COMBO AL: {symbol} {tf_label}")
                    # Veritabanına kaydet
                    db_save_signal(
                        symbol=symbol,
                        market_type=market_type,
                        strategy="COMBO",
                        signal_type="AL",
                        timeframe=tf_code,
                        score=str(res_combo["details"]["Score"]),
                        price=res_combo["details"].get("PRICE", 0),
                    )
                    increment_signal_count()

                if res_combo["sell"]:
                    combo_hits["sell"][tf_code] = res_combo["details"]
                    # SAT sinyalini de veritabanına kaydet
                    db_save_signal(
                        symbol=symbol,
                        market_type=market_type,
                        strategy="COMBO",
                        signal_type="SAT",
                        timeframe=tf_code,
                        score=str(res_combo["details"]["Score"]),
                        price=res_combo["details"].get("PRICE", 0),
                    )
                    increment_signal_count()

            # --- HUNTER ---
            res_hunter = calculate_hunter_signal(df_resampled, tf_code)
            if res_hunter:
                if res_hunter["buy"]:
                    hunter_hits["buy"][tf_code] = res_hunter["details"]
                    print(f">>> HUNTER DİP: {symbol} {tf_label}")
                    # Veritabanına kaydet
                    db_save_signal(
                        symbol=symbol,
                        market_type=market_type,
                        strategy="HUNTER",
                        signal_type="AL",
                        timeframe=tf_code,
                        score=str(res_hunter["details"]["DipScore"]),
                        price=res_hunter["details"].get("PRICE", 0),
                    )
                    increment_signal_count()

                if res_hunter["sell"]:
                    hunter_hits["sell"][tf_code] = res_hunter["details"]
                    # SAT sinyalini de veritabanına kaydet
                    db_save_signal(
                        symbol=symbol,
                        market_type=market_type,
                        strategy="HUNTER",
                        signal_type="SAT",
                        timeframe=tf_code,
                        score=str(res_hunter["details"]["TopScore"]),
                        price=res_hunter["details"].get("PRICE", 0),
                    )
                    increment_signal_count()

        except Exception as e:
            logger.error(f"HATA: {symbol} - {tf_label}: {str(e)}")

    # --- ÖZEL SİNYALLER & YAPAY ZEKA ANALİZİ ---
    secondary_df_cache: pd.DataFrame | None = None
    secondary_df_loaded = False

    def get_secondary_df() -> pd.DataFrame | None:
        nonlocal secondary_df_cache, secondary_df_loaded
        if secondary_df_loaded:
            return secondary_df_cache
        secondary_df_loaded = True
        secondary_df_cache = get_bist_data_secondary(symbol, start_date="01-01-2015")
        return secondary_df_cache

    def get_strategy_report(strategy_name: str) -> dict[str, Any]:
        if strategy_name not in strategy_reports:
            strategy_reports[strategy_name] = inspect_strategy_dataframe(
                df_daily=df_daily.copy(),
                symbol=symbol,
                market_type=market_type,
                strategy=strategy_name,
            )
        return strategy_reports[strategy_name]

    def trigger_ai_analysis(
        title_prefix: str,
        strategy_name: str,
        signal_dir: str,
        special_tag: str,
        trigger_rule: list[str],
    ) -> None:
        if (
            market_type == "BIST"
            and signal_guard_settings.BIST_REQUIRE_SECOND_SOURCE_CONFIRMATION
        ):
            ok, reason = _verify_bist_second_source(
                symbol=symbol,
                strategy_name=strategy_name,
                signal_dir=signal_dir,
                trigger_rule=trigger_rule,
                secondary_df=get_secondary_df(),
            )
            if not ok:
                logger.warning(
                    "Ikinci kaynak dogrulamasi basarisiz (%s %s %s): %s",
                    symbol,
                    strategy_name,
                    special_tag,
                    reason,
                )
                return

        logger.info(
            "Ozel sinyal tetiklendi: %s %s %s %s",
            symbol,
            strategy_name,
            special_tag,
            ",".join(trigger_rule),
        )
        technical_payload = build_strategy_ai_payload(
            report=get_strategy_report(strategy_name),
            signal_type=signal_dir,
            special_tag=special_tag,
            trigger_rule=trigger_rule,
            matched_timeframes=trigger_rule,
            scenario_name=title_prefix,
        )
        title_message = f"{title_prefix} #{symbol}"
        if not send_message(title_message):
            logger.error("Ozel sinyal baslik mesaji gonderilemedi: %s", title_message)
        news_data = fetch_market_news(symbol, market_type)
        ai_msg = analyze_with_gemini(
            symbol=symbol,
            scenario_name=title_prefix,
            signal_type=signal_dir,
            technical_data=technical_payload,
            news_context=news_data,
        )
        final_message = format_ai_message_for_telegram(
            symbol,
            ai_msg,
            strategy_name=strategy_name,
            signal_dir=signal_dir,
            special_tag=special_tag,
            report=get_strategy_report(strategy_name),
            technical_levels=_derive_technical_levels(df_daily, special_tag, market_type),
            trigger_rule=trigger_rule,
        )
        if not send_message(final_message):
            logger.error("Ozel sinyal AI mesaji gonderilemedi: %s %s", symbol, special_tag)

    def mark_special_signal(
        strategy_name: str, signal_dir: str, special_tag: str, timeframe: str
    ) -> None:
        try:
            tagged = db_set_signal_special_tag(
                symbol=symbol,
                market_type=market_type,
                strategy=strategy_name,
                signal_type=signal_dir,
                timeframe=timeframe,
                special_tag=special_tag,
                within_seconds=0,
            )
            if not tagged:
                logger.warning(
                    f"Ozel sinyal etiketi yazilamadi: {symbol} {strategy_name} {special_tag} ({timeframe})"
                )
        except Exception as exc:
            logger.error(
                f"Ozel sinyal etiketi kaydedilemedi ({symbol} {strategy_name} {special_tag}): {exc}"
            )

    # ÇOK UCUZ
    if "1D" in combo_hits["buy"] and "W-FRI" in combo_hits["buy"] and "3W-FRI" in combo_hits["buy"]:
        mark_special_signal("COMBO", "AL", "COK_UCUZ", "3W-FRI")
        trigger_ai_analysis(
            "🔥🔥 COMBO: ÇOK UCUZ!",
            "COMBO",
            "AL",
            "COK_UCUZ",
            ["1D", "W-FRI", "3W-FRI"],
        )

    if (
        "1D" in hunter_hits["buy"]
        and "W-FRI" in hunter_hits["buy"]
        and "3W-FRI" in hunter_hits["buy"]
    ):
        mark_special_signal("HUNTER", "AL", "COK_UCUZ", "3W-FRI")
        trigger_ai_analysis(
            "🔥🔥 HUNTER: ÇOK UCUZ!",
            "HUNTER",
            "AL",
            "COK_UCUZ",
            ["1D", "W-FRI", "3W-FRI"],
        )

    # BELEŞ
    if "1D" in combo_hits["buy"] and "2W-FRI" in combo_hits["buy"] and "ME" in combo_hits["buy"]:
        mark_special_signal("COMBO", "AL", "BELES", "ME")
        trigger_ai_analysis(
            "💎💎💎 COMBO: BELEŞ (TARİHİ FIRSAT)!",
            "COMBO",
            "AL",
            "BELES",
            ["1D", "2W-FRI", "ME"],
        )

    if "1D" in hunter_hits["buy"] and "2W-FRI" in hunter_hits["buy"] and "ME" in hunter_hits["buy"]:
        mark_special_signal("HUNTER", "AL", "BELES", "ME")
        trigger_ai_analysis(
            "💎💎💎 HUNTER: BELEŞ (TARİHİ FIRSAT)!",
            "HUNTER",
            "AL",
            "BELES",
            ["1D", "2W-FRI", "ME"],
        )

    # PAHALI
    if "1D" in combo_hits["sell"] and "W-FRI" in combo_hits["sell"]:
        mark_special_signal("COMBO", "SAT", "PAHALI", "W-FRI")
        trigger_ai_analysis(
            "⚠️⚠️ COMBO: PAHALI!",
            "COMBO",
            "SAT",
            "PAHALI",
            ["1D", "W-FRI"],
        )

    if "1D" in hunter_hits["sell"] and "W-FRI" in hunter_hits["sell"]:
        mark_special_signal("HUNTER", "SAT", "PAHALI", "W-FRI")
        trigger_ai_analysis(
            "⚠️⚠️ HUNTER: PAHALI!",
            "HUNTER",
            "SAT",
            "PAHALI",
            ["1D", "W-FRI"],
        )

    # FAHİŞ FİYAT
    if "1D" in combo_hits["sell"] and "W-FRI" in combo_hits["sell"] and "ME" in combo_hits["sell"]:
        mark_special_signal("COMBO", "SAT", "FAHIS_FIYAT", "ME")
        trigger_ai_analysis(
            "🚨🚨🚨 COMBO: FAHİŞ FİYAT!",
            "COMBO",
            "SAT",
            "FAHIS_FIYAT",
            ["1D", "W-FRI", "ME"],
        )

    if (
        "1D" in hunter_hits["sell"]
        and "W-FRI" in hunter_hits["sell"]
        and "ME" in hunter_hits["sell"]
    ):
        mark_special_signal("HUNTER", "SAT", "FAHIS_FIYAT", "ME")
        trigger_ai_analysis(
            "🚨🚨🚨 HUNTER: FAHİŞ FİYAT!",
            "HUNTER",
            "SAT",
            "FAHIS_FIYAT",
            ["1D", "W-FRI", "ME"],
        )


def scan_market(check_commands_callback=None) -> None:
    """
    Tum BIST ve Kripto piyasalarini tarar.

    468 BIST hissesi ve tum Binance USDT ciftlerini sirayla analiz eder.
    Her 10 sembolde bir kullanici komutlarini kontrol eder.
    Rate limiting ile API limitlerini asmayi onler.

    Args:
        check_commands_callback: Komut kontrol fonksiyonu (opsiyonel)
    """
    increment_scan_count()
    scan_num = get_scan_count()
    logger.info(f"Tarama #{scan_num} başladı")
    print(f"\n--- Tarama Başladı: {time.strftime('%H:%M:%S')} ---")

    # BIST Tarama
    symbols = get_all_bist_symbols()
    logger.info(f"BIST taranıyor: {len(symbols)} hisse")
    print(f"🏢 BIST Taranıyor ({len(symbols)} hisse)...")

    for i, sym in enumerate(symbols):
        print(f"\rBIST: {i + 1}/{len(symbols)} {sym}", end="")
        try:
            # Trade-time BIST akisinda cache bypass: her turde kaynaktan taze veri cek.
            df = get_bist_data(sym, start_date="01-01-2015")
            if not is_dataframe_fresh(df, signal_guard_settings.BIST_MAX_DATA_AGE_SECONDS):
                age = get_dataframe_age_seconds(df)
                if age is None:
                    logger.warning(f"BIST veri tazelik bilgisi yok, atlandi: {sym}")
                else:
                    logger.warning(
                        f"BIST veri bayat ({age:.1f}s > {signal_guard_settings.BIST_MAX_DATA_AGE_SECONDS}s), atlandi: {sym}"
                    )
                continue
            process_symbol(df, sym, "BIST")
        except Exception as e:
            logger.error(f"VERİ ÇEKME HATASI (BIST): {sym} - {str(e)}")

        if i % 10 == 0 and check_commands_callback:
            check_commands_callback()
        time.sleep(rate_limits.BIST_DELAY)

    # Kripto Tarama
    crypto_syms = get_all_binance_symbols()
    print(f"\n\n₿ Kripto Taranıyor ({len(crypto_syms)} çift)...")

    for i, sym in enumerate(crypto_syms):
        print(f"\rKripto: {i + 1}/{len(crypto_syms)} {sym}", end="")
        try:
            df = cached_get_crypto_data(sym)
            process_symbol(df, sym, "Kripto")
        except Exception as e:
            logger.error(f"VERİ ÇEKME HATASI (KRIPTO): {sym} - {str(e)}")

        if i % 10 == 0 and check_commands_callback:
            check_commands_callback()
        time.sleep(rate_limits.CRYPTO_DELAY)

    # Süresi dolmuş cache temizle
    price_cache.clear_expired()

    # Cache istatistikleri logla
    cache_stats = price_cache.get_stats()
    logger.info(f"Cache: {cache_stats['session_hits']} hit, {cache_stats['session_misses']} miss")

    logger.info(f"Tarama #{scan_num} tamamlandı")
    print("\n✅ Tarama Bitti.")
    send_message("✅ Tüm periyotlar tarandı. Yeni tarama 4 saat sonra.")
