from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from middleware.domain.events import TradingViewWebhookPayload
from middleware.infra.models import SignalEvent
from middleware.infra.time import UTC


class SignalRepository:
    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def build_event_hash(payload: TradingViewWebhookPayload) -> str:
        canonical = json.dumps(
            payload.model_dump(mode="json", exclude_defaults=True),
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def get_by_event_hash(self, event_hash: str) -> SignalEvent | None:
        stmt = select(SignalEvent).where(SignalEvent.event_hash == event_hash)
        return self.session.execute(stmt).scalar_one_or_none()

    def create(self, payload: TradingViewWebhookPayload, event_hash: str) -> SignalEvent:
        bar_time = datetime.fromtimestamp(payload.barTime / 1000, tz=UTC)
        entity = SignalEvent(
            event_hash=event_hash,
            schema_version=payload.schemaVersion,
            source=payload.source,
            symbol=payload.symbol,
            ticker=payload.ticker,
            signal_code=payload.signalCode,
            signal_text=payload.signalText,
            side=payload.side.value,
            price=payload.price,
            timeframe=payload.timeframe,
            bar_time=bar_time,
            bar_index=payload.barIndex,
            is_realtime=payload.isRealtime,
            payload_json=payload.model_dump(mode="json"),
            received_at=datetime.now(UTC),
        )
        with self.session.begin_nested():
            self.session.add(entity)
            self.session.flush()
        return entity

    def create_or_get(
        self,
        payload: TradingViewWebhookPayload,
        *,
        event_hash: str,
    ) -> tuple[SignalEvent, bool]:
        existing = self.get_by_event_hash(event_hash)
        if existing is not None:
            return existing, False
        try:
            return self.create(payload, event_hash), True
        except IntegrityError:
            existing = self.get_by_event_hash(event_hash)
            if existing is None:
                raise
            return existing, False

    def list_signals(self, *, limit: int = 100, symbol: str | None = None) -> list[SignalEvent]:
        stmt = select(SignalEvent)
        if symbol:
            stmt = stmt.where(SignalEvent.symbol == symbol.upper())
        stmt = stmt.order_by(SignalEvent.id.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())
