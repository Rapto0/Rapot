"""Approved, dated KAP share membership; never a trading-status assertion.

The 12 October user audit is independently identical to the stored 14 October
official KAP pay-market snapshot. General company/issuer codes are retained in
the source registry but are not the automatic share universe. Explicit user
watchlists, chart requests and provider symbol admission do not use this filter.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "bist_symbols.json"
SNAPSHOT_SHA256 = "41e445c012ea682933708fbbaf5dcb0cc7a770c0e8ffb88057129e248b5a6b0f"


@dataclass(frozen=True, slots=True)
class ShareUniverse:
    symbols: tuple[str, ...]
    separated: tuple[tuple[str, str], ...]
    source_url: str
    audit_as_of: str
    official_corroborated_at: str

    def metadata(self) -> dict:
        return {
            "source": "kap_verified_share_snapshot",
            "state": "ready",
            "classification": "verified_equity_snapshot",
            "count": len(self.symbols),
            "source_total_count": len(self.symbols),
            "audit_as_of": self.audit_as_of,
            "official_corroborated_at": self.official_corroborated_at,
            "source_url": self.source_url,
            "source_snapshot_sha256": SNAPSHOT_SHA256,
            "separated_candidate_count": len(self.separated),
            "separated_candidate_classifications": dict(
                Counter(kind for _, kind in self.separated)
            ),
            "equity_membership_verified": True,
            "live_trading_status_verified": False,
            "provider_resolution_verified": False,
            "future_membership_guaranteed": False,
            "automatic_refresh": False,
        }


@lru_cache(maxsize=1)
def share_universe() -> ShareUniverse:
    """Load the reviewed packaged registry once; no network or silent fallback."""
    raw = SNAPSHOT_PATH.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA256:
        raise ValueError("BIST pay evreni dosyasının doğrulama özeti eşleşmiyor.")
    payload = json.loads(raw)
    symbols = tuple(payload["symbols"])
    separated = tuple(
        (row["symbol"], row["classification"]) for row in payload["separated_candidates"]
    )
    if (
        payload["schema"] != "rapot-bist-share-universe-v1"
        or len(set(symbols)) != 631
        or len(symbols) != 631
        or len(separated) != 174
        or len({symbol for symbol, _ in separated}) != 174
        or set(symbols).intersection(symbol for symbol, _ in separated)
    ):
        raise ValueError("BIST pay evreni kapsamı doğrulanamadı.")
    return ShareUniverse(
        symbols,
        separated,
        payload["source_url"],
        payload["audit_as_of"],
        payload["official_corroborated_at"],
    )
