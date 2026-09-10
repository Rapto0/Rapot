"""Per-invocation scanner accounting and one terminal history write.

Only completed inserts count as signals. Context-local accounting keeps manual
analyses and concurrent scan invocations from borrowing each other's counters.
Async child tasks share their parent's progress object while it is active.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from infrastructure.persistence.ops_repository import save_scan_history
from logger import get_logger

logger = get_logger(__name__)


@dataclass
class ScanProgress:
    scan_type: str
    mode: str
    symbols_scanned: int = 0
    signals_found: int = 0
    errors_count: int = 0
    status: str = "success"
    duration_seconds: float = 0.0
    history_id: int | None = None
    started_at: float = field(default_factory=lambda: time.monotonic())
    finished: bool = False


_current_scan: ContextVar[ScanProgress | None] = ContextVar("current_scan", default=None)


def record_signal_saved() -> None:
    progress = _current_scan.get()
    if progress is not None and not progress.finished:
        progress.signals_found += 1


def record_scan_error(count: int = 1) -> None:
    progress = _current_scan.get()
    if progress is not None and not progress.finished:
        progress.errors_count += max(0, count)


@contextmanager
def suspend_scan_tracking() -> Iterator[None]:
    """Keep command callbacks/manual analysis out of the scheduled scan totals."""
    token = _current_scan.set(None)
    try:
        yield
    finally:
        _current_scan.reset(token)


@contextmanager
def track_scan(*, markets: set[str], mode: str) -> Iterator[ScanProgress]:
    """Record once on normal return, failure or cooperative cancellation.

    A process kill cannot run finally; this is terminal history, not a durable
    in-progress job queue. Failure to write history is logged without masking
    an original exception or rolling back previously committed signals.
    """
    scan_type = "Full" if len(markets) > 1 else next(iter(markets))
    progress = ScanProgress(scan_type=scan_type, mode=mode)
    token = _current_scan.set(progress)
    try:
        yield progress
    except (asyncio.CancelledError, KeyboardInterrupt, SystemExit):
        progress.status = "cancelled"
        raise
    except BaseException:
        progress.status = "failed"
        progress.errors_count += 1
        raise
    finally:
        progress.finished = True
        progress.duration_seconds = max(0.0, time.monotonic() - progress.started_at)
        if progress.status == "success" and progress.errors_count:
            progress.status = "partial"
        _current_scan.reset(token)
        try:
            progress.history_id = save_scan_history(
                scan_type=progress.scan_type,
                mode=progress.mode,
                symbols_scanned=progress.symbols_scanned,
                signals_found=progress.signals_found,
                errors_count=progress.errors_count,
                duration_seconds=progress.duration_seconds,
                status=progress.status,
            )
        except Exception:
            logger.exception("Tarama gecmisi kaydedilemedi; onceki sinyaller korundu.")
