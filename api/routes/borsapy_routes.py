"""Private, bounded borsapy research and chart endpoints."""

from __future__ import annotations

import json
import threading
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.auth import User, get_current_admin_user
from api.rate_limit import limiter
from api.routes.borsapy_connection_routes import PrivateRoute
from infrastructure.repositories import research_workspace_repository as saved

router = APIRouter(prefix="/borsapy", tags=["Borsapy research"], route_class=PrivateRoute)
_research_slots = threading.BoundedSemaphore(2)
_INTERVALS = Literal[
    "1m",
    "5m",
    "15m",
    "30m",
    "1h",
    "4h",
    "1d",
    "1wk",
    "1mo",
    "2d",
    "3d",
    "4d",
    "5d",
    "6d",
    "2wk",
    "3wk",
    "2mo",
    "3mo",
]
_INDEPENDENT_SOURCES = {
    "calendar",
    "fx.current",
    "fx.banks",
    "crypto.pairs",
    "crypto.current",
    "crypto.history",
    "fund.search",
    "fund.info",
    "fund.history",
    "fund.allocation",
    "fund.screen",
    "fund.compare",
    "fund.fees",
    "fund.tax",
    "inflation",
    "inflation.calculate",
    "evds.categories",
    "evds.groups",
    "evds.search",
    "evds.series",
    "bonds",
    "tcmb.rates",
    "tcmb.history",
    "eurobonds",
    "eurobond.history",
    "twitter.search",
}
_AUTHENTICATED_HISTORY = {
    "history",
    "replay",
    "heikin_ashi",
    "ta.indicators",
    "backtest",
    "portfolio",
}


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9_.]+$")
    params: dict[str, Any] = Field(default_factory=dict, max_length=20)

    @field_validator("params")
    @classmethod
    def bounded_params(cls, value: dict) -> dict:
        try:
            if len(json.dumps(value, allow_nan=False).encode("utf-8")) > 32_768:
                raise ValueError
        except (TypeError, ValueError, OverflowError, RecursionError) as exc:
            raise ValueError("Araştırma girdisi geçersiz veya çok büyük.") from exc
        return value


class SavedResearchWrite(ResearchQuery):
    name: str = Field(min_length=1, max_length=80)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(character) < 32 for character in value):
            raise ValueError("Geçerli bir kayıt adı girin.")
        return value


def _private(response: Response) -> None:
    response.headers["Cache-Control"] = "private, no-store"


def _validated(payload: ResearchQuery) -> dict:
    from application.services.borsapy_research import validate_params

    if payload.operation.startswith("stream."):
        raise HTTPException(422, "Bu işlem canlı akış panelinden başlatılır.")
    try:
        return validate_params(payload.operation, payload.params)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get("/catalog")
def research_catalog(response: Response, user: User = Depends(get_current_admin_user)) -> dict:
    from application.services.borsapy_catalog import get_catalog

    _private(response)
    return get_catalog()


@router.post("/query")
@limiter.limit("20/minute")
def research_query(
    request: Request,
    response: Response,
    payload: ResearchQuery,
    user: User = Depends(get_current_admin_user),
) -> dict:
    from application.services.borsapy_gateway import BorsapyGatewayError, get_borsapy_gateway
    from application.services.borsapy_research import run_operation

    params = _validated(payload)
    _private(response)
    if not _research_slots.acquire(blocking=False):
        raise HTTPException(429, "İki araştırma sürüyor. Tamamlanınca tekrar deneyin.")
    try:
        if payload.operation == "company.actions":
            # Pinned Ticker dividends/splits use only public İş Yatırım data;
            # actions combines them locally. Slow public I/O must not retain
            # the TradingView account lock, but still occupies a research slot.
            return get_borsapy_gateway().run_public(
                lambda bp: run_operation(bp, payload.operation, params)
            )
        fx_intraday = payload.operation == "fx.history" and params["interval"] not in {
            "1d",
            "1wk",
            "1mo",
        }
        uses_tv = payload.operation not in _INDEPENDENT_SOURCES
        if payload.operation == "fx.history":
            uses_tv = fx_intraday
        return get_borsapy_gateway().run(
            lambda bp: run_operation(bp, payload.operation, params),
            tradingview=uses_tv,
            require_auth=payload.operation in _AUTHENTICATED_HISTORY or fx_intraday,
        )
    except HTTPException:
        raise
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except Exception:
        # Provider errors may contain authenticated URLs, cookies or upstream bodies.
        raise HTTPException(
            502, "Veri alınamadı. Bağlantı durumunu ve bu özelliğin gereksinimlerini kontrol edin."
        ) from None
    finally:
        _research_slots.release()


@router.get("/candles/{symbol}")
@limiter.limit("30/minute")
def private_candles(
    request: Request,
    response: Response,
    symbol: str = Path(min_length=1, max_length=25, pattern=r"^[A-Za-z0-9]{1,20}(?:\.IS)?$"),
    interval: _INTERVALS = "1d",
    limit: int = Query(1000, ge=1, le=2000),
    user: User = Depends(get_current_admin_user),
) -> dict:
    from application.services.borsapy_gateway import BorsapyGatewayError
    from application.services.borsapy_market_data import get_borsapy_market_data

    _private(response)
    if not _research_slots.acquire(blocking=False):
        raise HTTPException(429, "Veri yükleniyor; biraz sonra tekrar deneyin.")
    try:
        return get_borsapy_market_data().candles(symbol, interval, limit)
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    except Exception:
        raise HTTPException(
            502, "TradingView mumları alınamadı. Hesap bağlantısını kontrol edin."
        ) from None
    finally:
        _research_slots.release()


@router.get("/saved")
def list_saved(response: Response, user: User = Depends(get_current_admin_user)) -> list[dict]:
    _private(response)
    return saved.list_workspaces(user.username)


def _save(user: User, payload: SavedResearchWrite, workspace_id: str | None = None) -> dict:
    values = payload.model_dump()
    values["params"] = _validated(payload)
    try:
        return saved.save_workspace(user.username, values, workspace_id)
    except LookupError:
        raise HTTPException(404, "Kayıt bulunamadı.") from None
    except ValueError:
        raise HTTPException(409, "Kayıt sınırına ulaşıldı.") from None


@router.post("/saved")
def create_saved(
    payload: SavedResearchWrite, response: Response, user: User = Depends(get_current_admin_user)
) -> dict:
    _private(response)
    return _save(user, payload)


@router.put("/saved/{workspace_id}")
def update_saved(
    workspace_id: str,
    payload: SavedResearchWrite,
    response: Response,
    user: User = Depends(get_current_admin_user),
) -> dict:
    _private(response)
    return _save(user, payload, workspace_id)


@router.delete("/saved/{workspace_id}")
def delete_saved(
    workspace_id: str, response: Response, user: User = Depends(get_current_admin_user)
) -> dict:
    try:
        saved.delete_workspace(user.username, workspace_id)
    except LookupError:
        raise HTTPException(404, "Kayıt bulunamadı.") from None
    _private(response)
    return {"deleted": True}
