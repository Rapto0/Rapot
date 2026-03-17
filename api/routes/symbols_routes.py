from fastapi import APIRouter, Request

from api.rate_limit import limiter

router = APIRouter(tags=["Symbols"])


@router.get("/symbols/bist")
@limiter.limit("60/minute")
async def get_bist_symbols(request: Request):
    from data_loader import get_all_bist_symbols

    symbols = get_all_bist_symbols()
    return {"count": len(symbols), "symbols": symbols}


@router.get("/symbols/crypto")
@limiter.limit("60/minute")
async def get_crypto_symbols(request: Request):
    from data_loader import get_all_binance_symbols

    symbols = get_all_binance_symbols()
    return {"count": len(symbols), "symbols": symbols}
