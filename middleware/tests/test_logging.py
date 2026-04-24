from __future__ import annotations

import logging

from middleware.infra.logging import SensitiveQueryFilter, redact_sensitive_query_values


def test_redact_sensitive_query_values_masks_token_like_params():
    url = "/webhooks/tradingview?token=secret-token&symbol=THYAO"

    assert (
        redact_sensitive_query_values(url) == "/webhooks/tradingview?token=<redacted>&symbol=THYAO"
    )


def test_sensitive_query_filter_redacts_uvicorn_access_args():
    record = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=(
            "127.0.0.1:12345",
            "POST",
            "/webhooks/tradingview?token=secret-token",
            "1.1",
            200,
        ),
        exc_info=None,
    )

    SensitiveQueryFilter().filter(record)

    assert record.args[2] == "/webhooks/tradingview?token=<redacted>"
