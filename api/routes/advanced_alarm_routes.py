"""Private administrative API for persistent advanced alarms and watchlists."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.auth import User, get_current_admin_user
from api.rate_limit import limiter
from api.routes.alarm_routes import AlarmSymbol
from application.services.advanced_alarm_conditions import prepare_condition, validate_condition
from application.services.advanced_alarm_service import (
    get_advanced_alarm_engine,
    telegram_configured,
)
from infrastructure.repositories import advanced_alarm_repository as repository


class AlarmPrivateRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def private(request):
            try:
                response = await handler(request)
            except StarletteHTTPException as exc:
                response = JSONResponse(
                    {"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers
                )
            except RequestValidationError as exc:
                # Fixed validator messages help the form recover without echoing
                # submitted input, locations or exception context (credentials).
                details = [{"msg": str(error["msg"])[:300]} for error in exc.errors()[:3]]
                response = JSONResponse({"detail": details}, status_code=422)
            response.headers["Cache-Control"] = "private, no-store"
            return response

        return private


router = APIRouter(
    prefix="/advanced-alarms", tags=["Advanced alarms"], route_class=AlarmPrivateRoute
)
Timeframe = str


class WatchlistWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    symbols: list[AlarmSymbol] = Field(default_factory=list, max_length=2000)
    revision: int | None = Field(None, ge=1)

    @field_validator("name")
    @classmethod
    def name_is_safe(cls, value):
        value = value.strip()
        if not value or any(ord(c) < 32 for c in value):
            raise ValueError("Geçersiz ad.")
        return value

    @model_validator(mode="after")
    def unique_symbols(self):
        if len({(item.symbol, item.market_type) for item in self.symbols}) != len(self.symbols):
            raise ValueError("Semboller tekrarlanamaz.")
        return self


class AlarmWrite(WatchlistWrite):
    category: Literal["price", "technical", "watchlist"]
    scope: Literal["symbols", "watchlist", "all_bist"] = "symbols"
    watchlist_id: str | None = Field(None, max_length=36)
    timeframe: Timeframe = "1d"
    trigger: Literal["intrabar", "bar_close"] = "intrabar"
    condition: dict
    mode: Literal["on_enter", "once_per_bar", "cooldown"] = "on_enter"
    cooldown_seconds: int = Field(60, ge=1, le=86400)
    enabled: bool = True
    notify_telegram: bool = False

    @model_validator(mode="after")
    def consistent_scope(self):
        from application.services.custom_indicators.catalog import ALIASES, canonical_timeframe

        base = canonical_timeframe(self.timeframe)
        self.timeframe = next((alias for alias, native in ALIASES.items() if native == base), base)
        self.condition = validate_condition(self.condition)
        prepared = prepare_condition(self.condition, self.timeframe)
        if self.trigger != "bar_close" and any(
            ref["field"] == "custom"
            and ref["indicator"] != "htf_rsi_score"
            and ref["output"] in {"buy_signal", "sell_signal", "any_signal"}
            for ref in prepared.fields
        ):
            raise ValueError(
                "Snapshot ve N OY sinyalleri için 'Yalnız kapanmış mum' seçin; mum içinde skor veya oy çıktısını kullanabilirsiniz."
            )
        if self.category == "watchlist":
            if self.scope not in {"watchlist", "all_bist"} or self.symbols:
                raise ValueError("İzleme listesi alarmında kalıcı liste veya bütün BIST seçin.")
        elif self.scope != "symbols" or not self.symbols:
            raise ValueError("Fiyat/teknik alarm için açık sembol listesi gerekir.")
        if (self.scope == "watchlist") != bool(self.watchlist_id):
            raise ValueError("İzleme listesi kimliği kapsamla uyuşmuyor.")
        if self.scope == "all_bist" and self.watchlist_id:
            raise ValueError("Bütün BIST kapsamına liste kimliği verilemez.")
        if self.category == "price":

            def price_only(node):
                if node["op"] in {"and", "or"}:
                    return all(price_only(child) for child in node["children"])
                return all(
                    not isinstance(ref, dict) or ref.get("field") == "price"
                    for ref in (node["left"], node["right"])
                )

            if not price_only(self.condition):
                raise ValueError("Fiyat alarmında yalnız fiyat alanı kullanılabilir.")
        return self


class IndicatorPreview(AlarmSymbol):
    model_config = ConfigDict(extra="forbid")
    indicator: str = Field(max_length=40)
    inputs: dict = Field(default_factory=dict)
    chart_timeframe: str = Field("1D", max_length=10)

    @model_validator(mode="after")
    def valid_indicator(self):
        from application.services.custom_indicators.catalog import (
            canonical_timeframe,
            requirements,
            validate_config,
        )

        self.chart_timeframe = canonical_timeframe(self.chart_timeframe)
        self.inputs = validate_config(self.indicator, self.inputs, self.chart_timeframe)
        requirements(self.indicator, self.inputs, self.chart_timeframe)
        return self


@router.get("/indicators/catalog")
@limiter.limit("60/minute")
def indicator_catalog(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    from application.services.custom_indicators.catalog import catalog

    return catalog()


@router.post("/indicators/preview")
@limiter.limit("30/minute")
def indicator_preview(
    request: Request, payload: IndicatorPreview, user: User = Depends(get_current_admin_user)
) -> dict:
    return get_advanced_alarm_engine().hub.custom.preview(**payload.model_dump())


def _call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except repository.NotFound as exc:
        raise HTTPException(404, str(exc)) from None
    except repository.Conflict as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("")
@limiter.limit("120/minute")
def rules(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return {
        "rules": get_advanced_alarm_engine().rules(user.username),
        "limits": repository.LIMITS,
        "usage": repository.usage(user.username),
        "runtime": get_advanced_alarm_engine().status(user.username),
    }


@router.get("/status")
@limiter.limit("120/minute")
def status(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return get_advanced_alarm_engine().status(user.username)


@router.get("/events")
@limiter.limit("120/minute")
def events(
    request: Request,
    after_id: int | None = Query(None, ge=0),
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_current_admin_user),
) -> dict:
    return repository.events(user.username, after_id, limit)


@router.get("/heartbeat")
@limiter.limit("120/minute")
def heartbeat(
    request: Request,
    test_run_id: str | None = Query(None, pattern=r"^[a-f0-9]{32}$"),
    user: User = Depends(get_current_admin_user),
) -> dict:
    return get_advanced_alarm_engine().heartbeat(user.username, test_run_id=test_run_id)


@router.get("/coverage")
@limiter.limit("10/minute")
def coverage(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return get_advanced_alarm_engine().hub.coverage()


@router.get("/watchlists")
@limiter.limit("120/minute")
def watchlists(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return {"watchlists": repository.list_watchlists(user.username)}


@router.get("/history")
@limiter.limit("120/minute")
def history(
    request: Request,
    symbol: str = Query(min_length=1, max_length=25),
    market_type: Literal["BIST", "Kripto"] = "BIST",
    timeframe: Literal["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1wk", "1mo"] = "1m",
    limit: int = Query(1000, ge=1, le=1500),
    user: User = Depends(get_current_admin_user),
) -> dict:
    try:
        selected = AlarmSymbol(symbol=symbol, market_type=market_type)
    except ValueError:
        raise HTTPException(422, "Geçersiz sembol.") from None
    return get_advanced_alarm_engine().hub.history(
        selected.symbol, market_type=selected.market_type, timeframe=timeframe, limit=limit
    )


@router.post("/watchlists", status_code=201)
@limiter.limit("30/minute")
def create_watchlist(
    request: Request, payload: WatchlistWrite, user: User = Depends(get_current_admin_user)
) -> dict:
    return _call(repository.save_watchlist, user.username, payload.model_dump())


@router.put("/watchlists/{watchlist_id}")
@limiter.limit("30/minute")
def update_watchlist(
    request: Request,
    watchlist_id: str,
    payload: WatchlistWrite,
    user: User = Depends(get_current_admin_user),
) -> dict:
    if payload.revision is None:
        raise HTTPException(422, "Güncelleme için mevcut revision gerekli.")
    return _call(repository.save_watchlist, user.username, payload.model_dump(), watchlist_id)


@router.delete("/watchlists/{watchlist_id}")
@limiter.limit("30/minute")
def remove_watchlist(
    request: Request, watchlist_id: str, user: User = Depends(get_current_admin_user)
) -> dict:
    _call(repository.delete_watchlist, user.username, watchlist_id)
    return {"deleted": True}


def _save(owner, payload, rule_id=None):
    if payload.enabled and payload.notify_telegram and not telegram_configured():
        raise HTTPException(422, "Sunucuda Telegram yapılandırılmamış.")
    if rule_id and payload.revision is None:
        raise HTTPException(422, "Güncelleme için mevcut revision gerekli.")
    return _call(repository.save_rule, owner, payload.model_dump(), rule_id)


@router.post("", status_code=201)
@limiter.limit("30/minute")
def create_rule(
    request: Request, payload: AlarmWrite, user: User = Depends(get_current_admin_user)
) -> dict:
    return _save(user.username, payload)


@router.put("/{rule_id}")
@limiter.limit("30/minute")
def update_rule(
    request: Request,
    rule_id: str,
    payload: AlarmWrite,
    user: User = Depends(get_current_admin_user),
) -> dict:
    return _save(user.username, payload, rule_id)


@router.delete("/{rule_id}")
@limiter.limit("30/minute")
def remove_rule(
    request: Request, rule_id: str, user: User = Depends(get_current_admin_user)
) -> dict:
    _call(repository.delete_rule, user.username, rule_id)
    return {"deleted": True}
