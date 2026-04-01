"""
Async Market Scanner ModÃ¼lÃ¼
Paralel piyasa tarama ve sinyal iÅŸleme.
"""

import asyncio
import json
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from application.scanner.signal_handlers import persist_and_publish_signal_event
from async_data_loader import (
    fetch_multiple_bist_async,
    fetch_multiple_crypto_async,
    get_all_binance_symbols_async,
)
from config import TIMEFRAMES
from data_loader import get_all_bist_symbols, resample_market_data
from domain.events import SignalDomainEvent
from infrastructure.persistence.signal_repository import save_signal as db_save_signal
from logger import get_logger
from signal_dispatcher import publish_signal_event
from signals import calculate_combo_signal, calculate_hunter_signal
from state_keys import ASYNC_SCAN_COUNT_KEY, ASYNC_SIGNAL_COUNT_KEY
from telegram_notify import send_message

logger = get_logger(__name__)
_REALTIME_PUBLISH_FAILURE_COUNT = 0


def _json_default(value: Any):
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return str(value)


def _serialize_signal_details(details: dict[str, Any] | None) -> str:
    if not details:
        return ""
    try:
        return json.dumps(details, ensure_ascii=False, default=_json_default)
    except Exception:
        return ""


def _build_realtime_signal_payload(
    *,
    signal_id: int,
    symbol: str,
    market_type: str,
    strategy: str,
    signal_type: str,
    timeframe: str,
    score: str,
    price: float,
) -> dict[str, Any]:
    return {
        "id": signal_id,
        "symbol": symbol,
        "marketType": market_type,
        "strategy": strategy,
        "signalType": signal_type,
        "timeframe": timeframe,
        "score": score,
        "price": float(price),
        "createdAt": datetime.now().isoformat(),
    }


def _publish_realtime_signal(payload: dict[str, Any]) -> bool:
    global _REALTIME_PUBLISH_FAILURE_COUNT
    try:
        return publish_signal_event(payload)
    except Exception as exc:
        _REALTIME_PUBLISH_FAILURE_COUNT += 1
        logger.warning(
            "Realtime signal publish skipped (%s failures): %s",
            _REALTIME_PUBLISH_FAILURE_COUNT,
            exc,
        )
        return False


def get_realtime_publish_failure_count() -> int:
    return _REALTIME_PUBLISH_FAILURE_COUNT


class AsyncScannerState:
    """Async scanner durum yÃ¶netimi."""

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
        try:
            from infrastructure.persistence.ops_repository import set_bot_stat_int

            set_bot_stat_int(ASYNC_SCAN_COUNT_KEY, self._scan_count)
        except Exception as exc:
            logger.warning("Async scan count persistence failed: %s", exc)
        return self._scan_count

    def end_scan(self, duration: float) -> None:
        self._is_scanning = False
        self._last_scan_duration = duration

    def increment_signal(self) -> int:
        self._signal_count += 1
        try:
            from infrastructure.persistence.ops_repository import set_bot_stat_int

            set_bot_stat_int(ASYNC_SIGNAL_COUNT_KEY, self._signal_count)
        except Exception as exc:
            logger.warning("Async signal count persistence failed: %s", exc)
        return self._signal_count

    def restore(self, scan_count: int, signal_count: int) -> None:
        self._scan_count = max(0, int(scan_count))
        self._signal_count = max(0, int(signal_count))

    def get_stats(self) -> dict[str, Any]:
        return {
            "scan_count": self._scan_count,
            "signal_count": self._signal_count,
            "is_scanning": self._is_scanning,
            "last_scan_duration": self._last_scan_duration,
        }


# Singleton state
_async_state = AsyncScannerState()


def restore_async_scanner_state_from_db() -> None:
    try:
        from infrastructure.persistence.ops_repository import get_bot_stat_int

        scan_count = get_bot_stat_int(ASYNC_SCAN_COUNT_KEY, default=0)
        signal_count = get_bot_stat_int(ASYNC_SIGNAL_COUNT_KEY, default=0)
        _async_state.restore(scan_count=scan_count, signal_count=signal_count)
        logger.info("Async scanner state restored | scans=%s signals=%s", scan_count, signal_count)
    except Exception as exc:
        logger.warning("Async scanner state restore skipped: %s", exc)


async def process_symbol_async(symbol: str, df_daily, market_type: str) -> dict[str, Any]:
    """
    Tek sembol iÃ§in asenkron sinyal analizi.

    Args:
        symbol: Sembol
        df_daily: OHLCV verisi
        market_type: Piyasa tÃ¼rÃ¼

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
                            "details": res_combo.get("details"),
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
                            "details": res_combo.get("details"),
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
                            "details": res_hunter.get("details"),
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
                            "details": res_hunter.get("details"),
                        }
                    )

        except Exception as e:
            logger.error(f"Sinyal hesaplama hatasÄ± ({symbol} - {tf_code}): {e}")

    return {"symbol": symbol, "market_type": market_type, "signals": signals}


async def process_signals_batch(results: list[dict[str, Any]], notify: bool = True) -> int:
    """
    Sinyal sonuÃ§larÄ±nÄ± iÅŸler ve bildirim gÃ¶nderir.

    Args:
        results: Sembol sonuÃ§larÄ± listesi
        notify: Telegram bildirimi gÃ¶nder

    Returns:
        Toplam sinyal sayÄ±sÄ±
    """
    total_signals = 0

    for result in results:
        symbol = result["symbol"]
        market_type = result.get("market_type", "BIST")

        for signal in result.get("signals", []):
            total_signals += 1
            _async_state.increment_signal()

            event = SignalDomainEvent(
                symbol=symbol,
                market_type=market_type,
                strategy=str(signal["strategy"]),
                signal_type=str(signal["type"]),
                timeframe=str(signal["timeframe"]),
                score=str(signal["score"]),
                price=float(signal["price"]),
                details=signal.get("details"),
                special_tag=None,
            )
            persist_and_publish_signal_event(
                event=event,
                save_signal_fn=db_save_signal,
                publish_signal_fn=_publish_realtime_signal,
                payload_builder_fn=_build_realtime_signal_payload,
                details_serializer=_serialize_signal_details,
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

    BIST ve kripto piyasalarÄ±nÄ± paralel tarar.

    Args:
        notify: Telegram bildirimleri gÃ¶nder
        progress_callback: Ä°lerleme callback'i

    Returns:
        Tarama sonuÃ§ istatistikleri
    """
    if _async_state.is_scanning:
        logger.warning("Tarama zaten devam ediyor")
        return {"error": "Tarama devam ediyor"}

    selected_markets = _normalize_scan_markets(markets)
    market_label = " + ".join(m for m in ("BIST", "Kripto") if m in selected_markets)

    scan_num = _async_state.start_scan()
    start_time = time.time()

    logger.info(f"Async tarama #{scan_num} baÅŸladÄ±")
    send_message(f"ğŸ”„ Tarama #{scan_num} baÅŸladÄ± (Async Mode)")

    total_signals = 0
    bist_data = {}
    crypto_data = {}
    scan_failed = False
    scan_error = ""

    try:
        # BIST Tarama
        bist_symbols = get_all_bist_symbols() if "BIST" in selected_markets else []
        logger.info(f"BIST taranÄ±yor: {len(bist_symbols)} hisse")

        bist_data = await fetch_multiple_bist_async(bist_symbols, batch_size=30)
        logger.info(f"BIST verisi Ã§ekildi: {len(bist_data)} sembol")

        # BIST sinyalleri paralel hesapla
        bist_tasks = [process_symbol_async(sym, df, "BIST") for sym, df in bist_data.items()]
        bist_results = await asyncio.gather(*bist_tasks)

        bist_signals = await process_signals_batch(bist_results, notify)
        total_signals += bist_signals
        logger.info(f"BIST sinyalleri: {bist_signals}")

        # Kripto Tarama
        crypto_symbols = get_all_binance_symbols_async() if "Kripto" in selected_markets else []
        logger.info(f"Kripto taranÄ±yor: {len(crypto_symbols)} Ã§ift")

        crypto_data = await fetch_multiple_crypto_async(crypto_symbols, batch_size=50)
        logger.info(f"Kripto verisi Ã§ekildi: {len(crypto_data)} sembol")

        # Kripto sinyalleri paralel hesapla
        crypto_tasks = [process_symbol_async(sym, df, "Kripto") for sym, df in crypto_data.items()]
        crypto_results = await asyncio.gather(*crypto_tasks)

        crypto_signals = await process_signals_batch(crypto_results, notify)
        total_signals += crypto_signals
        logger.info(f"Kripto sinyalleri: {crypto_signals}")

    except Exception as e:
        scan_failed = True
        scan_error = str(e)
        logger.exception("Async tarama hatasi.")
        send_message(f"âŒ Tarama hatasi: {scan_error}")

    duration = time.time() - start_time
    _async_state.end_scan(duration)

    if scan_failed:
        failure_summary = (
            f"Tarama #{scan_num} basarisiz\n"
            f"Sure: {duration:.1f}s\n"
            f"BIST: {len(bist_data)} sembol\n"
            f"Kripto: {len(crypto_data)} sembol\n"
            f"Toplam Sinyal: {total_signals}\n"
            f"Piyasalar: {market_label}\n"
            f"Hata: {scan_error}"
        )
        send_message(failure_summary)
        logger.error(failure_summary.replace("\n", " | "))
        return {
            "status": "failed",
            "error": scan_error,
            "scan_num": scan_num,
            "duration": duration,
            "bist_count": len(bist_data),
            "crypto_count": len(crypto_data),
            "total_signals": total_signals,
        }

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
        "status": "success",
        "error": None,
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
    """Scanner istatistiklerini dÃ¶ndÃ¼rÃ¼r."""
    return _async_state.get_stats()


restore_async_scanner_state_from_db()
