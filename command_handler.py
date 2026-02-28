"""
Telegram command handling utilities.
"""

from __future__ import annotations

import re
import time
from datetime import datetime

from data_loader import get_bist_data, get_crypto_data, resample_data
from logger import get_logger
from signals import calculate_combo_signal, calculate_hunter_signal
from strategy_inspector import (
    StrategyInspectorError,
    build_strategy_inspector_chunks,
    inspect_strategy,
)
from telegram_notify import get_last_messages, send_message

logger = get_logger(__name__)

BOT_START_TIME = datetime.now()

INSPECTOR_MESSAGE_PATTERN = re.compile(
    r"^(?P<symbol>[A-Z0-9.]{1,20})\s+"
    r"(?P<strategy>combo|hunter)"
    r"(?:\s+(?P<market>bist|kripto|krypto|auto))?$",
    re.IGNORECASE,
)


def get_uptime_hours() -> float:
    """Return bot uptime in hours."""
    uptime = datetime.now() - BOT_START_TIME
    return uptime.total_seconds() / 3600


def analyze_manual(symbol: str) -> None:
    """
    Run the existing manual analysis flow for a single symbol.
    """
    from market_scanner import generate_manual_report

    symbol = symbol.upper()
    market_type = "BIST"
    df = get_bist_data(symbol)

    if df is None or df.empty:
        market_type = "KRIPTO"
        if (
            not symbol.endswith("USDT")
            and not symbol.endswith("BTC")
            and not symbol.endswith("TRY")
        ):
            crypto_symbol = symbol + "USDT"
            df = get_crypto_data(crypto_symbol)
            if df is not None and not df.empty:
                symbol = crypto_symbol
        else:
            df = get_crypto_data(symbol)

    if df is None or df.empty:
        send_message(f"ERROR: '{symbol}' bulunamadi.")
        return

    df_daily = resample_data(df.copy(), "1D")
    if df_daily is None or len(df_daily) < 30:
        send_message("Uyari: Yetersiz veri.")
        return

    res_combo = calculate_combo_signal(df_daily, "1D")
    res_hunter = calculate_hunter_signal(df_daily, "1D")

    if res_combo and res_hunter:
        report = generate_manual_report(symbol, market_type, res_combo, res_hunter)
        send_message(report)
    else:
        send_message("Uyari: Hesaplama hatasi.")


def handle_durum_command() -> None:
    """Send short bot status message."""
    send_message("Bot calisiyor.\nSaat: " + time.strftime("%H:%M:%S"))


def handle_health_command(scan_count: int = 0, signal_count: int = 0) -> None:
    """Send bot health snapshot."""
    hours = get_uptime_hours()
    health_msg = (
        f"<b>Bot Saglik Durumu</b>\n"
        f"- Durum: Calisiyor\n"
        f"- Uptime: {hours:.1f} saat\n"
        f"- Toplam Tarama: {scan_count}\n"
        f"- Uretilen Sinyal: {signal_count}\n"
        f"- Saat: {time.strftime('%H:%M:%S')}"
    )
    send_message(health_msg)


def handle_analiz_command(msg: str) -> None:
    """Handle /analiz SYMBOL command."""
    parts = msg.split()
    if len(parts) > 1:
        symbol = parts[1].upper()
        if not re.match(r"^[A-Z0-9]{1,15}$", symbol):
            send_message("ERROR: Gecersiz sembol formati. Ornek: /analiz THYAO")
            return
        send_message(f"Analiz basladi: #{symbol}")
        analyze_manual(symbol)
        return

    send_message("Kullanim: /analiz THYAO")


def _parse_inspector_tokens(tokens: list[str]) -> tuple[str, str, str | None]:
    if len(tokens) < 2:
        raise StrategyInspectorError("Kullanim: /indikator THYAO HUNTER [BIST|KRIPTO]")

    symbol = tokens[0].upper()
    strategy = tokens[1].upper()
    market_type = tokens[2].upper() if len(tokens) > 2 else None

    if not re.match(r"^[A-Z0-9.]{1,20}$", symbol):
        raise StrategyInspectorError("Gecersiz sembol formati.")

    if strategy not in {"COMBO", "HUNTER"}:
        raise StrategyInspectorError("Strateji COMBO veya HUNTER olmali.")

    if market_type and market_type not in {"BIST", "KRIPTO", "KRYPTO", "AUTO"}:
        raise StrategyInspectorError("Piyasa tipi BIST, KRIPTO veya AUTO olmali.")

    return symbol, strategy, market_type


def send_strategy_inspector_report(
    symbol: str,
    strategy: str,
    market_type: str | None = None,
) -> None:
    """Run the strategy inspector and send the report to Telegram."""
    progress = f"Inspector basladi: {symbol} {strategy}"
    if market_type:
        progress += f" {market_type}"
    send_message(progress)

    report = inspect_strategy(symbol=symbol, strategy=strategy, market_type=market_type)
    for chunk in build_strategy_inspector_chunks(report):
        send_message(chunk)


def handle_strategy_inspector_command(msg: str) -> None:
    """Handle /indikator and equivalent inspector commands."""
    try:
        parts = msg.split()
        tokens = parts[1:] if parts and parts[0].startswith("/") else parts
        symbol, strategy, market_type = _parse_inspector_tokens(tokens)
        send_strategy_inspector_report(symbol, strategy, market_type)
    except StrategyInspectorError as exc:
        send_message(f"Inspector hatasi: {exc}")
    except Exception as exc:  # pragma: no cover - defensive Telegram path
        logger.exception("Strategy inspector command failed: %s", exc)
        send_message("Inspector hatasi: Hesaplama tamamlanamadi.")


def check_commands(scan_market_callback=None, get_scan_count_callback=None) -> None:
    """
    Process incoming Telegram commands.

    Supported:
        /durum
        /tara
        /asynctara
        /analiz SYMBOL
        /indikator SYMBOL STRATEJI [BIST|KRIPTO]
        /inspector SYMBOL STRATEJI [BIST|KRIPTO]
        /strateji SYMBOL STRATEJI [BIST|KRIPTO]
        SYMBOL STRATEJI [BIST|KRIPTO]
        /health
        /portfoy
        /islemler [SYMBOL]
        /cache
    """
    messages = get_last_messages()
    for msg in messages:
        if not msg:
            continue

        stripped = msg.strip()
        msg_lower = stripped.lower()

        if msg_lower == "/durum":
            handle_durum_command()

        elif msg_lower == "/tara":
            send_message("Tarama manuel baslatildi...")
            if scan_market_callback:
                scan_market_callback()

        elif msg_lower.startswith("/analiz"):
            handle_analiz_command(stripped)

        elif (
            msg_lower.startswith("/indikator")
            or msg_lower.startswith("/inspector")
            or msg_lower.startswith("/strateji")
        ):
            handle_strategy_inspector_command(stripped)

        elif msg_lower == "/health":
            scan_count = get_scan_count_callback() if get_scan_count_callback else 0
            handle_health_command(scan_count=scan_count)

        elif msg_lower == "/portfoy":
            from trade_manager import handle_portfolio_command

            handle_portfolio_command()

        elif msg_lower == "/islemler" or msg_lower.startswith("/islemler "):
            from trade_manager import handle_trades_command

            parts = stripped.split()
            symbol = None
            if len(parts) > 1:
                symbol = parts[1].upper()
                if not re.match(r"^[A-Z0-9]{1,15}$", symbol):
                    send_message("ERROR: Gecersiz sembol formati. Ornek: /islemler THYAO")
                    continue
            handle_trades_command(symbol)

        elif msg_lower == "/cache":
            from price_cache import get_cache_report

            send_message(get_cache_report())

        elif msg_lower == "/asynctara":
            send_message("Async tarama baslatiliyor...")
            from async_scanner import run_async_scan

            run_async_scan()

        else:
            matched = INSPECTOR_MESSAGE_PATTERN.fullmatch(stripped)
            if matched:
                handle_strategy_inspector_command(stripped)
