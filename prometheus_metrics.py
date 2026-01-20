"""
Prometheus Metrics Modülü
Grafana/Prometheus için metrik endpoint'leri.
"""

import time

from flask import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

from logger import get_logger

logger = get_logger(__name__)

# Bot başlangıç zamanı
BOT_START_TIME = time.time()

# ==================== PROMETHEUS METRİKLERİ ====================

# Info metriği - bot bilgisi
bot_info = Info("trading_bot", "Trading bot information")
bot_info.info({"version": "1.0.0", "name": "Algo Trading Bot", "mode": "sync"})

# Gauge - anlık değerler
uptime_seconds = Gauge("trading_bot_uptime_seconds", "Bot uptime in seconds")

is_running = Gauge("trading_bot_is_running", "Bot running status (1=running, 0=stopped)")
is_running.set(1)

is_scanning = Gauge("trading_bot_is_scanning", "Bot scanning status (1=scanning, 0=idle)")

current_scan_progress = Gauge(
    "trading_bot_scan_progress", "Current scan progress percentage", ["market"]
)

cache_entries = Gauge("trading_bot_cache_entries", "Number of cached price entries")

cache_hit_rate = Gauge("trading_bot_cache_hit_rate", "Cache hit rate percentage")

open_trades = Gauge("trading_bot_open_trades", "Number of open trades")

# Counter - kümülatif sayaçlar
scans_total = Counter(
    "trading_bot_scans_total",
    "Total number of market scans",
    ["market"],  # BIST, Kripto
)

signals_total = Counter(
    "trading_bot_signals_total",
    "Total number of signals generated",
    ["strategy", "signal_type", "market"],  # COMBO/HUNTER, AL/SAT, BIST/Kripto
)

errors_total = Counter("trading_bot_errors_total", "Total number of errors", ["severity", "module"])

api_calls_total = Counter(
    "trading_bot_api_calls_total",
    "Total API calls made",
    ["api"],  # BIST, Binance, Telegram, Gemini
)

api_calls_saved = Counter("trading_bot_api_calls_saved_total", "API calls saved by cache")

# Histogram - dağılım ölçümü
scan_duration = Histogram(
    "trading_bot_scan_duration_seconds",
    "Scan duration in seconds",
    ["market"],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 1800],
)

signal_latency = Histogram(
    "trading_bot_signal_latency_seconds",
    "Time from data fetch to signal generation",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
)


# ==================== HELPER FONKSİYONLARI ====================


def update_uptime():
    """Uptime metriğini günceller."""
    uptime_seconds.set(time.time() - BOT_START_TIME)


def set_scanning(scanning: bool):
    """Tarama durumunu ayarlar."""
    is_scanning.set(1 if scanning else 0)


def record_scan_start(market: str):
    """Tarama başlangıcını kaydeder."""
    set_scanning(True)
    current_scan_progress.labels(market=market).set(0)


def record_scan_progress(market: str, progress: float):
    """Tarama ilerlemesini kaydeder (0-100)."""
    current_scan_progress.labels(market=market).set(progress)


def record_scan_complete(market: str, duration_seconds: float):
    """Tarama tamamlanmasını kaydeder."""
    scans_total.labels(market=market).inc()
    scan_duration.labels(market=market).observe(duration_seconds)
    current_scan_progress.labels(market=market).set(100)
    set_scanning(False)


def record_signal(strategy: str, signal_type: str, market: str):
    """Yeni sinyal kaydeder."""
    signals_total.labels(strategy=strategy, signal_type=signal_type, market=market).inc()


def record_error(severity: str, module: str):
    """Hata kaydeder."""
    errors_total.labels(severity=severity, module=module).inc()


def record_api_call(api: str, saved_by_cache: bool = False):
    """API çağrısı kaydeder."""
    if saved_by_cache:
        api_calls_saved.inc()
    else:
        api_calls_total.labels(api=api).inc()


def update_cache_metrics(entries: int, hit_rate: float):
    """Cache metriklerini günceller."""
    cache_entries.set(entries)
    cache_hit_rate.set(hit_rate)


def update_trades_metric(count: int):
    """Açık trade sayısını günceller."""
    open_trades.set(count)


# ==================== FLASK ENDPOINT ====================


def register_prometheus_endpoint(app):
    """
    Flask app'e Prometheus endpoint ekler.

    Args:
        app: Flask application instance
    """

    @app.route("/metrics")
    def metrics():
        """Prometheus metrics endpoint."""
        # Uptime güncelle
        update_uptime()

        # Cache metriklerini güncelle
        try:
            from price_cache import price_cache

            stats = price_cache.get_stats()
            update_cache_metrics(stats["cache_entries"], stats["hit_rate"])
        except Exception:
            pass

        # Trade metriklerini güncelle
        try:
            from database import db

            trades = db.get_open_trades()
            update_trades_metric(len(trades))
        except Exception:
            pass

        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    logger.info("Prometheus endpoint kaydedildi: /metrics")


# ==================== GRAFANA DASHBOARD JSON ====================

GRAFANA_DASHBOARD = {
    "title": "Trading Bot Dashboard",
    "panels": [
        {"title": "Uptime", "type": "stat", "target": "trading_bot_uptime_seconds"},
        {"title": "Signals/Hour", "type": "graph", "target": "rate(trading_bot_signals_total[1h])"},
        {"title": "Cache Hit Rate", "type": "gauge", "target": "trading_bot_cache_hit_rate"},
        {
            "title": "Scan Duration",
            "type": "histogram",
            "target": "trading_bot_scan_duration_seconds",
        },
    ],
}


def get_grafana_dashboard_json() -> dict:
    """Grafana dashboard JSON'ını döndürür."""
    return GRAFANA_DASHBOARD
