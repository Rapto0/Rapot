from __future__ import annotations

import hashlib


def build_client_order_id(idempotency_key: str) -> str:
    """Return a deterministic Binance-safe ID that includes the entire idempotency key."""
    digest = hashlib.sha256(idempotency_key.encode()).hexdigest().upper()
    return f"RAPOT-{digest[:30]}"
