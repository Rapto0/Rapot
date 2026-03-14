"""
Async Market Scanner Modülü
Paralel piyasa tarama ve sinyal işleme.
"""

import asyncio
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from async_data_loader import (
    fetch_multiple_bist_async,
    fetch_multiple_crypto_async,
    get_all_binance_symbols_async,
)
from config import TIMEFRAMES
from data_loader import get_all_bist_symbols, resample_market_data
from database import save_signal as db_save_signal
from logger import get_logger
from signals import calculate_combo_signal, calculate_hunter_signal
from telegram_notify import send_message

logger = get_logger(__name__)


class AsyncScannerState:
    """Async scanner durum yönetimi."""

    def __init__(self):
        self._scan_count = 0
        self._signal_count = 0
        self._is_scanning = False
        self._last_scan_time = None
        self._last_scan_duration = 0

    @property
    def is_scanning(self) -> bool:
        return self._is_scanning

    def start_scan(self) -> int:
        self._scan_count += 1
        self._is_scanning = True
        self._last_scan_time = datetime.now()
        return self._scan_count

    def end_scan(self, duration: float) -> None:
        self._is_scanning = False
        self._last_scan_duration = duration

    def increment_signal(self) -> int:
        self._signal_count += 1
        return self._signal_count

    def get_stats(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "signal_count": self._signal_count,
            "is_scanning": self._is_scanning,
            "last_scan_duration": self._last_scan_duration,
        }


# Singleton state
_async_state = AsyncScannerState()


async def process_symbol_async(symbol: str, df_daily, market_type: str) -> dict[str, Any]:
    """
    Tek sembol için asenkron sinyal analizi.

    Args:
        symbol: Sembol
        df_daily: OHLCV verisi
        market_type: Piyasa türü

    Returns:
        Bulunan sinyaller
    """
    if df_daily is None or df_daily.empty:
        return {"symbol": symbol, "signals": []}

    signals = []

    for tf_code, tf_label in TIMEFRAMES:
        try:
            df_resampled = resample_market_data(df_daily.copy(), tf_code, market_type)
            if df_resampled is None or len(df_resampled) < 20:
                continue

            # COMBO
            res_combo = calculate_combo_signal(df_resampled, tf_code)
            if res_combo:
                if res_combo["buy"]:
                    signals.append(
                        {
                            "strategy": "COMBO",
                            "type": "AL",
                            "timeframe": tf_code,
                            "tf_label": tf_label,
                            "score": res_combo["details"]["Score"],
                            "price": res_combo["details"].get("PRICE", 0),
                        }
                    )
                if res_combo["sell"]:
                    signals.append(
                        {
                            "strategy": "COMBO",
                            "type": "SAT",
                            "timeframe": tf_code,
                            "tf_label": tf_label,
                            "score": res_combo["details"]["Score"],
                            "price": res_combo["details"].get("PRICE", 0),
                        }
                    )

            # HUNTER
            res_hunter = calculate_hunter_signal(df_resampled, tf_code)
            if res_hunter:
                if res_hunter["buy"]:
                    signals.append(
                        {
                            "strategy": "HUNTER",
                            "type": "AL",
                            "timeframe": tf_code,
                            "tf_label": tf_label,
                            "score": res_hunter["details"]["DipScore"],
                            "price": res_hunter["details"].get("PRICE", 0),
                        }
                    )
                if res_hunter["sell"]:
                    signals.append(
                        {
                            "strategy": "HUNTER",
                            "type": "SAT",
                            "timeframe": tf_code,
                            "tf_label": tf_label,
                            "score": res_hunter["details"]["TopScore"],
                            "price": res_hunter["details"].get("PRICE", 0),
                        }
                    )

        except Exception as e:
            logger.error(f"Sinyal hesaplama hatası ({symbol} - {tf_code}): {e}")

    return {"symbol": symbol, "market_type": market_type, "signals": signals}


async def process_signals_batch(results: list[dict[str, Any]], notify: bool = True) -> int:
    """
    Sinyal sonuçlarını işler ve bildirim gönderir.

    Args:
        results: Sembol sonuçları listesi
        notify: Telegram bildirimi gönder

    Returns:
        Toplam sinyal sayısı
    """
    total_signals = 0

    for result in results:
        symbol = result["symbol"]
        market_type = result.get("market_type", "BIST")

        for signal in result.get("signals", []):
            total_signals += 1
            _async_state.increment_signal()

            # Veritabanına kaydet
            db_save_signal(
                symbol=symbol,
                market_type=market_type,
                strategy=signal["strategy"],
                signal_type=signal["type"],
                timeframe=signal["timeframe"],
                score=str(signal["score"]),
                price=signal["price"],
            )

    return total_signals


def _normalize_scan_markets(
    markets: str | list[str] | tuple[str, ...] | set[str] | None,
) -> set[str]:
    if markets is None:
        return {"BIST", "Kripto"}

    raw_markets = [markets] if isinstance(markets, str) else list(markets)

    normalized: set[str] = set()
    for market in raw_markets:
        token = str(market or "").strip().upper()
        if token == "BIST":
            normalized.add("BIST")
        elif token in {"KRIPTO", "CRYPTO"}:
            normalized.add("Kripto")
    return normalized or {"BIST", "Kripto"}


async def scan_market_async(
    notify: bool = True,
    progress_callback: Callable | None = None,
    markets: str | list[str] | tuple[str, ...] | set[str] | None = None,
) -> dict[str, Any]:
    """
    Asenkron piyasa tarama.

    BIST ve kripto piyasalarını paralel tarar.

    Args:
        notify: Telegram bildirimleri gönder
        progress_callback: İlerleme callback'i

    Returns:
        Tarama sonuç istatistikleri
    """
    if _async_state.is_scanning:
        logger.warning("Tarama zaten devam ediyor")
        return {"error": "Tarama devam ediyor"}

    selected_markets = _normalize_scan_markets(markets)
    market_label = " + ".join(m for m in ("BIST", "Kripto") if m in selected_markets)

    scan_num = _async_state.start_scan()
    start_time = time.time()

    logger.info(f"Async tarama #{scan_num} başladı")
    send_message(f"🔄 Tarama #{scan_num} başladı (Async Mode)")

    total_signals = 0
    bist_data = {}
    crypto_data = {}

    try:
        # BIST Tarama
        bist_symbols = get_all_bist_symbols() if "BIST" in selected_markets else []
        logger.info(f"BIST taranıyor: {len(bist_symbols)} hisse")

        bist_data = await fetch_multiple_bist_async(bist_symbols, batch_size=30)
        logger.info(f"BIST verisi çekildi: {len(bist_data)} sembol")

        # BIST sinyalleri paralel hesapla
        bist_tasks = [process_symbol_async(sym, df, "BIST") for sym, df in bist_data.items()]
        bist_results = await asyncio.gather(*bist_tasks)

        bist_signals = await process_signals_batch(bist_results, notify)
        total_signals += bist_signals
        logger.info(f"BIST sinyalleri: {bist_signals}")

        # Kripto Tarama
        crypto_symbols = (
            get_all_binance_symbols_async() if "Kripto" in selected_markets else []
        )
        logger.info(f"Kripto taranıyor: {len(crypto_symbols)} çift")

        crypto_data = await fetch_multiple_crypto_async(crypto_symbols, batch_size=50)
        logger.info(f"Kripto verisi çekildi: {len(crypto_data)} sembol")

        # Kripto sinyalleri paralel hesapla
        crypto_tasks = [process_symbol_async(sym, df, "Kripto") for sym, df in crypto_data.items()]
        crypto_results = await asyncio.gather(*crypto_tasks)

        crypto_signals = await process_signals_batch(crypto_results, notify)
        total_signals += crypto_signals
        logger.info(f"Kripto sinyalleri: {crypto_signals}")

    except Exception as e:
        logger.error(f"Async tarama hatası: {e}")
        send_message(f"❌ Tarama hatası: {str(e)}")

    duration = time.time() - start_time
    _async_state.end_scan(duration)

    # Sonuç mesajı
    summary = (
        f"Tarama #{scan_num} tamamlandi\n"
        f"Sure: {duration:.1f}s\n"
        f"BIST: {len(bist_data)} sembol\n"
        f"Kripto: {len(crypto_data)} sembol\n"
        f"Toplam Sinyal: {total_signals}\n"
        f"Piyasalar: {market_label}"
    )
    send_message(summary)
    logger.info(summary.replace("\n", " | "))

    return {
        "scan_num": scan_num,
        "duration": duration,
        "bist_count": len(bist_data),
        "crypto_count": len(crypto_data),
        "total_signals": total_signals,
    }


def run_async_scan(markets: str | list[str] | tuple[str, ...] | set[str] | None = None):
    """Sync wrapper for async scan."""
    return asyncio.run(scan_market_async(markets=markets))


def get_async_scanner_stats() -> dict[str, Any]:
    """Scanner istatistiklerini döndürür."""
    return _async_state.get_stats()
