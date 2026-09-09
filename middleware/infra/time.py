from __future__ import annotations

import datetime as dt

# Python 3.10/3.11+ compatible UTC tzinfo.
try:
    UTC = dt.UTC
except AttributeError:
    UTC = dt.timezone.utc  # noqa: UP017


def datetime_from_unix_ms(timestamp_ms: int) -> dt.datetime:
    """Convert validated integer milliseconds without float rounding or OS time limits."""
    return dt.datetime(1970, 1, 1, tzinfo=UTC) + dt.timedelta(milliseconds=timestamp_ms)
