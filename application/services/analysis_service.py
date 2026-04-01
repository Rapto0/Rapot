from __future__ import annotations

from typing import Any

from infrastructure.repositories.analysis_repository import (
    get_ai_analysis_by_id as repo_get_ai_analysis_by_id,
)
from infrastructure.repositories.analysis_repository import (
    get_ai_analysis_by_signal_id as repo_get_ai_analysis_by_signal_id,
)
from infrastructure.repositories.analysis_repository import (
    list_ai_analyses as repo_list_ai_analyses,
)


def list_ai_analyses(
    *,
    symbol: str | None,
    market_type: str | None,
    limit: int,
) -> list[Any]:
    return repo_list_ai_analyses(symbol=symbol, market_type=market_type, limit=limit)


def get_ai_analysis_by_id(analysis_id: int) -> Any | None:
    return repo_get_ai_analysis_by_id(analysis_id)


def get_ai_analysis_by_signal_id(signal_id: int) -> Any | None:
    return repo_get_ai_analysis_by_signal_id(signal_id)
