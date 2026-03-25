"""Health API endpoints for runtime observability."""

import threading
from datetime import datetime
from typing import Any

from flask import Flask, jsonify

from logger import get_logger

logger = get_logger(__name__)
app = Flask(__name__)

BOT_START_TIME = datetime.now()

# Legacy in-memory state retained for backward compatibility with callers.
_bot_status = {
    "is_running": True,
    "is_scanning": False,
    "last_scan_time": None,
    "error_count": 0,
    "last_error": None,
}

_SYNC_SCAN_COUNT_KEY = "sync_scan_count"
_SYNC_SIGNAL_COUNT_KEY = "sync_signal_count"
_ASYNC_SCAN_COUNT_KEY = "async_scan_count"
_ASYNC_SIGNAL_COUNT_KEY = "async_signal_count"
_RUNTIME_IS_RUNNING_KEY = "runtime_is_running"
_RUNTIME_IS_SCANNING_KEY = "runtime_is_scanning"
_RUNTIME_LAST_SCAN_TIME_KEY = "runtime_last_scan_time"
_RUNTIME_ERROR_COUNT_KEY = "runtime_error_count"
_RUNTIME_LAST_ERROR_KEY = "runtime_last_error"


def get_uptime_seconds() -> float:
    return (datetime.now() - BOT_START_TIME).total_seconds()


def update_status(key: str, value: Any) -> None:
    _bot_status[key] = value
    try:
        from ops_repository import set_bot_stat

        set_bot_stat(f"runtime_{key}", str(value))
    except Exception as exc:
        logger.debug("Runtime status persist skipped for key=%s: %s", key, exc)


def increment_counter(key: str) -> int:
    current = int(_bot_status.get(key, 0) or 0) + 1
    _bot_status[key] = current
    try:
        from ops_repository import increment_bot_stat_int

        current = increment_bot_stat_int(f"runtime_{key}", step=1)
    except Exception as exc:
        logger.debug("Runtime counter persist skipped for key=%s: %s", key, exc)
    return current


def _probe_database() -> bool:
    try:
        from sqlalchemy import text

        from db_session import get_session

        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Health DB probe failed.")
        return False


def _load_scanner_counters() -> dict[str, Any]:
    defaults = {
        "sync_scans": 0,
        "sync_signals": 0,
        "async_scans": 0,
        "async_signals": 0,
        "total_scans": 0,
        "total_signals": 0,
        "last_updated": None,
    }

    try:
        from ops_repository import get_bot_stat_int, get_bot_stats_last_updated

        sync_scans = get_bot_stat_int(_SYNC_SCAN_COUNT_KEY, default=0)
        sync_signals = get_bot_stat_int(_SYNC_SIGNAL_COUNT_KEY, default=0)
        async_scans = get_bot_stat_int(_ASYNC_SCAN_COUNT_KEY, default=0)
        async_signals = get_bot_stat_int(_ASYNC_SIGNAL_COUNT_KEY, default=0)

        last_updated = get_bot_stats_last_updated(
            (
                _SYNC_SCAN_COUNT_KEY,
                _SYNC_SIGNAL_COUNT_KEY,
                _ASYNC_SCAN_COUNT_KEY,
                _ASYNC_SIGNAL_COUNT_KEY,
            )
        )

        return {
            "sync_scans": int(sync_scans),
            "sync_signals": int(sync_signals),
            "async_scans": int(async_scans),
            "async_signals": int(async_signals),
            "total_scans": int(sync_scans) + int(async_scans),
            "total_signals": int(sync_signals) + int(async_signals),
            "last_updated": last_updated.isoformat() if last_updated else None,
        }
    except Exception as exc:
        logger.warning("Scanner counters could not be loaded from repository: %s", exc)
        return defaults


def _parse_stat_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _load_runtime_state_from_repo() -> dict[str, Any]:
    defaults = {
        "is_running": bool(_bot_status.get("is_running", True)),
        "is_scanning": bool(_bot_status.get("is_scanning", False)),
        "last_scan_time": _bot_status.get("last_scan_time"),
        "error_count": int(_bot_status.get("error_count", 0) or 0),
        "last_error": _bot_status.get("last_error"),
    }

    try:
        from ops_repository import (
            get_bot_stat,
            get_bot_stat_int,
            get_distributed_lock_state,
        )

        distributed_scan_lock = get_distributed_lock_state("scheduled_scan")
        is_running = _parse_stat_bool(get_bot_stat(_RUNTIME_IS_RUNNING_KEY), default=True)
        runtime_scanning = _parse_stat_bool(get_bot_stat(_RUNTIME_IS_SCANNING_KEY), default=False)
        last_scan_time = get_bot_stat(_RUNTIME_LAST_SCAN_TIME_KEY) or _bot_status.get(
            "last_scan_time"
        )
        error_count = get_bot_stat_int(_RUNTIME_ERROR_COUNT_KEY, default=0)
        last_error = get_bot_stat(_RUNTIME_LAST_ERROR_KEY)

        return {
            "is_running": bool(is_running),
            "is_scanning": bool(distributed_scan_lock.get("locked") or runtime_scanning),
            "last_scan_time": last_scan_time,
            "error_count": int(error_count),
            "last_error": last_error,
        }
    except Exception as exc:
        logger.warning("Runtime state load failed; using in-memory fallback: %s", exc)
        return defaults


@app.route("/")
def index():
    return jsonify(
        {
            "name": "Algo Trading Bot",
            "version": "1.0.0",
            "status": "running",
            "endpoints": ["/health", "/status", "/stats", "/signals", "/metrics"],
        }
    )


try:
    from prometheus_metrics import register_prometheus_endpoint

    register_prometheus_endpoint(app)
except ImportError:
    logger.debug("prometheus-client not installed; metrics endpoint disabled.")


@app.route("/health")
def health():
    uptime = get_uptime_seconds()
    db_ok = _probe_database()
    status = "healthy" if db_ok else "unhealthy"

    return jsonify(
        {
            "status": status,
            "database": "connected" if db_ok else "disconnected",
            "uptime_seconds": round(uptime, 2),
            "uptime_human": format_uptime(uptime),
            "timestamp": datetime.now().isoformat(),
        }
    ), (200 if db_ok else 503)


@app.route("/status")
def status():
    uptime = get_uptime_seconds()
    db_ok = _probe_database()
    counters = _load_scanner_counters()
    runtime_state = _load_runtime_state_from_repo()

    return jsonify(
        {
            "bot": {
                "is_running": bool(runtime_state.get("is_running", True)) and db_ok,
                "is_scanning": bool(runtime_state.get("is_scanning", False)),
                "uptime_seconds": round(uptime, 2),
                "uptime_human": format_uptime(uptime),
                "started_at": BOT_START_TIME.isoformat(),
                "database": "connected" if db_ok else "disconnected",
            },
            "scanning": {
                "last_scan_time": counters.get("last_updated")
                or runtime_state.get("last_scan_time"),
                "sync_scan_count": counters["sync_scans"],
                "async_scan_count": counters["async_scans"],
                "scan_count": counters["total_scans"],
                "signal_count": counters["total_signals"],
            },
            "errors": {
                "error_count": int(runtime_state.get("error_count", 0) or 0),
                "last_error": runtime_state.get("last_error"),
            },
            "timestamp": datetime.now().isoformat(),
        }
    )


@app.route("/stats")
def stats():
    try:
        from ops_repository import get_trade_stats
        from price_cache import price_cache

        counters = _load_scanner_counters()
        cache_stats = price_cache.get_stats()
        trade_stats = get_trade_stats()

        return jsonify(
            {
                "scanning": {
                    "total_scans": counters["total_scans"],
                    "total_signals": counters["total_signals"],
                    "sync_scans": counters["sync_scans"],
                    "async_scans": counters["async_scans"],
                },
                "cache": {
                    "entries": cache_stats["cache_entries"],
                    "hit_rate": round(cache_stats["hit_rate"], 2),
                    "api_calls_saved": cache_stats["api_calls_saved"],
                },
                "trading": trade_stats,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception:
        logger.exception("Health stats endpoint failed.")
        return jsonify({"error": "stats_unavailable", "timestamp": datetime.now().isoformat()}), 500


@app.route("/signals")
def signals():
    try:
        from ops_repository import get_recent_signals

        signals_list = get_recent_signals(limit=20)

        return jsonify(
            {
                "count": len(signals_list),
                "signals": signals_list,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception:
        logger.exception("Health signals endpoint failed.")
        return jsonify({"error": "signals_unavailable"}), 500


def format_uptime(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def start_health_server(host: str | None = None, port: int | None = None) -> threading.Thread:
    from settings import settings

    host = host or settings.health_api_host
    port = port or settings.health_api_port

    def run_server():
        import logging

        logging.getLogger("werkzeug").setLevel(logging.ERROR)
        logger.info("Health API started: http://%s:%s", host, port)
        app.run(host=host, port=port, debug=False, use_reloader=False)

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    logger.info("Health API: http://localhost:5000")
    app.run(debug=True, port=5000)
