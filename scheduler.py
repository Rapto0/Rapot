"""
Scheduler Modülü
Zamanlama ve ana çalışma döngüsü.
Async tarama varsayılan olarak aktif.
"""

import asyncio
import time
import warnings

import schedule

from config import scan_settings
from logger import get_logger
from telegram_notify import send_message

logger = get_logger(__name__)

warnings.simplefilter(action="ignore", category=FutureWarning)


def run_special_tag_health_check() -> None:
    """
    Ozel etiketleme kapsama kontrolu.
    candidate > tagged oldugunda alarm logu basar.
    """
    try:
        from database import get_special_tag_coverage

        coverage_rows = get_special_tag_coverage(
            since_hours=24,
            market_type="BIST",
            strategy=None,
            window_seconds=900,
        )
        issues = [row for row in coverage_rows if row.get("missing", 0) > 0]

        if issues:
            summary = ", ".join(
                f"{row['strategy']}:{row['tag']} m={row['missing']} c={row['candidates']} t={row['tagged']}"
                for row in issues
            )
            logger.warning(f"Ozel etiket kapsama alarmi (24h): {summary}")
        else:
            logger.info("Ozel etiket kapsama kontrolu OK (24h, BIST).")
    except Exception as exc:
        logger.error(f"Ozel etiket kapsama kontrolu hatasi: {exc}")


def setup_scheduler(scan_func, interval_hours: int = None) -> None:
    """
    Periyodik tarama zamanlamasını ayarlar.

    Args:
        scan_func: Çalıştırılacak tarama fonksiyonu
        interval_hours: Tarama aralığı (saat). None ise config'den alınır.
    """
    if interval_hours is None:
        interval_hours = scan_settings.SCAN_INTERVAL_HOURS

    schedule.every(interval_hours).hours.do(scan_func)
    schedule.every().hour.do(run_special_tag_health_check)
    logger.info(f"Scheduler kuruldu: her {interval_hours} saatte bir tarama")
    logger.info("Scheduler kuruldu: her 1 saatte ozel etiket kapsama kontrolu")


def run_bot_loop(scan_func, check_commands_func) -> None:
    """
    Ana bot döngüsünü çalıştırır.

    Her saniye:
    1. Zamanlı görevleri kontrol eder
    2. Telegram komutlarını kontrol eder

    Args:
        scan_func: Tarama fonksiyonu
        check_commands_func: Komut kontrol fonksiyonu
    """
    logger.info("Bot döngüsü başlatıldı")

    while True:
        try:
            schedule.run_pending()
            check_commands_func()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot kapatılıyor...")
            send_message("🛑 Bot kapatıldı.")
            break
        except Exception as e:
            logger.error(f"Döngü hatası: {e}")
            time.sleep(5)  # Hata durumunda 5 saniye bekle


def run_async_scan_wrapper():
    """Async taramayı sync wrapper ile çalıştırır."""
    from async_scanner import scan_market_async

    try:
        asyncio.run(scan_market_async())
    except Exception as e:
        logger.error(f"Async tarama hatası: {e}")
        # Fallback to sync scan
        logger.info("Sync taramaya geri dönülüyor...")
        from market_scanner import scan_market

        scan_market()


def start_bot(use_async: bool = True) -> None:
    """
    Bot'u başlatır ve ana döngüyü çalıştırır.

    1. İlk taramayı yapar (async veya sync)
    2. Periyodik taramayı zamanlar
    3. Ana döngüyü başlatır

    Args:
        use_async: True ise async tarama kullan (varsayılan: True, main.py'den False geçiliyor)
    """
    from command_handler import check_commands
    from db_session import init_db
    from market_scanner import get_scan_count, scan_market

    mode = "⚡ Async" if use_async else "🔄 Sync"
    logger.info(f"🚀 Bot Başlatılıyor... ({mode} Mode)")
    print(f"🚀 Bot Başlatılıyor... ({mode} Mode)")

    try:
        init_db()
        logger.info("Bot başlangıcında veritabanı şeması doğrulandı.")
    except Exception as e:
        logger.error(f"Veritabanı başlatılamadı, bot durduruluyor: {e}")
        raise

    # Health API'yi başlat
    try:
        from health_api import start_health_server

        start_health_server(port=5000)
        logger.info("Health API: http://localhost:5000")
    except Exception as e:
        logger.warning(f"Health API başlatılamadı: {e}")

    welcome_msg = (
        f"🚀 Bot Başlatıldı! ({mode} Mode)\n"
        "Komutlar:\n"
        "👉 /durum\n"
        "👉 /tara (sync)\n"
        "👉 /asynctara (async)\n"
        "👉 /analiz SEMBOL\n"
        "👉 /health\n"
        "👉 /portfoy\n"
        "👉 /islemler\n"
        "👉 /cache"
    )
    send_message(welcome_msg)

    # Komut callback'leri oluştur
    def check_commands_wrapper():
        check_commands(
            scan_market_callback=lambda: scan_market(
                check_commands_callback=check_commands_wrapper
            ),
            get_scan_count_callback=get_scan_count,
        )

    def run_sync_scan():
        scan_market(check_commands_callback=check_commands_wrapper)

    # Tarama fonksiyonu seç
    scan_func = run_async_scan_wrapper if use_async else run_sync_scan

    # İlk tarama
    logger.info("İlk tarama başlatılıyor...")
    scan_func()
    run_special_tag_health_check()

    # Zamanlayıcı kur
    setup_scheduler(scan_func)

    # Ana döngü
    run_bot_loop(scan_func, check_commands_wrapper)


if __name__ == "__main__":
    start_bot(use_async=False)  # Sync varsayılan
