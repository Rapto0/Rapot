"""
Otonom Analiz - FastAPI REST API
Sinyal, trade ve bot istatistiklerine erişim sağlar.

Kullanım:
    uvicorn api.main:app --reload --port 8000
"""

from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    UserLogin,
    authenticate_user,
    create_access_token,
    get_current_user,
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# FastAPI uygulaması
app = FastAPI(
    title="Otonom Analiz API",
    description="7/24 Finansal Sinyal ve Analiz REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate Limit Handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Frontend erişimi için
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod'da spesifik domainler kullanın
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Başlangıç zamanı
_start_time = datetime.now()


# ==================== SCHEMAS ====================


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı."""

    status: str
    uptime_seconds: float
    database: str
    version: str


class SignalResponse(BaseModel):
    """Sinyal yanıtı."""

    id: int
    symbol: str
    market_type: str
    strategy: str
    signal_type: str
    timeframe: str
    score: str | None = None
    price: float
    created_at: str | None = None

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    """Trade yanıtı."""

    id: int
    symbol: str
    market_type: str
    direction: str
    price: float
    quantity: float
    pnl: float
    status: str
    created_at: str | None = None

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """İstatistik yanıtı."""

    total_signals: int
    total_trades: int
    open_trades: int
    total_pnl: float
    win_rate: float
    scan_count: int


class ScanRequest(BaseModel):
    """Tarama isteği."""

    market_type: str = "BIST"  # BIST veya Kripto
    async_mode: bool = False


# ==================== ENDPOINTS ====================


# ==================== AUTH ENDPOINTS ====================


@app.post("/auth/token", response_model=Token, tags=["Authentication"])
@limiter.limit("5/minute")
async def login(request: Request, user_login: UserLogin):
    """
    Kullanıcı girişi - JWT token döndürür.

    Varsayılan kullanıcılar:
    - admin / admin123 (admin yetkili)
    - user / user123 (normal kullanıcı)
    """
    user = authenticate_user(user_login.username, user_login.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # saniye cinsinden
    )


@app.get("/auth/me", response_model=User, tags=["Authentication"])
async def get_me(current_user: User = Depends(get_current_user)):
    """Mevcut kullanıcı bilgilerini döndürür (token gerekli)."""
    return current_user


# ==================== PUBLIC ENDPOINTS ====================


@app.get("/", tags=["Root"])
@limiter.limit("60/minute")
async def root(request: Request):
    """API kök endpoint."""
    return {
        "name": "Otonom Analiz API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["System"])
@limiter.limit("60/minute")
async def health_check(request: Request):
    """
    Sistem sağlık kontrolü.

    Bot durumu, uptime ve veritabanı bağlantısını kontrol eder.
    """
    uptime = (datetime.now() - _start_time).total_seconds()

    # Veritabanı kontrolü
    try:
        from db_session import get_table_stats

        stats = get_table_stats()
        db_status = "connected"
    except Exception:
        db_status = "error"

    return HealthResponse(
        status="healthy",
        uptime_seconds=uptime,
        database=db_status,
        version="1.0.0",
    )


@app.get("/signals", response_model=list[SignalResponse], tags=["Signals"])
@limiter.limit("60/minute")
async def get_signals(
    request: Request,
    symbol: str | None = Query(None, description="Sembol filtresi"),
    strategy: str | None = Query(None, description="Strateji filtresi (COMBO/HUNTER)"),
    signal_type: str | None = Query(None, description="Sinyal türü (AL/SAT)"),
    limit: int = Query(50, ge=1, le=500, description="Maksimum kayıt sayısı"),
):
    """
    Sinyal listesini döndürür.

    Opsiyonel filtreler: symbol, strategy, signal_type
    """
    from db_session import get_session
    from models import Signal

    with get_session() as session:
        query = session.query(Signal)

        if symbol:
            query = query.filter(Signal.symbol == symbol.upper())
        if strategy:
            query = query.filter(Signal.strategy == strategy.upper())
        if signal_type:
            query = query.filter(Signal.signal_type == signal_type.upper())

        signals = query.order_by(Signal.created_at.desc()).limit(limit).all()

        return [
            SignalResponse(
                id=s.id,
                symbol=s.symbol,
                market_type=s.market_type,
                strategy=s.strategy,
                signal_type=s.signal_type,
                timeframe=s.timeframe,
                score=s.score,
                price=s.price,
                created_at=s.created_at.isoformat() if s.created_at else None,
            )
            for s in signals
        ]


@app.get("/signals/{signal_id}", response_model=SignalResponse, tags=["Signals"])
async def get_signal(signal_id: int):
    """Belirli bir sinyali döndürür."""
    from db_session import get_session
    from models import Signal

    with get_session() as session:
        signal = session.query(Signal).filter(Signal.id == signal_id).first()

        if not signal:
            raise HTTPException(status_code=404, detail="Sinyal bulunamadı")

        return SignalResponse(
            id=signal.id,
            symbol=signal.symbol,
            market_type=signal.market_type,
            strategy=signal.strategy,
            signal_type=signal.signal_type,
            timeframe=signal.timeframe,
            score=signal.score,
            price=signal.price,
            created_at=signal.created_at.isoformat() if signal.created_at else None,
        )


@app.get("/trades", response_model=list[TradeResponse], tags=["Trades"])
@limiter.limit("60/minute")
async def get_trades(
    request: Request,
    symbol: str | None = Query(None, description="Sembol filtresi"),
    status: str | None = Query(None, description="Durum filtresi (OPEN/CLOSED)"),
    limit: int = Query(50, ge=1, le=500, description="Maksimum kayıt sayısı"),
):
    """
    Trade listesini döndürür.

    Opsiyonel filtreler: symbol, status
    """
    from db_session import get_session
    from models import Trade

    with get_session() as session:
        query = session.query(Trade)

        if symbol:
            query = query.filter(Trade.symbol == symbol.upper())
        if status:
            query = query.filter(Trade.status == status.upper())

        trades = query.order_by(Trade.created_at.desc()).limit(limit).all()

        return [
            TradeResponse(
                id=t.id,
                symbol=t.symbol,
                market_type=t.market_type,
                direction=t.direction,
                price=t.price,
                quantity=t.quantity,
                pnl=t.pnl,
                status=t.status,
                created_at=t.created_at.isoformat() if t.created_at else None,
            )
            for t in trades
        ]


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
@limiter.limit("60/minute")
async def get_stats(request: Request):
    """
    Bot ve trade istatistiklerini döndürür.
    """
    from db_session import get_session
    from models import Signal, Trade

    with get_session() as session:
        # Sinyal sayısı
        total_signals = session.query(Signal).count()

        # Trade istatistikleri
        total_trades = session.query(Trade).count()
        open_trades = session.query(Trade).filter(Trade.status == "OPEN").count()

        # PnL hesaplama
        from sqlalchemy import func

        pnl_result = session.query(func.sum(Trade.pnl)).filter(Trade.status == "CLOSED").scalar()
        total_pnl = pnl_result or 0.0

        # Win rate
        closed_trades = session.query(Trade).filter(Trade.status == "CLOSED").count()
        winning_trades = (
            session.query(Trade).filter(Trade.status == "CLOSED", Trade.pnl > 0).count()
        )
        win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0

        # Tarama sayısı
        try:
            from market_scanner import get_scan_count

            scan_count = get_scan_count()
        except Exception:
            scan_count = 0

        return StatsResponse(
            total_signals=total_signals,
            total_trades=total_trades,
            open_trades=open_trades,
            total_pnl=total_pnl,
            win_rate=round(win_rate, 2),
            scan_count=scan_count,
        )


@app.post("/analyze/{symbol}", tags=["Analysis"])
@limiter.limit("2/minute")
async def analyze_symbol(
    request: Request,
    symbol: str,
    market_type: str = Query("BIST", description="Piyasa türü"),
):
    """
    Belirli bir sembol için manuel analiz başlatır.
    """
    try:
        from command_handler import analyze_manual

        analyze_manual(symbol.upper())
        return {"message": f"{symbol.upper()} analizi başlatıldı", "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/symbols/bist", tags=["Symbols"])
@limiter.limit("60/minute")
async def get_bist_symbols(request: Request):
    """BIST sembol listesini döndürür."""
    from data_loader import get_all_bist_symbols

    symbols = get_all_bist_symbols()
    return {"count": len(symbols), "symbols": symbols}


@app.get("/symbols/crypto", tags=["Symbols"])
@limiter.limit("60/minute")
async def get_crypto_symbols(request: Request):
    """Kripto sembol listesini döndürür."""
    from data_loader import get_all_binance_symbols

    symbols = get_all_binance_symbols()
    return {"count": len(symbols), "symbols": symbols}


# ==================== STARTUP/SHUTDOWN ====================


@app.on_event("startup")
async def startup_event():
    """API başlangıcında çalışır."""
    from db_session import init_db

    init_db()
    print("🚀 Otonom Analiz API başlatıldı")


@app.on_event("shutdown")
async def shutdown_event():
    """API kapanışında çalışır."""
    print("🛑 Otonom Analiz API kapatıldı")
