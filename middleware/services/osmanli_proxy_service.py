from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any

from middleware.domain.constants import SUPPORTED_SIGNAL_CODES
from middleware.domain.enums import Side
from middleware.domain.events import (
    OsmanliProxyResponse,
    ProcessSignalResponse,
    TradingViewWebhookPayload,
)
from middleware.infra.settings import MiddlewareSettings
from middleware.infra.time import UTC
from middleware.services.trading_service import TradingService

_SIGNAL_CODE_RE = re.compile(r"\b[HC]_(?:BLS|UCZ|PAH)\b", re.IGNORECASE)

_SYMBOL_KEYS = {
    "symbol",
    "ticker",
    "sembol",
    "hisse",
    "hissekodu",
    "hissesembolkodu",
}
_SIDE_KEYS = {
    "side",
    "direction",
    "yon",
    "islemyonu",
    "emiryonu",
}
_PRICE_KEYS = {
    "price",
    "close",
    "limitprice",
    "limitfiyat",
    "limitfiyati",
    "fiyat",
}
_BAR_TIME_KEYS = {"bartime", "bar_time", "time"}
_BAR_INDEX_KEYS = {"barindex", "bar_index"}
_TIMEFRAME_KEYS = {"timeframe", "interval", "periyot"}
_REALTIME_KEYS = {"isrealtime", "realtime"}
_SIGNAL_CODE_KEYS = {"signalcode", "sinyalkodu"}
_SIGNAL_TEXT_KEYS = {"signaltext", "sinyalmetni", "komutadi", "commandname"}


class OsmanliProxyPayloadError(ValueError):
    pass


class OsmanliProxyService:
    def __init__(
        self,
        *,
        cfg: MiddlewareSettings,
        trading_service: TradingService,
    ) -> None:
        self.cfg = cfg
        self.trading_service = trading_service

    def process_shadow(self, raw_payload: dict[str, Any]) -> OsmanliProxyResponse:
        extracted_signal = self.extract_signal(raw_payload)
        process_result = self.trading_service.process_webhook(extracted_signal)
        return OsmanliProxyResponse(
            forward_enabled=self.cfg.osmanli_forward_enabled,
            forwarded=False,
            message=self._build_shadow_message(process_result),
            extracted_signal=extracted_signal,
            process_result=process_result,
        )

    def extract_signal(self, raw_payload: dict[str, Any]) -> TradingViewWebhookPayload:
        if not isinstance(raw_payload, dict) or not raw_payload:
            raise OsmanliProxyPayloadError("Osmanli proxy payload must be a JSON object")

        symbol = _clean_symbol(_require_text(raw_payload, _SYMBOL_KEYS, "symbol"))
        side = _parse_side(_require_text(raw_payload, _SIDE_KEYS, "side"))
        signal_code = _extract_signal_code(raw_payload)
        signal_text = _find_text(raw_payload, _SIGNAL_TEXT_KEYS) or signal_code
        price = _parse_decimal(_require_value(raw_payload, _PRICE_KEYS, "price"), "price")
        timeframe = (_find_text(raw_payload, _TIMEFRAME_KEYS) or "1D").upper()
        bar_time = _parse_bar_time(_find_value(raw_payload, _BAR_TIME_KEYS))
        bar_index = _parse_bar_index(_find_value(raw_payload, _BAR_INDEX_KEYS), raw_payload)
        is_realtime = _parse_bool(_find_value(raw_payload, _REALTIME_KEYS), default=True)

        return TradingViewWebhookPayload(
            schemaVersion=1,
            source="Combo+Hunter",
            symbol=symbol,
            ticker=symbol,
            signalCode=signal_code,
            signalText=signal_text,
            side=side,
            price=price,
            timeframe=timeframe,
            barTime=bar_time,
            barIndex=bar_index,
            isRealtime=is_realtime,
        )

    def _build_shadow_message(self, process_result: ProcessSignalResponse) -> str:
        if self.cfg.osmanli_forward_enabled:
            return "Osmanli proxy forward is configured but not implemented in shadow step"
        if process_result.duplicate:
            return "shadow processed: duplicate signal ignored"
        if process_result.risk_reason:
            return "shadow processed: signal rejected by risk checks"
        return "shadow processed: signal passed middleware checks; Osmanli forward disabled"


def _normalize_key(value: str) -> str:
    normalized = (
        value.replace("\u0130", "i")
        .replace("I", "i")
        .replace("\u0131", "i")
        .replace("\u015e", "s")
        .replace("\u015f", "s")
        .replace("\u011e", "g")
        .replace("\u011f", "g")
        .replace("\u00dc", "u")
        .replace("\u00fc", "u")
        .replace("\u00d6", "o")
        .replace("\u00f6", "o")
        .replace("\u00c7", "c")
        .replace("\u00e7", "c")
    )
    return "".join(ch for ch in normalized.lower() if ch.isalnum())


def _walk_json(value: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield _normalize_key(str(key)), item
            yield from _walk_json(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_json(item)


def _find_value(raw_payload: dict[str, Any], keys: set[str]) -> Any | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for key, value in _walk_json(raw_payload):
        if key in normalized_keys:
            return value
    return None


def _find_text(raw_payload: dict[str, Any], keys: set[str]) -> str | None:
    value = _find_value(raw_payload, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _require_value(raw_payload: dict[str, Any], keys: set[str], field_name: str) -> Any:
    value = _find_value(raw_payload, keys)
    if value is None or str(value).strip() == "":
        raise OsmanliProxyPayloadError(f"missing required Osmanli proxy field: {field_name}")
    return value


def _require_text(raw_payload: dict[str, Any], keys: set[str], field_name: str) -> str:
    return str(_require_value(raw_payload, keys, field_name)).strip()


def _clean_symbol(value: str) -> str:
    symbol = value.strip().upper()
    if ":" in symbol:
        symbol = symbol.split(":", 1)[1]
    return symbol


def _parse_side(value: str) -> Side:
    normalized = _normalize_key(value)
    if normalized in {"buy", "al", "alis"}:
        return Side.BUY
    if normalized in {"sell", "sat", "satis"}:
        return Side.SELL
    raise OsmanliProxyPayloadError(f"unsupported side value: {value}")


def _extract_signal_code(raw_payload: dict[str, Any]) -> str:
    direct = _find_text(raw_payload, _SIGNAL_CODE_KEYS)
    candidates = [direct] if direct else []
    signal_text_keys = {_normalize_key(item) for item in _SIGNAL_TEXT_KEYS}
    candidates.extend(
        str(value) for key, value in _walk_json(raw_payload) if key in signal_text_keys
    )
    for candidate in candidates:
        match = _SIGNAL_CODE_RE.search(candidate or "")
        if not match:
            continue
        code = match.group(0).upper()
        if code in SUPPORTED_SIGNAL_CODES:
            return code
    raise OsmanliProxyPayloadError("missing supported signalCode in Osmanli proxy payload")


def _parse_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, str):
        value = value.strip().replace(",", ".")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise OsmanliProxyPayloadError(f"invalid decimal field: {field_name}") from exc
    if parsed <= 0:
        raise OsmanliProxyPayloadError(f"{field_name} must be > 0")
    return parsed


def _parse_bar_time(value: Any | None) -> int:
    if value is None or str(value).strip() == "":
        return int(datetime.now(UTC).timestamp() * 1000)
    text = str(value).strip()
    if text.isdigit():
        parsed = int(text)
        return parsed * 1000 if parsed < 10_000_000_000 else parsed
    try:
        parsed_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OsmanliProxyPayloadError("invalid barTime/time field") from exc
    return int(parsed_dt.timestamp() * 1000)


def _parse_bar_index(value: Any | None, raw_payload: dict[str, Any]) -> int:
    if value is not None and str(value).strip() != "":
        try:
            return max(0, int(str(value).strip()))
        except ValueError as exc:
            raise OsmanliProxyPayloadError("invalid barIndex field") from exc
    fingerprint = sha256(str(raw_payload).encode("utf-8")).hexdigest()
    return int(fingerprint[:8], 16)


def _parse_bool(value: Any | None, *, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = _normalize_key(str(value))
    if normalized in {"true", "1", "yes", "evet"}:
        return True
    if normalized in {"false", "0", "no", "hayir"}:
        return False
    raise OsmanliProxyPayloadError("invalid isRealtime field")
