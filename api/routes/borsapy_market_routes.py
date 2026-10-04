"""The site's private Borsapy market surface; no legacy price-cache fallback."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.auth import User, get_current_admin_user
from api.rate_limit import limiter
from api.routes.borsapy_connection_routes import PrivateRoute
from application.services.borsapy_gateway import BorsapyGatewayError, get_borsapy_gateway
from application.services.borsapy_market_data import get_borsapy_market_data

router = APIRouter(prefix="/borsapy/market", tags=["Private market data"], route_class=PrivateRoute)


def _call(method, *args):
    try:
        return method(*args)
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None


@router.get("/indices")
@limiter.limit("60/minute")
def quotes(
    request: Request,
    symbol: list[str] = Query(min_length=1, max_length=50),
    user: User = Depends(get_current_admin_user),
) -> list[dict]:
    return _call(get_borsapy_market_data().quotes, symbol)


@router.get("/metrics")
@limiter.limit("60/minute")
def metrics(
    request: Request,
    key: list[str] = Query(min_length=1, max_length=50),
    user: User = Depends(get_current_admin_user),
) -> dict:
    return _call(get_borsapy_market_data().metrics, key)


@router.get("/ticker")
@limiter.limit("30/minute")
def ticker(request: Request, user: User = Depends(get_current_admin_user)) -> list[dict]:
    items = _call(
        get_borsapy_market_data().quotes, ["XU100.IS", "THYAO.IS", "GARAN.IS", "AKBNK.IS"]
    )
    return [
        {
            **item,
            "symbol": item["symbol"].removesuffix(".IS"),
            "name": item["shortName"],
            "price": item["regularMarketPrice"],
            "changePercent": item["regularMarketChangePercent"],
        }
        for item in items
    ]


@router.get("/crypto-metrics")
@limiter.limit("60/minute")
def crypto_metrics(
    request: Request,
    key: list[str] = Query(min_length=1, max_length=50),
    user: User = Depends(get_current_admin_user),
) -> dict:
    return _call(get_borsapy_market_data().crypto_metrics, key)


@router.get("/overview")
@limiter.limit("30/minute")
def overview(request: Request, user: User = Depends(get_current_admin_user)) -> dict:
    return _call(get_borsapy_market_data().overview)


@router.get("/status")
def status(user: User = Depends(get_current_admin_user)) -> dict:
    from data_loader import bist_source_policy, bist_symbols_status
    from settings import get_settings

    return {
        "connection": get_borsapy_gateway().status(),
        "primary": "borsapy_tradingview",
        "bist_jobs_enabled": get_settings().borsapy_use_for_bist,
        "quote_limit": 200,
        "batch_limit": 50,
        "realtime_verified": False,
        "bist_alarm_intervals": ["1d"],
        "crypto_source": "binance",
        "secondary_confirmation": "independent_yahoo_when_required",
        "bist_policy": bist_source_policy(),
        "symbols": bist_symbols_status(),
    }
