from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SignalDomainEvent:
    symbol: str
    market_type: str
    strategy: str
    signal_type: str
    timeframe: str
    score: str
    price: float
    details: dict[str, Any] | None = None
    special_tag: str | None = None

    def to_save_kwargs(self, *, serialized_details: str | None) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "market_type": self.market_type,
            "strategy": self.strategy,
            "signal_type": self.signal_type,
            "timeframe": self.timeframe,
            "score": self.score,
            "price": self.price,
            "details": serialized_details,
            "special_tag": self.special_tag,
        }

    def to_payload_kwargs(self) -> dict[str, Any]:
        payload = {
            "symbol": self.symbol,
            "market_type": self.market_type,
            "strategy": self.strategy,
            "signal_type": self.signal_type,
            "timeframe": self.timeframe,
            "score": self.score,
            "price": self.price,
        }
        if self.special_tag:
            payload["special_tag"] = self.special_tag
        return payload
