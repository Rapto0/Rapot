"""
Runtime signal publishing adapter.

Domain modules (scanner) publish through this adapter so they do not import API transport modules.
"""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import Any

from logger import get_logger

logger = get_logger(__name__)

SignalPublisher = Callable[[dict[str, Any]], bool]

_publisher_lock = RLock()
_publisher: SignalPublisher | None = None


def register_signal_publisher(publisher: SignalPublisher | None) -> None:
    """
    Register or clear runtime signal publisher.
    """
    global _publisher
    with _publisher_lock:
        _publisher = publisher


def publish_signal_event(payload: dict[str, Any]) -> bool:
    """
    Publish signal via registered transport publisher.
    Returns False when no publisher is active.
    """
    with _publisher_lock:
        current_publisher = _publisher

    if current_publisher is None:
        logger.debug("Signal publish skipped: no runtime publisher registered.")
        return False

    try:
        return bool(current_publisher(payload))
    except Exception:
        logger.exception("Signal publish adapter failed.")
        return False
