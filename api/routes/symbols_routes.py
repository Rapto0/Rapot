import asyncio

from fastapi import APIRouter, HTTPException, Request

from api.rate_limit import limiter

router = APIRouter(tags=["Symbols"])


@router.get("/symbols/bist")
@limiter.limit("60/minute")
async def get_bist_symbols(request: Request):
    from application.services.borsapy_gateway import BorsapyGatewayError
    from data_loader import bist_symbols_status, get_all_bist_symbols

    try:
        symbols = await asyncio.to_thread(get_all_bist_symbols)
        return {"count": len(symbols), "symbols": symbols, "meta": bist_symbols_status()}
    except BorsapyGatewayError as exc:
        raise HTTPException(exc.status_code, str(exc)) from None


@router.get("/symbols/crypto")
@limiter.limit("60/minute")
async def get_crypto_symbols(request: Request):
    from data_loader import get_all_binance_symbols

    symbols = get_all_binance_symbols()
    return {"count": len(symbols), "symbols": symbols}
