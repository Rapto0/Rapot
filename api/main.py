"""
Otonom Analiz - FastAPI REST API
Sinyal, trade ve bot istatistiklerine erişim sağlar.

Kullanım:
    uvicorn api.main:app --reload --port 8000
"""

from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

import yfinance as yf  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.util import get_remote_address  # noqa: E402

from api.auth import (  # noqa: E402
    ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    User,
    UserLogin,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from api.calendar_service import calendar_service  # noqa: E402

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Başlangıç zamanı
_start_time = datetime.now()

import threading  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü.
    Botun scheduler döngüsünü arka plan thread'inde başlatır.
    """

    # Bot Thread Başlat
    def run_scheduler():
        try:
            print("🤖 Bot Scheduler Thread Başlatılıyor...")
            from scheduler import start_bot

            # Async modda çalıştır (kendi event loop'unu yönetir)
            # main.py varsayılanı False olabilir ama burada True deniyoruz
            start_bot(use_async=True)
        except Exception as e:
            print(f"❌ Bot Thread Hatası: {e}")

    # Daemon thread: Ana process kapanınca bu da kapanır
    bot_thread = threading.Thread(target=run_scheduler, daemon=True)
    bot_thread.start()

    yield

    print("🛑 API Kapatılıyor...")


# FastAPI uygulaması
app = FastAPI(
    title="Otonom Analiz API",
    description="7/24 Finansal Sinyal ve Analiz REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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


class AIAnalysisResponse(BaseModel):
    """AI Analiz yanıtı."""

    id: int
    signal_id: int | None = None
    symbol: str
    market_type: str
    scenario_name: str | None = None
    signal_type: str | None = None
    analysis_text: str
    technical_data: str | None = None
    created_at: str | None = None

    class Config:
        from_attributes = True


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

        _ = get_table_stats()
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
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/symbols/bist", tags=["Symbols"])
@limiter.limit("60/minute")
async def get_bist_symbols(request: Request):
    """BIST sembol listesini döndürür."""
    from data_loader import get_all_bist_symbols

    symbols = get_all_bist_symbols()
    return {"count": len(symbols), "symbols": symbols}


# ==================== AI ANALYSIS ENDPOINTS ====================


@app.get("/analyses", response_model=list[AIAnalysisResponse], tags=["AI Analysis"])
@limiter.limit("30/minute")
async def get_analyses(
    request: Request,
    symbol: str | None = Query(None, description="Sembol filtresi"),
    market_type: str | None = Query(None, description="Piyasa türü (BIST/Kripto)"),
    limit: int = Query(50, ge=1, le=200, description="Maksimum kayıt sayısı"),
):
    """
    AI Analiz listesini döndürür.

    Gemini AI tarafından üretilen tüm analizleri listeler.
    """
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        query = session.query(AIAnalysis)

        if symbol:
            query = query.filter(AIAnalysis.symbol == symbol.upper())
        if market_type:
            query = query.filter(AIAnalysis.market_type == market_type)

        analyses = query.order_by(AIAnalysis.created_at.desc()).limit(limit).all()

        return [
            AIAnalysisResponse(
                id=a.id,
                signal_id=a.signal_id,
                symbol=a.symbol,
                market_type=a.market_type,
                scenario_name=a.scenario_name,
                signal_type=a.signal_type,
                analysis_text=a.analysis_text,
                technical_data=a.technical_data,
                created_at=a.created_at.isoformat() if a.created_at else None,
            )
            for a in analyses
        ]


@app.get("/analyses/{analysis_id}", response_model=AIAnalysisResponse, tags=["AI Analysis"])
async def get_analysis(analysis_id: int):
    """Belirli bir AI analizini döndürür."""
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        analysis = session.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analiz bulunamadı")

        return AIAnalysisResponse(
            id=analysis.id,
            signal_id=analysis.signal_id,
            symbol=analysis.symbol,
            market_type=analysis.market_type,
            scenario_name=analysis.scenario_name,
            signal_type=analysis.signal_type,
            analysis_text=analysis.analysis_text,
            technical_data=analysis.technical_data,
            created_at=analysis.created_at.isoformat() if analysis.created_at else None,
        )


@app.get(
    "/signals/{signal_id}/analysis", response_model=AIAnalysisResponse | None, tags=["AI Analysis"]
)
async def get_signal_analysis(signal_id: int):
    """Belirli bir sinyale ait AI analizini döndürür."""
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        analysis = session.query(AIAnalysis).filter(AIAnalysis.signal_id == signal_id).first()

        if not analysis:
            return None

        return AIAnalysisResponse(
            id=analysis.id,
            signal_id=analysis.signal_id,
            symbol=analysis.symbol,
            market_type=analysis.market_type,
            scenario_name=analysis.scenario_name,
            signal_type=analysis.signal_type,
            analysis_text=analysis.analysis_text,
            technical_data=analysis.technical_data,
            created_at=analysis.created_at.isoformat() if analysis.created_at else None,
        )


@app.get("/market/overview", tags=["Market Data"])
@limiter.limit("5/minute")
async def get_market_overview(request: Request):
    """
    Piyasa genel bakış verilerini döndürür (BIST 100 ve Bitcoin).
    Son 24 saatlik mini grafik verisi içerir.
    """
    try:
        symbols = {"bist": "XU100.IS", "crypto": "BTC-USD"}
        data = {}

        for key, symbol in symbols.items():
            ticker = yf.Ticker(symbol)
            # Mini grafik için son 1 günlük veriyi 15 veya 5er dakikalık alalım
            df = ticker.history(period="24h", interval="15m")

            if df.empty:
                # Fallback if 24h is empty (e.g. weekend for BIST)
                df = ticker.history(period="5d", interval="60m")

            history = []
            if not df.empty:
                current_value = float(df["Close"].iloc[-1])
                first_value = float(df["Open"].iloc[0])
                change_percent = ((current_value - first_value) / first_value) * 100

                # Resample or just take last N points to keep payload small
                # Taking last 24 points (approx 6 hours if 15m, or 24h if 1h)
                # Let's just take all points but formatted
                for index, row in df.iterrows():
                    history.append({"time": index.strftime("%H:%M"), "value": float(row["Close"])})

                data[key] = {
                    "currentValue": current_value,
                    "change": change_percent,
                    "history": history,
                }
            else:
                data[key] = {"currentValue": 0, "change": 0, "history": []}

        return data

    except Exception as e:
        print(f"Market overview error: {e}")
        # Return empty data instead of crash to keep dashboard alive
        return {
            "bist": {"currentValue": 0, "change": 0, "history": []},
            "crypto": {"currentValue": 0, "change": 0, "history": []},
        }


@app.get("/scans", tags=["System"])
@limiter.limit("10/minute")
async def get_scan_history(request: Request, limit: int = 10):
    """Son tarama geçmişini döndürür."""
    from db_session import get_session
    from models import ScanHistory

    with get_session() as session:
        scans = (
            session.query(ScanHistory).order_by(ScanHistory.created_at.desc()).limit(limit).all()
        )
        return [scan.to_dict() for scan in scans]


@app.get("/logs", tags=["System"])
@limiter.limit("10/minute")
async def get_system_logs(request: Request, limit: int = 50):
    """Sistem loglarını döndürür (son N satır)."""
    try:
        import os

        log_path = "logs/trading_bot.log"
        if not os.path.exists(log_path):
            return []

        # Read last N lines
        # This is a simple implementation, for very large logs use improved methods
        with open(log_path, encoding="utf-8") as f:
            lines = f.readlines()
            last_lines = lines[-limit:]

        logs = []
        for line in last_lines:
            # Simple parsing, assuming format: YYYY-MM-DD HH:MM:SS | LEVEL | ...
            parts = line.split(" | ")
            if len(parts) >= 3:
                logs.append(
                    {
                        "timestamp": parts[0],
                        "level": parts[1].strip(),
                        "message": " | ".join(parts[2:]).strip(),
                    }
                )
            else:
                logs.append({"timestamp": "", "level": "INFO", "message": line.strip()})

        return list(reversed(logs))  # Show newest first

    except Exception as e:
        print(f"Log error: {e}")
        return []


@app.get("/market/ticker", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_market_ticker(request: Request):
    """
    Header ticker için popüler sembol verilerini döndürür.
    """
    try:
        symbols = [
            {"symbol": "XU100.IS", "name": "BIST 100"},
            {"symbol": "THYAO.IS", "name": "THY"},
            {"symbol": "GARAN.IS", "name": "Garanti"},
            {"symbol": "AKBNK.IS", "name": "Akbank"},
            {"symbol": "BTC-USD", "name": "Bitcoin"},
            {"symbol": "ETH-USD", "name": "Ethereum"},
        ]

        tickers = []
        for item in symbols:
            s_symbol = item["symbol"]
            ticker = yf.Ticker(s_symbol)
            # Get latest data (1 day)
            hist = ticker.history(period="2d")

            if not hist.empty and len(hist) >= 1:
                current_price = float(hist["Close"].iloc[-1])
                # Calculate change from previous close if available, else open
                prev_close = (
                    float(hist["Close"].iloc[-2]) if len(hist) > 1 else float(hist["Open"].iloc[0])
                )

                change = current_price - prev_close
                change_percent = (change / prev_close) * 100

                tickers.append(
                    {
                        "symbol": item["name"],  # Display name
                        "name": s_symbol.replace(".IS", "").replace("-USD", ""),  # Subtitle
                        "price": current_price,
                        "change": change,
                        "changePercent": change_percent,
                    }
                )

        return tickers

    except Exception as e:
        print(f"Ticker error: {e}")
        return []


@app.get("/api/market/analysis")
def get_market_analysis(
    market_type: str = Query(..., description="Market tipi: crypto veya bist"),
    symbol: str = Query(..., description="Sembol"),
):
    """
    Belirli bir sembol için detaylı teknik analiz ve AI yorumu getirir (CANLI).
    """
    try:
        import json
        from datetime import datetime

        from ai_analyst import analyze_with_gemini

        # 1. Temel teknik verileri al (Şimdilik mock, ilerde price_cache'den alınabilir)
        # Basitlik için sembolik veri gönderiyoruz, AI bunu yorumlayacak
        technical_data = {"PRICE": "Canlı Fiyat", "RSI": "50 (Nötr)", "MACD": "0 (Nötr)"}

        # 2. AI Analizi Başlat
        # Not: Senaryo ve Sinyal şimdilik 'Manuel Sorgu' varsayılıyor
        analysis_json = analyze_with_gemini(
            symbol=symbol,
            scenario_name="Kullanıcı Talebi",
            signal_type="NÖTR",
            technical_data=technical_data,
            market_type=market_type,
            save_to_db=True,
        )

        # 3. JSON Yanıtı Parse Et
        try:
            analysis_data = json.loads(analysis_json)
        except json.JSONDecodeError:
            # Fallback
            analysis_data = {
                "sentiment_score": 50,
                "sentiment_label": "NÖTR",
                "summary": ["Veri işlenemedi."],
                "explanation": "AI yanıtı formatlanamadı.",
                "error": "JSON Error",
            }

        return {
            "symbol": symbol,
            "market_type": market_type,
            "score": analysis_data.get("sentiment_label", "NÖTR"),
            "summary": analysis_data.get("explanation", ""),
            "structured_analysis": analysis_data,  # Frontend bu objeyi kullanacak
            "updated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"Analiz hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/candles/{symbol}", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_candles(
    request: Request,
    symbol: str,
    market_type: str = Query("BIST", description="Piyasa türü (BIST/Kripto)"),
    timeframe: str = Query("1d", description="Timeframe (1d, 1wk, 1mo)"),
    limit: int = Query(500, description="Number of candles (max 2000)"),
):
    """
    OHLCV mum grafiği verisi döndürür.

    Hibrit yaklaşım: Önce price_cache'e bakar, yoksa API'den çeker.
    BIST için İşyatırım, Kripto için Binance kullanır.
    """

    symbol = symbol.upper()
    limit = min(limit, 2000)  # Max limit

    # Timeframe mapping for resample
    timeframe_map = {
        "GÜNLÜK": "1D",
        "1d": "1D",
        "D": "1D",
        "HAFTALIK": "W-FRI",
        "1wk": "W-FRI",
        "W": "W-FRI",
        "2 HAFTALIK": "2W-FRI",
        "2wk": "2W-FRI",
        "3 HAFTALIK": "3W-FRI",
        "3wk": "3W-FRI",
        "AYLIK": "ME",
        "1mo": "ME",
        "M": "ME",
    }
    resample_tf = timeframe_map.get(timeframe, "1D")

    df = None
    source = "cache"

    try:
        # 1. Try price_cache first (hibrit yaklaşım)
        try:
            from price_cache import price_cache

            df = price_cache.get(symbol, market_type)
            if df is not None and not df.empty:
                source = "cache"
        except Exception as cache_err:
            print(f"Cache error for {symbol}: {cache_err}")
            df = None

        # 2. If cache miss, fetch from source
        if df is None or df.empty:
            if market_type == "BIST":
                # BIST: Use İşyatırım via data_loader
                try:
                    from data_loader import get_bist_data

                    df = get_bist_data(symbol, start_date="01-01-2010")
                    source = "isyatirim"

                    # Save to cache for next time
                    if df is not None and not df.empty:
                        try:
                            from price_cache import price_cache as pc

                            pc.set(symbol, market_type, df)
                        except Exception:
                            pass
                except Exception as bist_err:
                    print(f"BIST data error for {symbol}: {bist_err}")
                    df = None

            elif market_type in ["Kripto", "CRYPTO"]:
                # Crypto: Use Binance via data_loader
                try:
                    from data_loader import get_crypto_data

                    df = get_crypto_data(symbol, start_str="10 years ago")
                    source = "binance"

                    # Save to cache
                    if df is not None and not df.empty:
                        try:
                            from price_cache import price_cache as pc

                            pc.set(symbol, "Kripto", df)
                        except Exception:
                            pass
                except Exception as crypto_err:
                    print(f"Crypto data error for {symbol}: {crypto_err}")
                    df = None

        # 3. Final fallback: yfinance
        if df is None or df.empty:
            yf_symbol = symbol
            if market_type == "BIST" and not symbol.endswith(".IS"):
                yf_symbol = symbol + ".IS"
            elif symbol.endswith("USDT"):
                yf_symbol = symbol.replace("USDT", "-USD")

            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period="max", interval="1d")
            source = "yfinance"

            if df.empty:
                raise HTTPException(status_code=404, detail=f"{symbol} için veri bulunamadı")

        # 4. Resample if needed
        if resample_tf != "1D" and df is not None and not df.empty:
            try:
                from data_loader import resample_data

                resampled = resample_data(df, resample_tf)
                if resampled is not None and not resampled.empty:
                    df = resampled
            except Exception as resample_err:
                print(f"Resample error: {resample_err}")

        # 5. Format output
        candles = []
        if df is not None and not df.empty:
            # Take last N candles
            df_tail = df.tail(limit)

            for index, row in df_tail.iterrows():
                time_val = index.strftime("%Y-%m-%d")

                candles.append(
                    {
                        "time": time_val,
                        "open": float(row.get("Open", row.get("open", 0))),
                        "high": float(row.get("High", row.get("high", 0))),
                        "low": float(row.get("Low", row.get("low", 0))),
                        "close": float(row.get("Close", row.get("close", 0))),
                        "volume": int(row.get("Volume", row.get("volume", 0))),
                    }
                )

        return {
            "symbol": symbol,
            "market_type": market_type,
            "timeframe": resample_tf,
            "source": source,
            "count": len(candles),
            "candles": candles,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Candle error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/calendar", tags=["Calendar"])
def get_calendar(from_date: str = Query(None), to_date: str = Query(None)):
    """Ekonomik takvim verilerini getirir (Finnhub)."""
    return calendar_service.get_economic_calendar(from_date, to_date)


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
