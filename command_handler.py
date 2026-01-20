"""
Command Handler Modülü
Telegram komutlarını işleyen fonksiyonlar.
"""

import re
import time
from datetime import datetime

from data_loader import get_bist_data, get_crypto_data, resample_data
from logger import get_logger
from signals import calculate_combo_signal, calculate_hunter_signal
from telegram_notify import get_last_messages, send_message

logger = get_logger(__name__)

# Bot başlangıç zamanı
BOT_START_TIME = datetime.now()


def get_uptime_hours() -> float:
    """Bot uptime'ını saat cinsinden döndürür."""
    uptime = datetime.now() - BOT_START_TIME
    return uptime.total_seconds() / 3600


def analyze_manual(symbol: str) -> None:
    """
    Telegram /analiz komutu icin manuel sembol analizi yapar.

    Once BIST'te arar, bulamazsa kripto olarak dener.
    Sonuclari Telegram'a gonderir.

    Args:
        symbol: Analiz edilecek sembol (orn: THYAO, BTC)
    """
    # Lazy import to avoid circular dependency
    from market_scanner import generate_manual_report

    symbol = symbol.upper()
    market_type = "BIST"
    df = get_bist_data(symbol)

    if df is None or df.empty:
        market_type = "KRİPTO"
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
        send_message(f"❌ <b>HATA:</b> '{symbol}' bulunamadı.")
        return

    df_daily = resample_data(df.copy(), "1D")
    if df_daily is None or len(df_daily) < 30:
        send_message("⚠️ Yetersiz veri.")
        return

    res_combo = calculate_combo_signal(df_daily, "1D")
    res_hunter = calculate_hunter_signal(df_daily, "1D")

    if res_combo and res_hunter:
        report = generate_manual_report(symbol, market_type, res_combo, res_hunter)
        send_message(report)
    else:
        send_message("⚠️ Hesaplama hatası.")


def handle_durum_command() -> None:
    """Bot durum bilgisi gönderir."""
    send_message("🤖 Bot Çalışıyor (AI Aktif).\nSaat: " + time.strftime("%H:%M:%S"))


def handle_health_command(scan_count: int = 0, signal_count: int = 0) -> None:
    """
    Bot sağlık durumu bilgisi gönderir.

    Args:
        scan_count: Toplam tarama sayısı
        signal_count: Üretilen sinyal sayısı
    """
    hours = get_uptime_hours()
    health_msg = (
        f"🏥 <b>Bot Sağlık Durumu</b>\n"
        f"• Durum: ✅ Çalışıyor\n"
        f"• Uptime: {hours:.1f} saat\n"
        f"• Toplam Tarama: {scan_count}\n"
        f"• Üretilen Sinyal: {signal_count}\n"
        f"• Saat: {time.strftime('%H:%M:%S')}"
    )
    send_message(health_msg)


def handle_analiz_command(msg: str) -> None:
    """
    /analiz komutunu işler.

    Args:
        msg: Tam komut mesajı (orn: /analiz THYAO)
    """
    parts = msg.split()
    if len(parts) > 1:
        symbol = parts[1].upper()
        # Input validation
        if not re.match(r"^[A-Z0-9]{1,15}$", symbol):
            send_message("❌ Geçersiz sembol formatı. Örnek: /analiz THYAO")
            return
        send_message(f"🔎 #{symbol} analiz ediliyor...")
        analyze_manual(symbol)
    else:
        send_message("⚠️ Kullanım: /analiz THYAO")


def check_commands(scan_market_callback=None, get_scan_count_callback=None) -> None:
    """
    Telegram'dan gelen kullanici komutlarini isler.

    Desteklenen komutlar:
        /durum - Bot durumunu bildirir
        /tara - Manuel piyasa taramasi baslatir
        /asynctara - Async piyasa taramasi baslatir
        /analiz <sembol> - Belirli bir sembolu analiz eder
        /health - Bot saglik durumunu gosterir
        /portfoy - Portfoy durumunu gosterir
        /islemler - Son islemleri listeler
        /cache - Cache durumunu gosterir

    Args:
        scan_market_callback: Tarama fonksiyonu (opsiyonel)
        get_scan_count_callback: Tarama sayısı fonksiyonu (opsiyonel)
    """
    messages = get_last_messages()
    for msg in messages:
        if not msg:
            continue
        msg_lower = msg.lower()

        if msg_lower == "/durum":
            handle_durum_command()

        elif msg_lower == "/tara":
            send_message("⏳ Tarama manuel başlatıldı...")
            if scan_market_callback:
                scan_market_callback()

        elif msg_lower.startswith("/analiz"):
            handle_analiz_command(msg)

        elif msg_lower == "/health":
            scan_count = get_scan_count_callback() if get_scan_count_callback else 0
            handle_health_command(scan_count=scan_count)

        elif msg_lower == "/portfoy":
            from trade_manager import handle_portfolio_command

            handle_portfolio_command()

        elif msg_lower == "/islemler" or msg_lower.startswith("/islemler "):
            from trade_manager import handle_trades_command

            parts = msg.split()
            symbol = None
            if len(parts) > 1:
                symbol = parts[1].upper()
                # Input validation (aynı /analiz gibi)
                if not re.match(r"^[A-Z0-9]{1,15}$", symbol):
                    send_message("❌ Geçersiz sembol formatı. Örnek: /islemler THYAO")
                    continue
            handle_trades_command(symbol)

        elif msg_lower == "/cache":
            from price_cache import get_cache_report

            send_message(get_cache_report())

        elif msg_lower == "/asynctara":
            send_message("⚡ Async tarama başlatılıyor...")
            from async_scanner import run_async_scan

            run_async_scan()
