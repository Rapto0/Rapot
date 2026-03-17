"""
Scheduler module.
Time-based scanning loop for bot operations.
"""

import asyncio
import time
import warnings
from datetime import datetime
from threading import Lock
from zoneinfo import ZoneInfo

import schedule

from logger import get_logger
from telegram_notify import MessagePriority, send_message

logger = get_logger(__name__)

warnings.simplefilter(action="ignore", category=FutureWarning)

SPECIAL_TAG_HEALTH_STATE_KEY = "special_tag_health_state"
SPECIAL_TAG_HEALTH_SUMMARY_KEY = "special_tag_health_summary"
BIST_SCAN_TIMES_TR = ("10:15", "13:00", "17:00")
CRYPTO_SCAN_TIMES_TR = ("07:00", "15:00", "23:00")
_SCAN_LOCK = Lock()


def _format_special_tag_issue_summary(issues: list[dict]) -> str:
    ordered = sorted(
        issues,
        key=lambda row: (int(row.get("missing", 0)), int(row.get("candidates", 0))),
        reverse=True,
    )
    return "\n".join(
        f"- {row['strategy']} {row['tag']}: missing={row['missing']} "
        f"(candidate={row['candidates']}, tagged={row['tagged']})"
        for row in ordered
    )


def run_special_tag_health_check() -> None:
    """
    Special-tag coverage check.
    Sends Telegram only on state transitions.
    """
    try:
        from ops_repository import (
            get_bot_stat,
            get_special_tag_coverage,
            set_bot_stat,
        )

        coverage_rows = get_special_tag_coverage(
            since_hours=24,
            market_type="BIST",
            strategy=None,
            window_seconds=900,
        )
        issues = [row for row in coverage_rows if row.get("missing", 0) > 0]
        previous_state = (get_bot_stat(SPECIAL_TAG_HEALTH_STATE_KEY) or "").strip().lower()

        if issues:
            summary = _format_special_tag_issue_summary(issues)
            set_bot_stat(SPECIAL_TAG_HEALTH_SUMMARY_KEY, summary)
            set_bot_stat(SPECIAL_TAG_HEALTH_STATE_KEY, "alert")
            logger.warning(f"Ozel etiket kapsama alarmi (24h): {summary}")

            if previous_state != "alert":
                send_message(
                    "SPECIAL TAG ALERT\n"
                    "Son 24 saatte ozel etiket kapsama hatasi tespit edildi.\n"
                    f"{summary}",
                    priority=MessagePriority.CRITICAL,
                )
        else:
            logger.info("Ozel etiket kapsama kontrolu OK (24h, BIST).")
            set_bot_stat(SPECIAL_TAG_HEALTH_STATE_KEY, "ok")
            set_bot_stat(SPECIAL_TAG_HEALTH_SUMMARY_KEY, "")

            if previous_state == "alert":
                send_message(
                    "SPECIAL TAG RECOVERY OK\nSon 24 saatte ozel etiket kapsama farki kalmadi.",
                    priority=MessagePriority.HIGH,
                )
    except Exception as exc:
        logger.error(f"Ozel etiket kapsama kontrolu hatasi: {exc}")


def _tr_clock_to_local_clock(tr_clock: str) -> str:
    """
    Convert Europe/Istanbul clock to local server clock.
    Used when schedule package has no timezone support.
    """
    hour_str, minute_str = tr_clock.split(":", 1)
    hour = int(hour_str)
    minute = int(minute_str)
    tr_tz = ZoneInfo("Europe/Istanbul")
    local_now = datetime.now().astimezone()
    tr_now = local_now.astimezone(tr_tz)
    tr_target = tr_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    local_target = tr_target.astimezone(local_now.tzinfo)
    return local_target.strftime("%H:%M")


def _schedule_daily_tr_clock(tr_clock: str, job_func, job_label: str) -> None:
    """
    Schedule a daily job at a given Turkey clock.
    """
    try:
        # Supported in schedule>=1.2
        schedule.every().day.at(tr_clock, "Europe/Istanbul").do(job_func)
        logger.info(f"Scheduler: {job_label} her gun TR {tr_clock}")
    except TypeError:
        local_clock = _tr_clock_to_local_clock(tr_clock)
        schedule.every().day.at(local_clock).do(job_func)
        logger.info(f"Scheduler: {job_label} her gun TR {tr_clock} (local {local_clock} fallback)")


def _run_scheduled_scan(scan_func, label: str) -> None:
    """
    Run scheduled scan with overlap protection.
    """
    if not _SCAN_LOCK.acquire(blocking=False):
        logger.warning(f"{label} atlandi: onceki tarama hala devam ediyor.")
        return

    started_at = time.time()
    try:
        logger.info(f"{label} basladi.")
        scan_func()
    except Exception as exc:
        logger.error(f"{label} hatasi: {exc}")
    finally:
        elapsed = time.time() - started_at
        logger.info(f"{label} tamamlandi ({elapsed:.1f}s).")
        _SCAN_LOCK.release()


def setup_scheduler(scan_bist_func, scan_crypto_func) -> None:
    """
    Configure fixed daily schedule for BIST and Kripto scans.
    """
    for tr_clock in BIST_SCAN_TIMES_TR:
        _schedule_daily_tr_clock(
            tr_clock=tr_clock,
            job_func=lambda f=scan_bist_func, t=tr_clock: _run_scheduled_scan(
                f, f"BIST taramasi (TR {t})"
            ),
            job_label=f"BIST taramasi (TR {tr_clock})",
        )

    for tr_clock in CRYPTO_SCAN_TIMES_TR:
        _schedule_daily_tr_clock(
            tr_clock=tr_clock,
            job_func=lambda f=scan_crypto_func, t=tr_clock: _run_scheduled_scan(
                f, f"Kripto taramasi (TR {t})"
            ),
            job_label=f"Kripto taramasi (TR {tr_clock})",
        )

    schedule.every().hour.do(run_special_tag_health_check)
    logger.info(
        "Scheduler kuruldu | BIST: %s | Kripto: %s",
        ",".join(BIST_SCAN_TIMES_TR),
        ",".join(CRYPTO_SCAN_TIMES_TR),
    )
    logger.info("Scheduler kuruldu: her 1 saatte ozel etiket kapsama kontrolu")


def run_bot_loop(scan_func, check_commands_func) -> None:
    """
    Main loop.
    """
    del scan_func  # intentionally unused in this loop
    logger.info("Bot dongusu baslatildi")

    while True:
        try:
            schedule.run_pending()
            check_commands_func()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot kapatiliyor...")
            send_message("Bot kapatildi.")
            break
        except Exception as e:
            logger.error(f"Dongu hatasi: {e}")
            time.sleep(5)


def run_async_scan_wrapper(markets: str | list[str] | tuple[str, ...] | set[str] | None = None):
    """
    Run async scanner in a sync wrapper.
    """
    from async_scanner import scan_market_async

    try:
        asyncio.run(scan_market_async(markets=markets))
    except Exception as e:
        logger.error(f"Async tarama hatasi: {e}")
        logger.info("Sync taramaya geri donuluyor...")
        from market_scanner import scan_market

        scan_market(markets=markets)


def start_bot(use_async: bool = True) -> None:
    """
    Boot bot, configure scheduler, and run loop.
    """
    from command_handler import check_commands
    from db_session import init_db
    from market_scanner import get_scan_count, scan_market

    mode = "Async" if use_async else "Sync"
    logger.info(f"Bot baslatiliyor... ({mode} mode)")
    print(f"Bot baslatiliyor... ({mode} mode)")

    try:
        init_db()
        logger.info("Bot baslangicinda veritabani semasi dogrulandi.")
    except Exception as e:
        logger.error(f"Veritabani baslatilamadi, bot durduruluyor: {e}")
        raise

    try:
        from health_api import start_health_server

        start_health_server(port=5000)
        logger.info("Health API: http://localhost:5000")
    except Exception as e:
        logger.warning(f"Health API baslatilamadi: {e}")

    welcome_msg = (
        f"Bot baslatildi ({mode} mode)\n"
        "Komutlar:\n"
        "- /durum\n"
        "- /tara (sync)\n"
        "- /asynctara (async)\n"
        "- /analiz SEMBOL\n"
        "- /health\n"
        "- /portfoy\n"
        "- /islemler\n"
        "- /cache\n\n"
        "Planli Taramalar (TR):\n"
        f"BIST: {', '.join(BIST_SCAN_TIMES_TR)}\n"
        f"Kripto: {', '.join(CRYPTO_SCAN_TIMES_TR)}"
    )
    send_message(welcome_msg)

    def run_sync_scan(markets: str | list[str] | tuple[str, ...] | set[str] | None = None):
        scan_market(check_commands_callback=check_commands_wrapper, markets=markets)

    def run_manual_sync_full_scan():
        run_sync_scan(markets={"BIST", "Kripto"})

    def run_scheduled_bist_scan():
        if use_async:
            run_async_scan_wrapper(markets={"BIST"})
        else:
            run_sync_scan(markets={"BIST"})

    def run_scheduled_crypto_scan():
        if use_async:
            run_async_scan_wrapper(markets={"Kripto"})
        else:
            run_sync_scan(markets={"Kripto"})

    def check_commands_wrapper():
        check_commands(
            scan_market_callback=run_manual_sync_full_scan,
            get_scan_count_callback=get_scan_count,
        )

    # Startup: run only health check. Scans will start at fixed times.
    run_special_tag_health_check()

    setup_scheduler(
        scan_bist_func=run_scheduled_bist_scan, scan_crypto_func=run_scheduled_crypto_scan
    )
    run_bot_loop(run_manual_sync_full_scan, check_commands_wrapper)


if __name__ == "__main__":
    start_bot(use_async=False)
