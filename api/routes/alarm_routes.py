"""Authenticated management of persistent, server-evaluated alarm rules."""

import math
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from api.auth import User, get_current_admin_user
from api.rate_limit import limiter
from application.services import server_alarm_service as service

router = APIRouter(prefix="/alarms", tags=["Server alarms"])


class AlarmSymbol(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=25)
    market_type: Literal["BIST", "Kripto"]

    @model_validator(mode="after")
    def validate_symbol(self) -> "AlarmSymbol":
        self.symbol = self.symbol.strip().upper()
        if self.market_type == "BIST" and self.symbol.endswith(".IS"):
            self.symbol = self.symbol[:-3]
        pattern = r"[A-Z0-9]{1,20}" if self.market_type == "BIST" else r"[A-Z0-9]{2,20}USDT"
        if not re.fullmatch(pattern, self.symbol):
            raise ValueError("Geçersiz sembol; yalnız harf ve rakam kullanın.")
        return self


class AlarmWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)
    symbols: list[AlarmSymbol] = Field(min_length=1, max_length=20)
    indicator: Literal["rsi", "wr", "combo", "hunter"]
    timeframe: Literal["1h", "4h", "1d"]
    side: Literal["dip", "top"]
    threshold: float
    mode: Literal["on_enter", "once_per_bar"] = "on_enter"
    enabled: bool = True
    notify_telegram: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Alarm adı boş olamaz veya kontrol karakteri içeremez.")
        return value

    @model_validator(mode="after")
    def validate_rule(self) -> "AlarmWrite":
        ranges = {"rsi": (0, 100), "wr": (-100, 0), "combo": (1, 4), "hunter": (1, 15)}
        minimum, maximum = ranges[self.indicator]
        if not math.isfinite(self.threshold) or not minimum <= self.threshold <= maximum:
            raise ValueError(f"{self.indicator} eşiği {minimum} ile {maximum} arasında olmalı.")
        if self.indicator in {"combo", "hunter"} and not self.threshold.is_integer():
            raise ValueError("Puan eşiği tam sayı olmalı.")
        keys = {(item.symbol, item.market_type) for item in self.symbols}
        if len(keys) != len(self.symbols):
            raise ValueError("Aynı sembol bir kurala bir kez eklenebilir.")
        if self.timeframe != "1d" and any(item.market_type == "BIST" for item in self.symbols):
            raise ValueError("BIST sunucu alarmlarında yalnız 1d periyodu destekleniyor.")
        return self


def _save(owner: str, payload: AlarmWrite, rule_id: str | None = None) -> dict:
    if payload.enabled and payload.notify_telegram and not service.telegram_configured():
        raise HTTPException(422, "Sunucuda Telegram yapılandırılmamış.")
    try:
        return service.save_rule(owner, payload.model_dump(), rule_id=rule_id)
    except service.AlarmNotFoundError as exc:
        raise HTTPException(404, "Alarm bulunamadı.") from exc
    except service.AlarmLimitError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("")
@limiter.limit("60/minute")
def list_alarms(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return {
        "rules": service.list_rules(user.username),
        "runtime": service.runtime_status(),
        "limits": service.LIMITS,
    }


@router.get("/events")
@limiter.limit("60/minute")
def list_alarm_events(
    request: Request,
    limit: int = Query(100, ge=1, le=200),
    user: User = Depends(get_current_admin_user),
) -> dict:
    return {"events": service.list_events(user.username, limit)}


@router.post("", status_code=201)
@limiter.limit("30/minute")
def create_alarm(
    request: Request, payload: AlarmWrite, user: User = Depends(get_current_admin_user)
) -> dict:
    return _save(user.username, payload)


@router.put("/{rule_id}")
@limiter.limit("30/minute")
def update_alarm(
    request: Request,
    rule_id: str,
    payload: AlarmWrite,
    user: User = Depends(get_current_admin_user),
) -> dict:
    return _save(user.username, payload, rule_id)


@router.delete("/{rule_id}")
@limiter.limit("30/minute")
def delete_alarm(
    request: Request, rule_id: str, user: User = Depends(get_current_admin_user)
) -> dict:
    try:
        service.delete_rule(user.username, rule_id)
    except service.AlarmNotFoundError as exc:
        raise HTTPException(404, "Alarm bulunamadı.") from exc
    return {"deleted": True}
