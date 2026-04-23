from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from middleware.infra.models import ExecutionReport


class ExecutionReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(
        self,
        *,
        order_id: int,
        event_type: str,
        status: str | None,
        message: str | None,
        payload: dict[str, Any] | None = None,
    ) -> ExecutionReport:
        entity = ExecutionReport(
            order_id=order_id,
            event_type=event_type,
            status=status,
            message=message,
            payload_json=payload,
        )
        self.session.add(entity)
        self.session.flush()
        return entity

    def list_for_order(self, order_id: int) -> list[ExecutionReport]:
        stmt = (
            select(ExecutionReport)
            .where(ExecutionReport.order_id == order_id)
            .order_by(ExecutionReport.id.asc())
        )
        return list(self.session.execute(stmt).scalars().all())
