from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from middleware.domain.enums import TrancheStatus
from middleware.infra.models import Tranche
from middleware.infra.time import UTC


@dataclass(slots=True)
class SellFillResult:
    applied_lots: int
    realized_pnl: Decimal
    tranche: Tranche


class TrancheRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, tranche_id: int, *, for_update: bool = False) -> Tranche | None:
        stmt = select(Tranche).where(Tranche.id == tranche_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def count_open(self, symbol: str) -> int:
        stmt = select(func.count(Tranche.id)).where(
            Tranche.symbol == symbol.upper(),
            Tranche.status == TrancheStatus.OPEN.value,
            Tranche.remaining_lots > 0,
        )
        return int(self.session.execute(stmt).scalar() or 0)

    def get_symbol_exposure_tl(self, symbol: str) -> Decimal:
        stmt = select(
            func.coalesce(func.sum(Tranche.entry_price * Tranche.remaining_lots), 0)
        ).where(
            Tranche.symbol == symbol.upper(),
            Tranche.status == TrancheStatus.OPEN.value,
            Tranche.remaining_lots > 0,
        )
        value = self.session.execute(stmt).scalar()
        return Decimal(str(value or 0))

    def oldest_open(self, symbol: str, *, for_update: bool = False) -> Tranche | None:
        stmt = (
            select(Tranche)
            .where(
                Tranche.symbol == symbol.upper(),
                Tranche.status == TrancheStatus.OPEN.value,
                Tranche.remaining_lots > 0,
            )
            .order_by(Tranche.entry_time.asc(), Tranche.id.asc())
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return self.session.execute(stmt).scalar_one_or_none()

    def lock_symbol_open_tranches(self, symbol: str) -> None:
        stmt = (
            select(Tranche.id)
            .where(
                Tranche.symbol == symbol.upper(),
                Tranche.status == TrancheStatus.OPEN.value,
                Tranche.remaining_lots > 0,
            )
            .with_for_update()
        )
        self.session.execute(stmt)

    def get_or_create_by_open_order(
        self,
        *,
        open_order_id: int,
        symbol: str,
        signal_code: str,
        entry_time: datetime,
        requested_lots: int,
        initial_entry_price: Decimal,
    ) -> Tranche:
        stmt = select(Tranche).where(Tranche.open_order_id == open_order_id)
        tranche = self.session.execute(stmt).scalar_one_or_none()
        if tranche:
            return tranche

        tranche = Tranche(
            symbol=symbol.upper(),
            signal_code=signal_code,
            entry_price=initial_entry_price,
            entry_time=entry_time,
            requested_lots=requested_lots,
            filled_lots=0,
            remaining_lots=0,
            status=TrancheStatus.OPEN.value,
            open_order_id=open_order_id,
            close_order_id=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        self.session.add(tranche)
        self.session.flush()
        return tranche

    def apply_buy_fill(
        self,
        *,
        open_order_id: int,
        symbol: str,
        signal_code: str,
        fill_lots: int,
        fill_price: Decimal,
        fill_time: datetime,
        requested_lots: int,
    ) -> Tranche:
        tranche = self.get_or_create_by_open_order(
            open_order_id=open_order_id,
            symbol=symbol,
            signal_code=signal_code,
            entry_time=fill_time,
            requested_lots=requested_lots,
            initial_entry_price=fill_price,
        )
        fill_lots = int(max(0, fill_lots))
        if fill_lots == 0:
            return tranche

        previous_filled = int(tranche.filled_lots)
        new_total = previous_filled + fill_lots
        if new_total > 0:
            weighted = (tranche.entry_price * previous_filled) + (fill_price * fill_lots)
            tranche.entry_price = weighted / Decimal(new_total)

        tranche.filled_lots = new_total
        tranche.remaining_lots = int(tranche.remaining_lots) + fill_lots
        tranche.status = (
            TrancheStatus.OPEN.value if tranche.remaining_lots > 0 else TrancheStatus.CLOSED.value
        )
        tranche.updated_at = datetime.now(UTC)
        self.session.add(tranche)
        self.session.flush()
        return tranche

    def apply_sell_fill(
        self,
        *,
        close_order_id: int,
        target_tranche_id: int,
        fill_lots: int,
        fill_price: Decimal,
    ) -> SellFillResult:
        tranche = self.get(target_tranche_id, for_update=True)
        if tranche is None:
            raise ValueError(f"target tranche not found: {target_tranche_id}")

        fill_lots = int(max(0, fill_lots))
        fill_lots = min(fill_lots, int(tranche.remaining_lots))
        if fill_lots <= 0:
            return SellFillResult(applied_lots=0, realized_pnl=Decimal("0"), tranche=tranche)

        tranche.remaining_lots = int(tranche.remaining_lots) - fill_lots
        tranche.close_order_id = close_order_id
        tranche.status = (
            TrancheStatus.OPEN.value if tranche.remaining_lots > 0 else TrancheStatus.CLOSED.value
        )
        tranche.updated_at = datetime.now(UTC)
        self.session.add(tranche)
        self.session.flush()

        realized = (fill_price - tranche.entry_price) * Decimal(fill_lots)
        return SellFillResult(applied_lots=fill_lots, realized_pnl=realized, tranche=tranche)

    def list_open_tranches(self, symbol: str | None = None) -> list[Tranche]:
        stmt = select(Tranche).where(
            Tranche.status == TrancheStatus.OPEN.value,
            Tranche.remaining_lots > 0,
        )
        if symbol:
            stmt = stmt.where(Tranche.symbol == symbol.upper())
        stmt = stmt.order_by(Tranche.entry_time.asc(), Tranche.id.asc())
        return list(self.session.execute(stmt).scalars().all())

    def list_positions(self) -> list[dict[str, Decimal | int | str | None]]:
        weighted_numerator = func.sum(Tranche.entry_price * Tranche.remaining_lots)
        weighted_avg = case(
            (
                func.sum(Tranche.remaining_lots) > 0,
                weighted_numerator / func.sum(Tranche.remaining_lots),
            ),
            else_=None,
        )
        stmt = (
            select(
                Tranche.symbol.label("symbol"),
                func.count(Tranche.id).label("open_tranche_count"),
                func.sum(Tranche.remaining_lots).label("total_remaining_lots"),
                weighted_avg.label("weighted_avg_entry_price"),
            )
            .where(Tranche.status == TrancheStatus.OPEN.value, Tranche.remaining_lots > 0)
            .group_by(Tranche.symbol)
            .order_by(Tranche.symbol.asc())
        )
        rows = self.session.execute(stmt).mappings().all()
        return [
            {
                "symbol": str(row["symbol"]),
                "open_tranche_count": int(row["open_tranche_count"] or 0),
                "total_remaining_lots": int(row["total_remaining_lots"] or 0),
                "weighted_avg_entry_price": (
                    Decimal(str(row["weighted_avg_entry_price"]))
                    if row["weighted_avg_entry_price"] is not None
                    else None
                ),
            }
            for row in rows
        ]
