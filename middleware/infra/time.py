from __future__ import annotations

import datetime as dt

# Python 3.10/3.11+ compatible UTC tzinfo.
try:
    UTC = dt.UTC
except AttributeError:
    UTC = dt.timezone.utc  # noqa: UP017
