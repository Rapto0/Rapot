"""Health API endpoints for runtime observability."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from flask import Flask, jsonify, request

from api.contracts.health_contract import build_health_payload, format_uptime
from logger import get_logger
from state_keys import (
    ASYNC_SCAN_COUNT_KEY,
    ASYNC_SIGNAL_COUNT_KEY,
    RUNTIME_ERROR_COUNT_KEY,
    RUNTIME_IS_RUNNING_KEY,
    RUNTIME_LAST_ERROR_KEY,
    RUNTIME_LAST_SCAN_TIME_KEY,
    SYNC_SCAN_COUNT_KEY,
    SYNC_SIGNAL_COUNT_KEY,
)

logger = get_logger(__name__)
app = Flask(__name__)

BOT_START_TIME = datetime.now()

# Legacy in-memory state retained for backward compatibility with callers.
_bot_status = {
    "is_running": None,
    "is_scanning": None,
    "last_scan_time": None,
    "error_count": 0,
    "last_error": None,
}
_runtime_lock = threading.Lock()
_runtime_lifecycle: dict[str, Any] = {"phase": "unknown", "owner": None}


def begin_bot_runtime() -> None:
    """Bind status to this process's scheduler, not a persisted flag from an old run."""
    with _runtime_lock:
        _runtime_lifecycle.update(
            phase="starting", owner=threading.current_thread(), active_scans=0
        )


def mark_bot_runtime_running() -> None:
    with _runtime_lock:
        if _runtime_lifecycle.get("owner") is threading.current_thread():
            _runtime_lifecycle["phase"] = "running"


def end_bot_runtime() -> None:
    with _runtime_lock:
        if _runtime_lifecycle.get("owner") is threading.current_thread():
            _runtime_lifecycle["phase"] = "stopped"


@contextmanager
def track_bot_scan() -> Iterator[None]:
    """Observe active scan calls in this process, without trusting an old database lease."""
    with _runtime_lock:
        _runtime_lifecycle["active_scans"] = _runtime_lifecycle.get("active_scans", 0) + 1
    try:
        yield
    finally:
        with _runtime_lock:
            _runtime_lifecycle["active_scans"] -= 1


def _observe_bot_runtime() -> dict[str, Any]:
    with _runtime_lock:
        phase = _runtime_lifecycle.get("phase")
        owner = _runtime_lifecycle.get("owner")
        active_scans = _runtime_lifecycle.get("active_scans", 0)
    is_running = None
    if phase == "stopped":
        is_running = False
    elif phase == "running" and owner is not None and owner.is_alive():
        is_running = True
    return {
        "is_running": is_running,
        "is_scanning": bool(active_scans)
        if is_running is True
        else False
        if is_running is False
        else None,
        "state_source": "local_lifecycle" if owner is not None else "unverified_repository",
        "observed_at": datetime.now(UTC).isoformat() if owner is not None else None,
    }


def get_uptime_seconds() -> float:
    return (datetime.now() - BOT_START_TIME).total_seconds()


def update_status(key: str, value: Any) -> None:
    _bot_status[key] = value
    try:
        from infrastructure.persistence.ops_repository import set_bot_stat

        set_bot_stat(f"runtime_{key}", str(value))
    except Exception as exc:
        logger.debug("Runtime status persist skipped for key=%s: %s", key, exc)


def increment_counter(key: str) -> int:
    current = int(_bot_status.get(key, 0) or 0) + 1
    _bot_status[key] = current
    try:
        from infrastructure.persistence.ops_repository import increment_bot_stat_int

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
        "sync_scans": None,
        "sync_signals": None,
        "async_scans": None,
        "async_signals": None,
        "total_scans": None,
        "total_signals": None,
        "last_updated": None,
        "last_scan_time": None,
        "data_available": False,
        "last_scan_available": False,
    }

    try:
        from application.services.system_service import list_recent_scans
        from infrastructure.persistence.ops_repository import (
            get_bot_stat,
            get_bot_stats_last_updated,
        )

        sync_scans = _parse_stat_count(get_bot_stat(SYNC_SCAN_COUNT_KEY))
        sync_signals = _parse_stat_count(get_bot_stat(SYNC_SIGNAL_COUNT_KEY))
        async_scans = _parse_stat_count(get_bot_stat(ASYNC_SCAN_COUNT_KEY))
        async_signals = _parse_stat_count(get_bot_stat(ASYNC_SIGNAL_COUNT_KEY))
        counters_available = all(
            value is not None for value in (sync_scans, sync_signals, async_scans, async_signals)
        )

        last_updated = get_bot_stats_last_updated(
            (
                SYNC_SCAN_COUNT_KEY,
                SYNC_SIGNAL_COUNT_KEY,
                ASYNC_SCAN_COUNT_KEY,
                ASYNC_SIGNAL_COUNT_KEY,
            )
        )
        recent_scans = list_recent_scans(1)
        last_scan_time = recent_scans[0].get("created_at") if recent_scans else None
        if last_scan_time:
            parsed = datetime.fromisoformat(last_scan_time)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            last_scan_time = parsed.astimezone(UTC).isoformat()

        return {
            "sync_scans": sync_scans,
            "sync_signals": sync_signals,
            "async_scans": async_scans,
            "async_signals": async_signals,
            "total_scans": sync_scans + async_scans
            if sync_scans is not None and async_scans is not None
            else None,
            "total_signals": sync_signals + async_signals
            if sync_signals is not None and async_signals is not None
            else None,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "last_scan_time": last_scan_time,
            "data_available": counters_available,
            "last_scan_available": True,
        }
    except Exception as exc:
        logger.warning("Scanner counters could not be loaded from repository: %s", exc)
        return defaults


def _parse_stat_bool(raw_value: str | None) -> bool | None:
    normalized = str(raw_value).strip().lower() if raw_value is not None else ""
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _parse_stat_count(raw_value: str | None) -> int | None:
    try:
        value = int(str(raw_value).strip())
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None


def _parse_query_bool(key: str, default: bool = False) -> bool:
    raw_value = request.args.get(key)
    if raw_value is None:
        return default
    return str(raw_value).strip().lower() in {"1", "true", "yes", "on"}


def _load_runtime_state_from_repo() -> dict[str, Any]:
    defaults = {
        "is_running": None,
        "is_scanning": None,
        "last_reported_is_running": None,
        "state_source": "unavailable",
        "observed_at": None,
        "last_scan_time": _bot_status.get("last_scan_time"),
        "error_count": None,
        "last_error": _bot_status.get("last_error"),
    }

    try:
        from infrastructure.persistence.ops_repository import (
            get_bot_stat,
        )

        last_reported_is_running = _parse_stat_bool(get_bot_stat(RUNTIME_IS_RUNNING_KEY))
        observation = _observe_bot_runtime()
        last_scan_time = get_bot_stat(RUNTIME_LAST_SCAN_TIME_KEY) or _bot_status.get(
            "last_scan_time"
        )
        error_count = _parse_stat_count(get_bot_stat(RUNTIME_ERROR_COUNT_KEY))
        last_error = get_bot_stat(RUNTIME_LAST_ERROR_KEY)

        return {
            **observation,
            "last_reported_is_running": last_reported_is_running,
            "last_scan_time": last_scan_time,
            "error_count": error_count,
            "last_error": last_error,
        }
    except Exception as exc:
        logger.warning("Runtime state unavailable (%s).", type(exc).__name__)
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
    runtime_state = _load_runtime_state_from_repo()
    status = "healthy" if db_ok else "unhealthy"
    running = runtime_state.get("is_running") if db_ok else None
    realtime_status = "running" if running is True else "stopped" if running is False else "unknown"

    payload = build_health_payload(
        status=status,
        uptime_seconds=uptime,
        database="connected" if db_ok else "disconnected",
        realtime=realtime_status,
        version="1.0.0",
    )

    return jsonify(payload), (200 if db_ok else 503)


@app.route("/status")
def status():
    uptime = get_uptime_seconds()
    db_ok = _probe_database()
    counters = _load_scanner_counters()
    runtime_state = _load_runtime_state_from_repo()
    running = runtime_state.get("is_running") if db_ok else None
    state = "running" if running is True else "stopped" if running is False else "unknown"
    counters_available = db_ok and counters.get("data_available", True)
    last_scan_available = db_ok and counters.get("last_scan_available", False)
    include_compat_telemetry = _parse_query_bool("include_compat_telemetry", default=False)
    include_wrapper_details = _parse_query_bool("include_wrapper_details", default=False)

    payload = {
        "bot": {
            "is_running": running,
            "state": state,
            "state_source": runtime_state.get("state_source", "unavailable")
            if db_ok
            else "unavailable",
            "observed_at": runtime_state.get("observed_at") if db_ok else None,
            "last_reported_is_running": runtime_state.get("last_reported_is_running"),
            "is_scanning": runtime_state.get("is_scanning") if db_ok else None,
            "uptime_seconds": round(uptime, 2),
            "uptime_human": format_uptime(uptime),
            "started_at": BOT_START_TIME.isoformat(),
            "database": "connected" if db_ok else "disconnected",
        },
        "scanning": {
            "data_available": counters_available,
            "last_scan_available": last_scan_available,
            "last_scan_time": counters.get("last_scan_time") if last_scan_available else None,
            "counters_updated_at": counters.get("last_updated") if counters_available else None,
            "sync_scan_count": counters["sync_scans"] if counters_available else None,
            "async_scan_count": counters["async_scans"] if counters_available else None,
            "scan_count": counters["total_scans"] if counters_available else None,
            "signal_count": counters["total_signals"] if counters_available else None,
        },
        "errors": {
            "error_count": runtime_state.get("error_count")
            if db_ok and runtime_state.get("state_source") != "unavailable"
            else None,
            "last_error": runtime_state.get("last_error") if db_ok else None,
        },
        "timestamp": datetime.now().isoformat(),
    }

    if include_compat_telemetry:
        try:
            from infrastructure.compat import build_wrapper_usage_summary
            from settings import settings

            app_env = str(settings.app_env or "production").strip().lower()
            details_included = bool(include_wrapper_details and app_env != "production")
            telemetry = build_wrapper_usage_summary(
                include_details=details_included,
                detail_limit=20,
            )
            telemetry["details_requested"] = bool(include_wrapper_details)
            telemetry["details_included"] = bool(details_included)
            if include_wrapper_details and not details_included:
                telemetry["details_hidden_reason"] = "details_disabled_in_production"
            payload["compatibility_wrappers"] = telemetry
        except Exception:
            logger.exception("Compatibility wrapper telemetry build failed for /status.")

    return jsonify(payload)


@app.route("/stats")
def stats():
    try:
        from infrastructure.persistence.ops_repository import get_trade_stats
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
        from infrastructure.persistence.ops_repository import get_recent_signals

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
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
