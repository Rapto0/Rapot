from __future__ import annotations

from typing import Any


def list_ai_analyses(*, symbol: str | None, market_type: str | None, limit: int) -> list[Any]:
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        query = session.query(AIAnalysis)

        if symbol:
            query = query.filter(AIAnalysis.symbol == symbol.upper())
        if market_type:
            query = query.filter(AIAnalysis.market_type == market_type)

        return query.order_by(AIAnalysis.created_at.desc()).limit(limit).all()


def get_ai_analysis_by_id(analysis_id: int) -> Any | None:
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        return session.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()


def get_ai_analysis_by_signal_id(signal_id: int) -> Any | None:
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        return session.query(AIAnalysis).filter(AIAnalysis.signal_id == signal_id).first()
