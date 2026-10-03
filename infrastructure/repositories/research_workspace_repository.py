"""Owner-scoped persistence for portfolios and reusable research queries."""

from __future__ import annotations

import json
from datetime import UTC
from uuid import uuid4

from sqlalchemy import func, select, text

from db_session import get_session_factory
from infrastructure.time import utc_now_naive
from models import ResearchWorkspace


def _result(row: ResearchWorkspace) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "operation": row.operation,
        "params": json.loads(row.params_json),
        "updated_at": row.updated_at.replace(tzinfo=UTC).isoformat(),
    }


def list_workspaces(owner: str) -> list[dict]:
    with get_session_factory()() as session:
        rows = session.scalars(
            select(ResearchWorkspace)
            .where(ResearchWorkspace.owner == owner)
            .order_by(ResearchWorkspace.updated_at.desc(), ResearchWorkspace.id)
            .limit(100)
        )
        return [_result(row) for row in rows]


def save_workspace(owner: str, payload: dict, workspace_id: str | None = None) -> dict:
    with get_session_factory()() as session:
        session.execute(text("BEGIN IMMEDIATE"))
        row = None
        if workspace_id:
            row = session.scalar(
                select(ResearchWorkspace).where(
                    ResearchWorkspace.id == workspace_id, ResearchWorkspace.owner == owner
                )
            )
            if row is None:
                raise LookupError("Kayıt bulunamadı.")
        if row is None:
            count = session.scalar(
                select(func.count())
                .select_from(ResearchWorkspace)
                .where(ResearchWorkspace.owner == owner)
            )
            if count >= 100:
                raise ValueError("En fazla 100 araştırma kaydedilebilir.")
            row = ResearchWorkspace(id=str(uuid4()), owner=owner, created_at=utc_now_naive())
            session.add(row)
        row.name = payload["name"]
        row.operation = payload["operation"]
        row.params_json = json.dumps(payload["params"], ensure_ascii=False, allow_nan=False)
        row.updated_at = utc_now_naive()
        session.flush()
        result = _result(row)
        session.commit()
        return result


def delete_workspace(owner: str, workspace_id: str) -> None:
    with get_session_factory()() as session:
        row = session.scalar(
            select(ResearchWorkspace).where(
                ResearchWorkspace.id == workspace_id, ResearchWorkspace.owner == owner
            )
        )
        if row is None:
            raise LookupError("Kayıt bulunamadı.")
        session.delete(row)
        session.commit()
