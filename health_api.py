"""
Health Check API Modülü
Bot durumu için HTTP endpoint'leri.
"""

import threading
from datetime import datetime

from flask import Flask, jsonify

from logger import get_logger

logger = get_logger(__name__)

app = Flask(__name__)

# Bot başlangıç zamanı
BOT_START_TIME = datetime.now()

# Global durum (diğer modüllerden güncellenir)
_bot_status = {
    "is_running": True,
    "is_scanning": False,
    "last_scan_time": None,
    "scan_count": 0,
    "signal_count": 0,
    "error_count": 0,
    "last_error": None,
}


def get_uptime_seconds() -> float:
    """Bot uptime'ını saniye cinsinden döndürür."""
    return (datetime.now() - BOT_START_TIME).total_seconds()


def update_status(key: str, value) -> None:
    """Bot durumunu günceller."""
    _bot_status[key] = value


def increment_counter(key: str) -> int:
    """Sayacı artırır."""
    _bot_status[key] = _bot_status.get(key, 0) + 1
    return _bot_status[key]


@app.route("/")
def index():
    """Ana sayfa."""
    return jsonify(
        {
            "name": "Algo Trading Bot",
            "version": "1.0.0",
            "status": "running",
            "endpoints": ["/health", "/status", "/stats", "/signals", "/metrics"],
        }
    )


# Prometheus endpoint'i kaydet
try:
    from prometheus_metrics import register_prometheus_endpoint

    register_prometheus_endpoint(app)
except ImportError:
    pass  # prometheus-client yoksa sessizce geç


@app.route("/health")
def health():
    """
    Health check endpoint.
    Basit sağlık kontrolü - bot çalışıyor mu?
    """
    uptime = get_uptime_seconds()

    return jsonify(
        {
            "status": "healthy" if _bot_status["is_running"] else "unhealthy",
            "uptime_seconds": round(uptime, 2),
            "uptime_human": format_uptime(uptime),
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/status")
def status():
    """
    Detaylı bot durumu.
    """
    uptime = get_uptime_seconds()

    return jsonify(
        {
            "bot": {
                "is_running": _bot_status["is_running"],
                "is_scanning": _bot_status["is_scanning"],
                "uptime_seconds": round(uptime, 2),
                "uptime_human": format_uptime(uptime),
                "started_at": BOT_START_TIME.isoformat(),
            },
            "scanning": {
                "last_scan_time": _bot_status["last_scan_time"],
                "scan_count": _bot_status["scan_count"],
                "signal_count": _bot_status["signal_count"],
            },
            "errors": {
                "error_count": _bot_status["error_count"],
                "last_error": _bot_status["last_error"],
            },
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/stats")
def stats():
    """
    Bot istatistikleri.
    """
    try:
        from database import db
        from market_scanner import get_scan_count, get_signal_count
        from price_cache import price_cache

        cache_stats = price_cache.get_stats()
        trade_stats = db.get_trade_stats()

        return jsonify(
            {
                "scanning": {"total_scans": get_scan_count(), "total_signals": get_signal_count()},
                "cache": {
                    "entries": cache_stats["cache_entries"],
                    "hit_rate": round(cache_stats["hit_rate"], 2),
                    "api_calls_saved": cache_stats["api_calls_saved"],
                },
                "trading": trade_stats,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e), "timestamp": datetime.now().isoformat()}), 500


@app.route("/signals")
def signals():
    """Son sinyaller."""
    try:
        from database import get_recent_signals

        signals_list = get_recent_signals(limit=20)

        return jsonify(
            {
                "count": len(signals_list),
                "signals": signals_list,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def format_uptime(seconds: float) -> str:
    """Uptime'ı okunabilir formata çevirir."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def start_health_server(host: str | None = None, port: int | None = None) -> threading.Thread:
    """
    Health check sunucusunu ayrı thread'de başlatır.

    Args:
        host: Bind adresi (None ise settings'den alınır)
        port: Port numarası (None ise settings'den alınır)

    Returns:
        Server thread'i
    """
    from settings import settings

    # Settings'den varsayılan değerleri al
    host = host or settings.health_api_host
    port = port or settings.health_api_port

    def run_server():
        # Werkzeug uyarılarını sustur
        import logging

        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)

        logger.info(f"Health API başlatıldı: http://{host}:{port}")
        app.run(host=host, port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


# Test için
if __name__ == "__main__":
    print("Health API: http://localhost:5000")
    app.run(debug=True, port=5000)
