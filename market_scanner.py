"""
Market Scanner Modülü
Piyasa tarama ve sinyal işleme fonksiyonları.
"""

import time
from typing import Any

import pandas as pd

from ai_analyst import analyze_with_gemini
from ai_schema import AIResponseSchemaError, parse_ai_response
from config import TIMEFRAMES, rate_limits
from data_loader import get_all_binance_symbols, get_all_bist_symbols, resample_data
from database import save_signal as db_save_signal
from database import set_signal_special_tag as db_set_signal_special_tag
from logger import get_logger
from news_manager import fetch_market_news
from price_cache import cached_get_bist_data, cached_get_crypto_data, price_cache
from signals import calculate_combo_signal, calculate_hunter_signal
from strategy_inspector import build_strategy_ai_payload, inspect_strategy_dataframe
from telegram_notify import send_message

logger = get_logger(__name__)


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


def format_ai_message_for_telegram(symbol: str, ai_response: str) -> str:
    """
    AI JSON çıktısını Telegram için okunabilir metne çevirir.
    JSON değilse ham metni korur.
    """
    header = f"🧠 <b>AI KARARI ({symbol}):</b>"

    try:
        payload = parse_ai_response(ai_response)
    except AIResponseSchemaError:
        return f"{header}\n{ai_response}"

    error = payload.error
    if error:
        error_suffix = f" ({payload.error_code})" if payload.error_code else ""
        return f"{header}\n⚠️ AI analizi üretilemedi: {error}{error_suffix}"

    sentiment_label = payload.sentiment_label or "NOTR"
    sentiment_score = payload.sentiment_score
    if isinstance(sentiment_score, float):
        score_text = f"{sentiment_score:.1f}/100"
    elif isinstance(sentiment_score, int):
        score_text = f"{sentiment_score}/100"
    else:
        score_text = "Skor yok"

    upper_label = sentiment_label.upper()
    if "AL" in upper_label:
        sentiment_icon = "🟢"
    elif "SAT" in upper_label:
        sentiment_icon = "🔴"
    else:
        sentiment_icon = "⚪️"

    explanation = payload.explanation or "Detayli aciklama uretilemedi."
    summary_items = payload.summary or ["Ozet maddesi uretilemedi."]
    summary_lines = "\n".join(f"• {item}" for item in summary_items[:3])

    def _short_explanation(text: str, max_sentences: int = 2, max_chars: int = 420) -> str:
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return "Detayli yorum uretilemedi."

        sentences = []
        current = []
        for char in normalized:
            current.append(char)
            if char in ".!?":
                sentence = "".join(current).strip()
                if sentence:
                    sentences.append(sentence)
                current = []
            if len(sentences) >= max_sentences:
                break

        if not sentences and current:
            sentences.append("".join(current).strip())

        compact = " ".join(sentences).strip() or normalized
        if len(compact) > max_chars:
            compact = compact[: max_chars - 3].rstrip() + "..."
        return compact

    def _join_levels(levels: Any) -> str:
        if isinstance(levels, str):
            return levels.strip() or "-"
        if isinstance(levels, list):
            cleaned = [str(level).strip() for level in levels if str(level).strip()]
            return ", ".join(cleaned) if cleaned else "-"
        return "-"

    support_text = _join_levels(payload.key_levels.support)
    resistance_text = _join_levels(payload.key_levels.resistance)
    risk_level = payload.risk_level or "Belirsiz"
    compact_explanation = _short_explanation(explanation)

    meta_lines = [
        f"{sentiment_icon} <b>{sentiment_label}</b>",
        f"• Skor: {score_text}",
        f"• Risk: {risk_level}",
    ]

    level_lines = []
    if support_text != "-":
        level_lines.append(f"• Destek: {support_text}")
    if resistance_text != "-":
        level_lines.append(f"• Direnç: {resistance_text}")

    sections = [
        header,
        "\n".join(meta_lines),
        f"📌 <b>Ozet:</b>\n{summary_lines}",
        f"🧭 <b>Yorum:</b>\n{compact_explanation}",
    ]
    if level_lines:
        sections.append("📍 <b>Seviyeler:</b>\n" + "\n".join(level_lines))

    return "\n\n".join(sections)


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
            df_resampled = resample_data(df_daily.copy(), tf_code)
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
        technical_payload = build_strategy_ai_payload(
            report=get_strategy_report(strategy_name),
            signal_type=signal_dir,
            special_tag=special_tag,
            trigger_rule=trigger_rule,
            matched_timeframes=trigger_rule,
            scenario_name=title_prefix,
        )
        send_message(f"{title_prefix} #{symbol}")
        news_data = fetch_market_news(symbol, market_type)
        ai_msg = analyze_with_gemini(
            symbol=symbol,
            scenario_name=title_prefix,
            signal_type=signal_dir,
            technical_data=technical_payload,
            news_context=news_data,
        )
        send_message(format_ai_message_for_telegram(symbol, ai_msg))

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
            df = cached_get_bist_data(sym, start_date="01-01-2015")
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
