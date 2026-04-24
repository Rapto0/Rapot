from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime
from typing import Any

from middleware.infra.settings import settings
from middleware.infra.time import UTC

_SENSITIVE_QUERY_RE = re.compile(
    r"(?i)([?&](?:token|access_token|webhook_token|api_key|key|secret)=)[^&\s\"]+"
)


def redact_sensitive_query_values(value: str) -> str:
    return _SENSITIVE_QUERY_RE.sub(r"\1<redacted>", value)


class SensitiveQueryFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_query_values(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(
                redact_sensitive_query_values(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        elif isinstance(record.args, dict):
            record.args = {
                key: redact_sensitive_query_values(value) if isinstance(value, str) else value
                for key, value in record.args.items()
            }
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_fields"):
            payload["extra"] = record.extra_fields
        return json.dumps(payload, ensure_ascii=True, default=str)


def _add_sensitive_query_filter(logger: logging.Logger) -> None:
    if not any(isinstance(existing, SensitiveQueryFilter) for existing in logger.filters):
        logger.addFilter(SensitiveQueryFilter())


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    _add_sensitive_query_filter(root)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(SensitiveQueryFilter())

    root.handlers.clear()
    root.addHandler(handler)

    _add_sensitive_query_filter(logging.getLogger("uvicorn.access"))
    _add_sensitive_query_filter(logging.getLogger("uvicorn.error"))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
