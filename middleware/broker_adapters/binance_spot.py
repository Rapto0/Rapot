from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

import requests

from middleware.broker_adapters.base import BrokerAssetBalance, BrokerClient, BrokerOrderResult
from middleware.domain.enums import ExecutionMode, OrderStatus
from middleware.domain.events import BrokerOrderRequestPayload
from middleware.domain.idempotency import build_client_order_id
from middleware.infra.settings import MiddlewareSettings
from middleware.risk.binance_filters import BinanceSymbolRules


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


class BinanceAPIError(RuntimeError):
    def __init__(self, *, status_code: int, code: Any, message: str) -> None:
        super().__init__(f"Binance API error {status_code} ({code}): {message}")
        self.status_code = status_code
        self.code = code
        self.api_message = message

    @property
    def may_represent_an_existing_order(self) -> bool:
        return self.status_code >= 500 or "duplicate order" in self.api_message.lower()


class BinanceResponseError(RuntimeError):
    """A response that cannot prove whether an order was accepted."""


@dataclass(slots=True)
class BinanceSpotBrokerClient(BrokerClient):
    cfg: MiddlewareSettings
    session: requests.Session = field(default_factory=requests.Session)
    name: str = "BINANCE_SPOT"
    _rules_cache: dict[str, BinanceSymbolRules] = field(default_factory=dict)

    def get_symbol_rules(self, symbol: str) -> BinanceSymbolRules:
        normalized = symbol.upper()
        cached = self._rules_cache.get(normalized)
        if cached is not None:
            return cached

        response = self.session.get(
            self._url("/api/v3/exchangeInfo"),
            params={"symbol": normalized},
            timeout=self.cfg.binance_request_timeout_seconds,
        )
        payload = self._json_response(response)
        symbols = payload.get("symbols") or []
        if not symbols:
            raise RuntimeError(f"Binance symbol not found: {normalized}")

        rules = BinanceSymbolRules.from_exchange_info_symbol(symbols[0])
        self._rules_cache[normalized] = rules
        return rules

    def get_asset_balance(self, asset: str) -> Decimal:
        return self.get_asset_balances(asset).free

    def get_asset_balances(self, asset: str) -> BrokerAssetBalance:
        payload = self._signed_request("GET", "/api/v3/account", {})
        normalized = asset.upper()
        for item in payload.get("balances", []):
            if str(item.get("asset", "")).upper() == normalized:
                return BrokerAssetBalance(
                    asset=normalized,
                    free=_decimal(item.get("free")),
                    locked=_decimal(item.get("locked")),
                )
        return BrokerAssetBalance(asset=normalized, free=Decimal("0"), locked=Decimal("0"))

    def submit_limit_order(self, payload: BrokerOrderRequestPayload) -> BrokerOrderResult:
        quantity = payload.quantity if payload.quantity is not None else Decimal(payload.lots)
        if self.cfg.execution_mode == ExecutionMode.DRY_RUN:
            return self._dry_run_result(payload=payload, quantity=quantity)

        if not self.cfg.binance_live_enabled:
            return BrokerOrderResult(
                accepted=False,
                status=OrderStatus.FAILED,
                message=(
                    "Binance live adapter disabled by config. "
                    "Set MW_BINANCE_LIVE_ENABLED=true only after testnet/UAT sign-off."
                ),
                raw_payload=self._request_preview(payload=payload, quantity=quantity),
            )

        try:
            response_payload = self._signed_request(
                "POST",
                "/api/v3/order",
                {
                    "symbol": payload.symbol.upper(),
                    "side": payload.side.value,
                    "type": "LIMIT",
                    "timeInForce": payload.tif,
                    "quantity": _format_decimal(quantity),
                    "price": _format_decimal(payload.limit_price),
                    "newClientOrderId": payload.client_order_id,
                    "newOrderRespType": "FULL",
                },
            )
        except (requests.RequestException, BinanceResponseError):
            return self.get_order_by_client_id(payload.symbol, payload.client_order_id)
        except BinanceAPIError as exc:
            if exc.may_represent_an_existing_order:
                return self.get_order_by_client_id(payload.symbol, payload.client_order_id)
            return BrokerOrderResult(
                accepted=False,
                status=OrderStatus.FAILED,
                message=str(exc),
                raw_payload=self._request_preview(payload=payload, quantity=quantity),
            )

        return self._map_order_response(response_payload, client_order_id=payload.client_order_id)

    def get_order_by_client_id(self, symbol: str, client_order_id: str) -> BrokerOrderResult:
        try:
            response_payload = self._signed_request(
                "GET",
                "/api/v3/order",
                {
                    "symbol": symbol.upper(),
                    "origClientOrderId": client_order_id,
                },
            )
        except (requests.RequestException, RuntimeError):
            return BrokerOrderResult(
                accepted=False,
                status=OrderStatus.UNKNOWN,
                client_order_id=client_order_id,
                message="Binance order result is uncertain; recovery lookup did not complete",
                raw_payload={"symbol": symbol.upper(), "client_order_id": client_order_id},
                execution_uncertain=True,
            )
        return self._map_order_response(response_payload, client_order_id=client_order_id)

    def _dry_run_result(
        self, *, payload: BrokerOrderRequestPayload, quantity: Decimal
    ) -> BrokerOrderResult:
        broker_order_id = f"BINANCE-DRY-{uuid4().hex[:12].upper()}"
        raw = self._request_preview(payload=payload, quantity=quantity)
        raw["broker_order_id"] = broker_order_id
        raw["mode"] = ExecutionMode.DRY_RUN.value

        if self.cfg.binance_dry_run_auto_fill:
            return BrokerOrderResult(
                accepted=True,
                status=OrderStatus.FILLED,
                broker_order_id=broker_order_id,
                client_order_id=payload.client_order_id,
                filled_lots=0,
                filled_quantity=quantity,
                avg_fill_price=payload.limit_price,
                message="Binance dry-run order filled instantly",
                raw_payload=raw,
            )

        return BrokerOrderResult(
            accepted=True,
            status=OrderStatus.ACKNOWLEDGED,
            broker_order_id=broker_order_id,
            client_order_id=payload.client_order_id,
            filled_lots=0,
            filled_quantity=Decimal("0"),
            avg_fill_price=None,
            message="Binance dry-run order acknowledged",
            raw_payload=raw,
        )

    def _request_preview(
        self, *, payload: BrokerOrderRequestPayload, quantity: Decimal
    ) -> dict[str, Any]:
        return {
            "broker": self.name,
            "symbol": payload.symbol.upper(),
            "side": payload.side.value,
            "type": "LIMIT",
            "timeInForce": payload.tif,
            "quantity": _format_decimal(quantity),
            "price": _format_decimal(payload.limit_price),
            "idempotency_key": payload.idempotency_key,
            "client_order_id": payload.client_order_id,
        }

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.cfg.binance_api_key or not self.cfg.binance_secret_key:
            raise RuntimeError("Binance API key/secret are required for signed requests")

        signed_params = dict(params)
        signed_params["recvWindow"] = self.cfg.binance_recv_window_ms
        signed_params["timestamp"] = int(time.time() * 1000)
        query = urlencode(
            [(key, self._format_param(value)) for key, value in signed_params.items()]
        )
        signature = hmac.new(
            self.cfg.binance_secret_key.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{self._url(path)}?{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.cfg.binance_api_key}

        if method.upper() == "GET":
            response = self.session.get(
                url, headers=headers, timeout=self.cfg.binance_request_timeout_seconds
            )
        elif method.upper() == "POST":
            response = self.session.post(
                url, headers=headers, timeout=self.cfg.binance_request_timeout_seconds
            )
        else:
            raise ValueError(f"unsupported Binance method: {method}")

        return self._json_response(response)

    def _map_order_response(
        self, payload: dict[str, Any], *, client_order_id: str | None = None
    ) -> BrokerOrderResult:
        status_raw = str(payload.get("status", "")).upper()
        status = {
            "NEW": OrderStatus.ACKNOWLEDGED,
            "PENDING_CANCEL": OrderStatus.ACKNOWLEDGED,
            "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "FILLED": OrderStatus.FILLED,
            "CANCELED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.FAILED,
            "EXPIRED": OrderStatus.EXPIRED,
            "EXPIRED_IN_MATCH": OrderStatus.EXPIRED,
        }.get(status_raw, OrderStatus.UNKNOWN)
        accepted = status not in {
            OrderStatus.FAILED,
            OrderStatus.CANCELLED,
            OrderStatus.EXPIRED,
            OrderStatus.UNKNOWN,
        }
        filled_quantity = _decimal(payload.get("executedQty"))
        avg_fill_price = self._avg_fill_price(payload, filled_quantity)

        return BrokerOrderResult(
            accepted=accepted,
            status=status,
            broker_order_id=str(payload.get("orderId")) if payload.get("orderId") else None,
            client_order_id=client_order_id
            or str(payload.get("clientOrderId") or payload.get("origClientOrderId") or "")
            or None,
            filled_lots=0,
            filled_quantity=filled_quantity,
            avg_fill_price=avg_fill_price,
            message=f"Binance order status: {status_raw or status.value}",
            raw_payload=payload,
            execution_uncertain=status == OrderStatus.UNKNOWN,
        )

    def _avg_fill_price(self, payload: dict[str, Any], filled_quantity: Decimal) -> Decimal | None:
        fills = payload.get("fills") or []
        fill_quantity = Decimal("0")
        fill_notional = Decimal("0")
        for item in fills:
            quantity = _decimal(item.get("qty"))
            price = _decimal(item.get("price"))
            fill_quantity += quantity
            fill_notional += quantity * price
        if fill_quantity > 0:
            return fill_notional / fill_quantity

        cumulative_quote = _decimal(payload.get("cummulativeQuoteQty"))
        if filled_quantity > 0 and cumulative_quote > 0:
            return cumulative_quote / filled_quantity
        return None

    def _json_response(self, response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError as exc:
            raise BinanceResponseError("Binance returned a non-JSON response") from exc
        if not isinstance(payload, dict):
            raise BinanceResponseError("Binance returned an unexpected JSON payload")
        if response.status_code >= 400:
            code = payload.get("code")
            msg = payload.get("msg") or response.text
            raise BinanceAPIError(
                status_code=response.status_code,
                code=code,
                message=str(msg),
            )
        return payload

    def _url(self, path: str) -> str:
        return f"{self.cfg.binance_base_url.rstrip('/')}{path}"

    def _client_order_id(self, idempotency_key: str) -> str:
        return build_client_order_id(idempotency_key)

    def _format_param(self, value: Any) -> str:
        if isinstance(value, Decimal):
            return _format_decimal(value)
        return str(value)
