"""
Async Market Scanner ModÃ¼lÃ¼
Paralel piyasa tarama ve sinyal iÅŸleme.
"""

import asyncio
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from application.scanner.scan_history import record_scan_error, record_signal_saved, track_scan
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
        record_scan_error()
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
            record_scan_error()
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

    def on_persisted(signal_id: int) -> None:
        nonlocal total_signals
        if signal_id > 0:
            record_signal_saved()
            total_signals += 1
            _async_state.increment_signal()

    for result in results:
        symbol = result["symbol"]
        market_type = result.get("market_type", "BIST")

        for signal in result.get("signals", []):
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
                on_persisted=on_persisted,
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

    bist_data = {}
    crypto_data = {}
    scan_error = ""

    try:
        with track_scan(markets=selected_markets, mode="async") as progress:
            scan_num = _async_state.start_scan()
            logger.info("Async tarama #%s basladi", scan_num)
            _send_scan_message(f"Tarama #{scan_num} basladi (Async Mode)", notify)

            for market_type in ("BIST", "Kripto"):
                if market_type not in selected_markets:
                    continue
                symbols = (
                    get_all_bist_symbols()
                    if market_type == "BIST"
                    else get_all_binance_symbols_async()
                )
                if not symbols:
                    record_scan_error()
                    logger.warning("%s sembol listesi bos; tarama eksik.", market_type)
                # Count targets handed to the batch provider, including missing data.
                progress.symbols_scanned += len(symbols)
                logger.info("%s taraniyor: %s sembol", market_type, len(symbols))
                if market_type == "BIST":
                    bist_data = data = await fetch_multiple_bist_async(symbols, batch_size=30)
                else:
                    crypto_data = data = await fetch_multiple_crypto_async(symbols, batch_size=50)
                record_scan_error(len(set(symbols) - data.keys()))
                tasks = [
                    process_symbol_async(sym, data[sym], market_type)
                    for sym in symbols
                    if sym in data
                ]
                # Await every child before closing accounting, even if one fails.
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_results = []
                for result in results:
                    if isinstance(result, asyncio.CancelledError):
                        raise result
                    if isinstance(result, BaseException):
                        if not isinstance(result, Exception):
                            raise result
                        record_scan_error()
                        logger.error("Sembol analizi basarisiz: %s", type(result).__name__)
                    else:
                        successful_results.append(result)
                await process_signals_batch(successful_results, notify)
    except Exception as e:
        scan_error = str(e)
        logger.exception("Async tarama hatasi.")
    finally:
        _async_state.end_scan(progress.duration_seconds)

    duration = progress.duration_seconds
    total_signals = progress.signals_found
    outcome_label = {"success": "tamamlandi", "partial": "eksik tamamlandi", "failed": "basarisiz"}
    summary = (
        f"Tarama #{scan_num} {outcome_label[progress.status]}\n"
        f"Sure: {duration:.1f}s\n"
        f"BIST: {len(bist_data)} sembol\n"
        f"Kripto: {len(crypto_data)} sembol\n"
        f"Toplam Sinyal: {total_signals}\n"
        f"Piyasalar: {market_label}"
    )
    _send_scan_message(summary, notify)
    logger.info(summary.replace("\n", " | "))

    return {
        "status": progress.status,
        "error": scan_error or None,
        "scan_num": scan_num,
        "duration": duration,
        "bist_count": len(bist_data),
        "crypto_count": len(crypto_data),
        "total_signals": total_signals,
        "errors_count": progress.errors_count,
        "history_id": progress.history_id,
    }


def _send_scan_message(message: str, notify: bool) -> None:
    if not notify:
        return
    try:
        send_message(message)
    except Exception:
        logger.exception("Tarama bildirimi gonderilemedi.")


def run_async_scan(markets: str | list[str] | tuple[str, ...] | set[str] | None = None):
    """Sync wrapper for async scan."""
    return asyncio.run(scan_market_async(markets=markets))


def get_async_scanner_stats() -> dict[str, Any]:
    """Scanner istatistiklerini dÃ¶ndÃ¼rÃ¼r."""
    return _async_state.get_stats()


restore_async_scanner_state_from_db()
