"""UTC clock compatible with the main application's timezone-naive timestamps."""

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return current UTC without an offset, preserving legacy SQLite/API shapes.

    The main database stores naive UTC, not local wall time. Acquire an aware UTC
    instant before removing tzinfo; callers must not interpret this as local time.
    """
    return datetime.now(UTC).replace(tzinfo=None)
