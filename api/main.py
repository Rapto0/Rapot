"""
Otonom Analiz - FastAPI REST API
Sinyal, trade ve bot istatistiklerine erişim sağlar.

Kullanım:
    uvicorn api.main:app --reload --port 8000
"""

import math
import os
import unicodedata
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

import yfinance as yf  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException, Query, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, ConfigDict  # noqa: E402
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
from api.realtime import broadcast_bist_update, broadcast_ticker  # noqa: E402
from api.realtime import router as realtime_router  # noqa: E402
from strategy_inspector import (  # noqa: E402
    StrategyInspectorError,
    build_strategy_ai_payload,
    inspect_strategy,
    normalize_inspector_timeframe,
)

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)

# Başlangıç zamanı
_start_time = datetime.now()

import threading  # noqa: E402
from contextlib import asynccontextmanager, suppress  # noqa: E402

RUN_EMBEDDED_BOT = os.getenv("RUN_EMBEDDED_BOT", "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Uygulama yaşam döngüsü.
    Opsiyonel olarak bot scheduler döngüsünü arka plan thread'inde başlatır.
    """
    _run_startup_sequence()
    await _start_realtime_services()

    if RUN_EMBEDDED_BOT:
        # Bot Thread Başlat
        def run_scheduler():
            try:
                print("Embedded bot mode enabled in API process.")
                from scheduler import start_bot

                # Async modda çalıştır (kendi event loop'unu yönetir)
                start_bot(use_async=True)
            except Exception as e:
                print(f"Embedded bot thread error: {e}")

        # Daemon thread: Ana process kapanınca bu da kapanır
        bot_thread = threading.Thread(target=run_scheduler, daemon=True)
        bot_thread.start()

    try:
        yield
    finally:
        await _stop_realtime_services()
        print("API shutting down.")
        print("Otonom Analiz API kapatildi")


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

# Include Real-time WebSocket Router
app.include_router(realtime_router)

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
    special_tag: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SpecialTagHealthRuleResponse(BaseModel):
    """Ozel etiket kapsama kural satiri."""

    tag: str
    strategy: str
    signal_type: str
    target_timeframe: str
    candidates: int
    tagged: int
    missing: int


class SpecialTagHealthResponse(BaseModel):
    """Ozel etiket kapsama ozet durumu."""

    status: str
    stored_state: str | None = None
    market_type: str | None = None
    strategy: str | None = None
    checked_window_hours: int
    checked_window_seconds: int
    missing_total: int
    last_checked_at: str | None = None
    summary: str | None = None
    rows: list[SpecialTagHealthRuleResponse]


class StrategyInspectorTimeframeResponse(BaseModel):
    """Single timeframe inspection row."""

    code: str
    label: str
    available: bool
    signal_status: str
    reason: str | None = None
    price: float | int | None = None
    date: str | None = None
    active_indicators: str | None = None
    primary_score: str | None = None
    primary_score_label: str
    secondary_score: str | None = None
    secondary_score_label: str
    raw_score: str | None = None
    indicators: dict[str, float | int | str | None]


class StrategyInspectorResponse(BaseModel):
    """Strategy inspector response."""

    symbol: str
    market_type: str
    strategy: str
    indicator_order: list[str]
    indicator_labels: dict[str, str]
    generated_at: str
    timeframes: list[StrategyInspectorTimeframeResponse]


class MarketAnalysisResponse(BaseModel):
    """Manual AI analysis response."""

    symbol: str
    market_type: str
    strategy: str
    timeframe: str
    score: str
    summary: str
    structured_analysis: dict
    inspection: StrategyInspectorResponse
    updated_at: str


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

    model_config = ConfigDict(from_attributes=True)


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
    provider: str | None = None
    model: str | None = None
    backend: str | None = None
    prompt_version: str | None = None
    sentiment_score: int | None = None
    sentiment_label: str | None = None
    confidence_score: int | None = None
    risk_level: str | None = None
    technical_bias: str | None = None
    technical_strength: int | None = None
    news_bias: str | None = None
    news_strength: int | None = None
    headline_count: int | None = None
    latency_ms: int | None = None
    error_code: str | None = None
    created_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ==================== ENDPOINTS ====================

_SPECIAL_TAG_CODES = {"BELES", "COK_UCUZ", "PAHALI", "FAHIS_FIYAT"}
_SPECIAL_TAG_HEALTH_STATE_KEY = "special_tag_health_state"
_SPECIAL_TAG_HEALTH_SUMMARY_KEY = "special_tag_health_summary"


def _normalize_special_tag(value: str | None) -> str | None:
    if not value:
        return None

    normalized = unicodedata.normalize("NFKD", value.strip())
    normalized = normalized.encode("ascii", "ignore").decode("ascii").upper().replace(" ", "_")

    if normalized == "FAHIS":
        return "FAHIS_FIYAT"
    if normalized in _SPECIAL_TAG_CODES:
        return normalized
    return None


def _build_ai_analysis_response(analysis) -> AIAnalysisResponse:
    """AI analiz kaydını geriye uyumlu metadata ile response'a çevirir."""
    derived_metadata: dict[str, object | None] = {}
    if (
        analysis.provider is None
        or analysis.model is None
        or analysis.sentiment_label is None
        or analysis.confidence_score is None
        or analysis.risk_level is None
    ):
        try:
            from ai_analyst import extract_analysis_metadata

            derived_metadata = extract_analysis_metadata(analysis.analysis_text)
        except Exception:
            derived_metadata = {}

    return AIAnalysisResponse(
        id=analysis.id,
        signal_id=analysis.signal_id,
        symbol=analysis.symbol,
        market_type=analysis.market_type,
        scenario_name=analysis.scenario_name,
        signal_type=analysis.signal_type,
        analysis_text=analysis.analysis_text,
        technical_data=analysis.technical_data,
        provider=analysis.provider or derived_metadata.get("provider"),
        model=analysis.model or derived_metadata.get("model"),
        backend=analysis.backend or derived_metadata.get("backend"),
        prompt_version=analysis.prompt_version or derived_metadata.get("prompt_version"),
        sentiment_score=analysis.sentiment_score
        if analysis.sentiment_score is not None
        else derived_metadata.get("sentiment_score"),
        sentiment_label=analysis.sentiment_label or derived_metadata.get("sentiment_label"),
        confidence_score=analysis.confidence_score
        if analysis.confidence_score is not None
        else derived_metadata.get("confidence_score"),
        risk_level=analysis.risk_level or derived_metadata.get("risk_level"),
        technical_bias=analysis.technical_bias or derived_metadata.get("technical_bias"),
        technical_strength=analysis.technical_strength
        if analysis.technical_strength is not None
        else derived_metadata.get("technical_strength"),
        news_bias=analysis.news_bias or derived_metadata.get("news_bias"),
        news_strength=analysis.news_strength
        if analysis.news_strength is not None
        else derived_metadata.get("news_strength"),
        headline_count=analysis.headline_count
        if analysis.headline_count is not None
        else derived_metadata.get("headline_count"),
        latency_ms=analysis.latency_ms,
        error_code=analysis.error_code or derived_metadata.get("error_code"),
        created_at=analysis.created_at.isoformat() if analysis.created_at else None,
    )


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


@app.get("/ops/special-tag-health", response_model=SpecialTagHealthResponse, tags=["Operations"])
@limiter.limit("20/minute")
async def get_special_tag_health(
    request: Request,
    market_type: str = Query("BIST", description="Piyasa tipi (BIST/Kripto/ALL)"),
    strategy: str | None = Query(None, description="Strateji filtresi (COMBO/HUNTER)"),
    since_hours: int = Query(24, ge=1, le=720, description="Geri bakis penceresi (saat)"),
    window_seconds: int = Query(
        900, ge=0, le=86400, description="Kural eslesme toleransi (saniye)"
    ),
):
    """
    Ozel sinyal etiketleme kapsama durumunu dondurur.

    Ops kullanimi icindir. Scheduler tarafindaki health check ile ayni veri kaynagini kullanir.
    """
    from database import db, get_special_tag_coverage

    normalized_market = market_type.strip().upper()
    if normalized_market == "ALL":
        effective_market_type = None
        market_label = "ALL"
    elif normalized_market == "BIST":
        effective_market_type = "BIST"
        market_label = "BIST"
    elif normalized_market in {"KRIPTO", "KRPITO", "KRYPTO"}:
        effective_market_type = "Kripto"
        market_label = "Kripto"
    else:
        raise HTTPException(
            status_code=400, detail="Gecersiz market_type. BIST, Kripto veya ALL kullanin."
        )

    normalized_strategy = strategy.strip().upper() if strategy else None
    if normalized_strategy not in {None, "COMBO", "HUNTER"}:
        raise HTTPException(
            status_code=400, detail="Gecersiz strategy. COMBO veya HUNTER kullanin."
        )

    coverage_rows = get_special_tag_coverage(
        since_hours=since_hours,
        market_type=effective_market_type,
        strategy=normalized_strategy,
        window_seconds=window_seconds,
    )
    missing_total = sum(int(row.get("missing", 0)) for row in coverage_rows)

    with db.get_cursor() as cursor:
        cursor.execute(
            """
            SELECT MAX(updated_at)
            FROM bot_stats
            WHERE stat_name IN (?, ?)
            """,
            (_SPECIAL_TAG_HEALTH_STATE_KEY, _SPECIAL_TAG_HEALTH_SUMMARY_KEY),
        )
        last_checked_raw = cursor.fetchone()[0]

    if isinstance(last_checked_raw, datetime):
        last_checked_at = last_checked_raw.isoformat()
    elif last_checked_raw:
        last_checked_at = str(last_checked_raw)
    else:
        last_checked_at = None

    stored_state = db.get_stat(_SPECIAL_TAG_HEALTH_STATE_KEY)
    summary = db.get_stat(_SPECIAL_TAG_HEALTH_SUMMARY_KEY)

    return SpecialTagHealthResponse(
        status="alert" if missing_total > 0 else "ok",
        stored_state=stored_state,
        market_type=market_label,
        strategy=normalized_strategy,
        checked_window_hours=since_hours,
        checked_window_seconds=window_seconds,
        missing_total=missing_total,
        last_checked_at=last_checked_at,
        summary=summary or None,
        rows=[SpecialTagHealthRuleResponse(**row) for row in coverage_rows],
    )


@app.get(
    "/ops/strategy-inspector",
    response_model=StrategyInspectorResponse,
    tags=["Operations"],
)
@limiter.limit("30/minute")
async def get_strategy_inspector(
    request: Request,
    symbol: str = Query(..., min_length=1, max_length=20, description="Sembol"),
    strategy: str = Query(..., description="Strateji (COMBO/HUNTER)"),
    market_type: str | None = Query(
        None,
        description="Piyasa tipi (BIST/Kripto/AUTO)",
    ),
):
    """
    Tek sembol icin strateji indikator dump'i dondurur.

    Telegram inspector araci ve frontend denetim paneli bu endpoint'i kullanir.
    """
    try:
        report = inspect_strategy(symbol=symbol, strategy=strategy, market_type=market_type)
    except StrategyInspectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API path
        raise HTTPException(status_code=500, detail="Strategy inspector hesaplanamadi.") from exc

    return StrategyInspectorResponse(
        symbol=report["symbol"],
        market_type=report["market_type"],
        strategy=report["strategy"],
        indicator_order=list(report["indicator_order"]),
        indicator_labels=dict(report["indicator_labels"]),
        generated_at=report["generated_at"],
        timeframes=[
            StrategyInspectorTimeframeResponse(
                code=timeframe["code"],
                label=timeframe["label"],
                available=bool(timeframe["available"]),
                signal_status=str(timeframe["signal_status"]),
                reason=timeframe.get("reason"),
                price=timeframe.get("price"),
                date=timeframe.get("date"),
                active_indicators=timeframe.get("active_indicators"),
                primary_score=timeframe.get("primary_score"),
                primary_score_label=str(timeframe["primary_score_label"]),
                secondary_score=timeframe.get("secondary_score"),
                secondary_score_label=str(timeframe["secondary_score_label"]),
                raw_score=timeframe.get("raw_score"),
                indicators=dict(timeframe.get("indicators", {})),
            )
            for timeframe in report["timeframes"]
        ],
    )


@app.get("/signals", response_model=list[SignalResponse], tags=["Signals"])
@limiter.limit("60/minute")
async def get_signals(
    request: Request,
    symbol: str | None = Query(None, description="Sembol filtresi"),
    strategy: str | None = Query(None, description="Strateji filtresi (COMBO/HUNTER)"),
    signal_type: str | None = Query(None, description="Sinyal türü (AL/SAT)"),
    market_type: str | None = Query(None, description="Piyasa türü (BIST/Kripto)"),
    special_tag: str | None = Query(
        None,
        description="Ozel etiket filtresi (BELES/COK_UCUZ/PAHALI/FAHIS_FIYAT)",
    ),
    limit: int = Query(50, ge=1, le=1000, description="Maksimum kayıt sayısı"),
):
    """
    Sinyal listesini döndürür.

    Opsiyonel filtreler: symbol, strategy, signal_type, market_type, special_tag
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
        if market_type:
            query = query.filter(Signal.market_type == market_type)

        normalized_special_tag = _normalize_special_tag(special_tag)
        if special_tag is not None and normalized_special_tag is None:
            return []
        if normalized_special_tag:
            query = query.filter(Signal.special_tag == normalized_special_tag)

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
                created_at=s.created_at.isoformat() + "Z" if s.created_at else None,
                special_tag=s.special_tag,
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
            special_tag=signal.special_tag,
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

        return [_build_ai_analysis_response(a) for a in analyses]


@app.get("/analyses/{analysis_id}", response_model=AIAnalysisResponse, tags=["AI Analysis"])
async def get_analysis(analysis_id: int):
    """Belirli bir AI analizini döndürür."""
    from db_session import get_session
    from models import AIAnalysis

    with get_session() as session:
        analysis = session.query(AIAnalysis).filter(AIAnalysis.id == analysis_id).first()

        if not analysis:
            raise HTTPException(status_code=404, detail="Analiz bulunamadı")

        return _build_ai_analysis_response(analysis)


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

        return _build_ai_analysis_response(analysis)


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
            # yfinance period values do not support "24h"; use "1d" for the last day
            df = ticker.history(period="1d", interval="15m")

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


@app.get("/market/indices", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_market_indices(
    request: Request,
    symbol: list[str] = Query(
        default=["^GSPC", "^NDX", "XU100.IS"],
        description="Global endeks sembolleri. Örnek: ?symbol=^GSPC&symbol=^NDX&symbol=XU100.IS",
    ),
):
    """
    Landing sayfası için global endeks özet verisi döndürür.
    """
    try:
        display_names = {
            "^GSPC": "S&P 500",
            "^NDX": "Nasdaq 100",
            "XU100.IS": "BIST 100",
        }

        unique_symbols = []
        for raw_symbol in symbol:
            normalized = raw_symbol.strip().upper()
            if not normalized:
                continue
            if normalized in unique_symbols:
                continue
            unique_symbols.append(normalized)

        unique_symbols = unique_symbols[:10]

        items = []
        for ticker_symbol in unique_symbols:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period="2d")
            if hist.empty:
                hist = ticker.history(period="5d")

            if hist.empty:
                continue

            close_series = hist.get("Close")
            open_series = hist.get("Open")
            if close_series is None:
                continue

            close_values = close_series.dropna()
            if close_values.empty:
                continue

            current_price = float(close_values.iloc[-1])
            if not math.isfinite(current_price):
                continue

            if len(close_values) > 1:
                previous_close = float(close_values.iloc[-2])
            elif open_series is not None and not open_series.dropna().empty:
                previous_close = float(open_series.dropna().iloc[-1])
            else:
                previous_close = current_price

            if not math.isfinite(previous_close):
                previous_close = current_price

            change_percent = (
                ((current_price - previous_close) / previous_close) * 100 if previous_close else 0.0
            )

            items.append(
                {
                    "symbol": ticker_symbol,
                    "regularMarketPrice": current_price,
                    "regularMarketChangePercent": change_percent,
                    "shortName": display_names.get(ticker_symbol, ticker_symbol),
                }
            )

        return items

    except Exception as e:
        print(f"Market indices error: {e}")
        return []


@app.get("/scans", tags=["System"])
@limiter.limit("30/minute")
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
@limiter.limit("30/minute")
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


def _select_manual_analysis_timeframes(
    report: dict, timeframe_code: str | None
) -> tuple[str, list[dict]]:
    normalized_timeframe = normalize_inspector_timeframe(timeframe_code)
    if normalized_timeframe is None:
        return "ALL", list(report["timeframes"])

    selected_timeframes = [
        timeframe for timeframe in report["timeframes"] if timeframe["code"] == normalized_timeframe
    ]
    if not selected_timeframes:
        raise StrategyInspectorError(f"Periyot bulunamadi: {normalized_timeframe}")
    return normalized_timeframe, selected_timeframes


def _derive_manual_signal_type(selected_timeframes: list[dict]) -> str:
    buy_count = sum(
        1 for timeframe in selected_timeframes if timeframe.get("signal_status") == "AL"
    )
    sell_count = sum(
        1 for timeframe in selected_timeframes if timeframe.get("signal_status") == "SAT"
    )

    if buy_count > sell_count:
        return "AL"
    if sell_count > buy_count:
        return "SAT"
    return "NOTR"


def _build_strategy_inspector_response(report: dict) -> StrategyInspectorResponse:
    return StrategyInspectorResponse(
        symbol=report["symbol"],
        market_type=report["market_type"],
        strategy=report["strategy"],
        indicator_order=list(report["indicator_order"]),
        indicator_labels=dict(report["indicator_labels"]),
        generated_at=report["generated_at"],
        timeframes=[
            StrategyInspectorTimeframeResponse(
                code=timeframe["code"],
                label=timeframe["label"],
                available=bool(timeframe["available"]),
                signal_status=timeframe["signal_status"],
                reason=timeframe.get("reason"),
                price=timeframe.get("price"),
                date=timeframe.get("date"),
                active_indicators=timeframe.get("active_indicators"),
                primary_score=timeframe.get("primary_score"),
                primary_score_label=timeframe["primary_score_label"],
                secondary_score=timeframe.get("secondary_score"),
                secondary_score_label=timeframe["secondary_score_label"],
                raw_score=timeframe.get("raw_score"),
                indicators=dict(timeframe.get("indicators", {})),
            )
            for timeframe in report["timeframes"]
        ],
    )


@app.get("/api/market/analysis", response_model=MarketAnalysisResponse, tags=["AI Analysis"])
def get_market_analysis(
    market_type: str | None = Query(
        None,
        description="Piyasa tipi: BIST, Kripto veya AUTO",
    ),
    symbol: str = Query(..., description="Sembol"),
    strategy: str = Query("HUNTER", description="Strateji: COMBO veya HUNTER"),
    timeframe: str | None = Query(
        None,
        description="Periyot: 1D, 1W, 2W, 3W, 1M veya ALL",
    ),
):
    """
    Belirli bir sembol icin gercek teknik veriyle AI yorumu getirir.
    """
    try:
        from ai_analyst import analyze_with_gemini
        from ai_schema import AIResponseSchemaError, build_ai_error_payload, parse_ai_response

        report = inspect_strategy(symbol=symbol, strategy=strategy, market_type=market_type)
        resolved_timeframe, selected_timeframes = _select_manual_analysis_timeframes(
            report, timeframe
        )
        signal_type = _derive_manual_signal_type(selected_timeframes)
        technical_data = build_strategy_ai_payload(
            report=report,
            signal_type=signal_type,
            trigger_rule=[item["code"] for item in selected_timeframes],
            matched_timeframes=[item["code"] for item in selected_timeframes],
            scenario_name=f"MANUAL_{report['strategy']}_{resolved_timeframe}",
        )

        analysis_json = analyze_with_gemini(
            symbol=report["symbol"],
            scenario_name=f"MANUAL_{report['strategy']}_{resolved_timeframe}",
            signal_type=signal_type,
            technical_data=technical_data,
            market_type=report["market_type"],
            save_to_db=False,
        )

        try:
            analysis_data = parse_ai_response(analysis_json).model_dump(mode="json")
        except AIResponseSchemaError as exc:
            analysis_data = parse_ai_response(
                build_ai_error_payload(
                    error=str(exc),
                    error_code=exc.error_code,
                    provider="gemini",
                    model_name=None,
                    backend=None,
                    prompt_version=None,
                    summary="Veri islenemedi.",
                    explanation="AI yaniti formatlanamadi.",
                )
            ).model_dump(mode="json")

        return MarketAnalysisResponse(
            symbol=report["symbol"],
            market_type=report["market_type"],
            strategy=report["strategy"],
            timeframe=resolved_timeframe,
            score=analysis_data.get("sentiment_label", "NOTR"),
            summary=analysis_data.get("explanation", ""),
            structured_analysis=analysis_data,
            inspection=_build_strategy_inspector_response(
                {**report, "timeframes": selected_timeframes}
            ),
            updated_at=datetime.now().isoformat(),
        )

    except StrategyInspectorError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as e:
        print(f"Analiz hatasi: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/candles/{symbol}", tags=["Market Data"])
@limiter.limit("20/minute")
async def get_candles(
    request: Request,
    symbol: str,
    market_type: str = Query("BIST", description="Piyasa türü (BIST/Kripto)"),
    timeframe: str = Query(
        "1d",
        description="Timeframe (15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 2d, 3d, 4d, 5d, 6d, 1wk, 1mo)",
    ),
    limit: int = Query(500, description="Number of candles (max 2000)"),
):
    """
    OHLCV mum grafiği verisi döndürür.

    Hibrit yaklaşım: Önce price_cache'e bakar, yoksa API'den çeker.
    BIST için İşyatırım, Kripto için Binance kullanır.
    """

    symbol = symbol.upper()
    limit = min(limit, 2000)  # Max limit

    # Extended timeframe mapping
    # For resample (daily data -> larger timeframes)
    resample_map = {
        "GÜNLÜK": "1D",
        "1d": "1D",
        "D": "1D",
        "2d": "2D",
        "3d": "3D",
        "4d": "4D",
        "5d": "5D",
        "6d": "6D",
        "HAFTALIK": "W-FRI",
        "1wk": "W-FRI",
        "W": "W-FRI",
        "2wk": "2W-FRI",
        "2 HAFTALIK": "2W-FRI",
        "3wk": "3W-FRI",
        "3 HAFTALIK": "3W-FRI",
        "AYLIK": "ME",
        "1mo": "ME",
        "2mo": "2ME",
        "3mo": "3ME",
        "M": "ME",
    }

    # Binance interval mapping for intraday crypto data
    binance_interval_map = {
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "8h": "8h",
        "12h": "12h",
        "18h": "12h",  # Binance doesn't have 18h, use 12h
        "1d": "1d",
        "2d": "1d",  # Will resample from daily
        "3d": "3d",
        "1wk": "1w",
        "2wk": "1w",  # Will resample
        "3wk": "1w",  # Will resample
        "1mo": "1M",
        "2mo": "1M",  # Will resample
        "3mo": "1M",  # Will resample
    }

    # Check if this is an intraday timeframe
    is_intraday = timeframe in ["15m", "30m", "1h", "2h", "4h", "8h", "12h", "18h"]
    resample_tf = resample_map.get(timeframe, "1D")
    binance_interval = binance_interval_map.get(timeframe, "1d")

    df = None
    source = "cache"

    try:
        # For BIST with intraday: Use yfinance
        if market_type == "BIST" and is_intraday:
            try:
                import pandas as pd
                import pytz

                yf_symbol = symbol + ".IS" if not symbol.endswith(".IS") else symbol
                # NOTE:
                # yfinance 1h bars for BIST are often misaligned and sometimes sparse compared with TradingView.
                # For 1h, pull denser 15m bars and resample locally for better bar continuity/alignment.
                if timeframe in ["15m", "30m"]:
                    yf_interval = timeframe
                    period = "60d"
                elif timeframe == "1h":
                    yf_interval = "15m"
                    period = "60d"
                else:
                    yf_interval = "1h"
                    period = "730d"

                ticker = yf.Ticker(yf_symbol)
                df = ticker.history(
                    period=period,
                    interval=yf_interval,
                    auto_adjust=False,
                    actions=False,
                )

                if df is not None and not df.empty:
                    turkey_tz = pytz.timezone("Europe/Istanbul")
                    if hasattr(df.index, "tz") and df.index.tz is not None:
                        df.index = df.index.tz_convert(turkey_tz)
                    else:
                        with suppress(Exception):
                            df.index = df.index.tz_localize("UTC").tz_convert(turkey_tz)

                    agg_map = {
                        "Open": "first",
                        "High": "max",
                        "Low": "min",
                        "Close": "last",
                        "Volume": "sum",
                    }

                    if timeframe == "30m" and yf_interval == "15m":
                        df = (
                            df.resample("30min", label="left", closed="left", origin="start_day")
                            .agg(agg_map)
                            .dropna()
                        )
                    elif timeframe == "1h" and yf_interval == "15m":
                        df = (
                            df.resample("1h", label="left", closed="left", origin="start_day")
                            .agg(agg_map)
                            .dropna()
                        )
                    # Resample if needed (2h, 4h, 8h, 12h)
                    elif timeframe in ["2h", "4h", "8h", "12h"]:
                        hours = int(timeframe.replace("h", ""))
                        df = (
                            df.resample(
                                f"{hours}h", label="left", closed="left", origin="start_day"
                            )
                            .agg(agg_map)
                            .dropna()
                        )
                    source = (
                        "yfinance_intraday_resampled"
                        if timeframe != yf_interval
                        else "yfinance_intraday"
                    )
            except Exception as yf_err:
                print(f"yfinance intraday error for {symbol}: {yf_err}")
                df = None

        # For Crypto with intraday: Fetch directly from Binance with the interval
        elif market_type in ["Kripto", "CRYPTO"] and is_intraday:
            try:
                import pandas as pd
                from binance.client import Client

                client = Client()
                klines = client.get_klines(symbol=symbol, interval=binance_interval, limit=limit)

                if klines:
                    df = pd.DataFrame(
                        klines,
                        columns=[
                            "timestamp",
                            "Open",
                            "High",
                            "Low",
                            "Close",
                            "Volume",
                            "close_time",
                            "quote_volume",
                            "trades",
                            "taker_buy_base",
                            "taker_buy_quote",
                            "ignore",
                        ],
                    )
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                    df.set_index("timestamp", inplace=True)
                    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)
                    source = "binance"
            except Exception as binance_err:
                print(f"Binance intraday error for {symbol}: {binance_err}")
                df = None

        # For non-intraday or if intraday failed, use standard approach
        if df is None or df.empty:
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
                            with suppress(Exception):
                                from price_cache import price_cache as pc

                                pc.set(symbol, market_type, df)
                    except Exception as bist_err:
                        print(f"BIST data error for {symbol}: {bist_err}")
                        df = None

                elif market_type in ["Kripto", "CRYPTO"]:
                    # Crypto: Use Binance via data_loader (daily data)
                    try:
                        from data_loader import get_crypto_data

                        df = get_crypto_data(symbol, start_str="10 years ago")
                        source = "binance"

                        # Save to cache
                        if df is not None and not df.empty:
                            with suppress(Exception):
                                from price_cache import price_cache as pc

                                pc.set(symbol, "Kripto", df)
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

        # 4. Resample if needed (only for daily+ data, not for intraday)
        if not is_intraday and resample_tf != "1D" and df is not None and not df.empty:
            try:
                from data_loader import resample_data

                resampled = resample_data(df, resample_tf)
                if resampled is not None and not resampled.empty:
                    df = resampled
            except Exception as resample_err:
                print(f"Resample error: {resample_err}")

        # 5. Format output with Turkey timezone conversion
        import pytz

        turkey_tz = pytz.timezone("Europe/Istanbul")
        candles = []
        if df is not None and not df.empty:
            # Take last N candles
            df_tail = df.tail(limit)

            for index, row in df_tail.iterrows():
                # Convert index to Turkey timezone if it's timezone-aware
                ts = index
                if is_intraday:
                    # Convert UTC to Turkey timezone for intraday data
                    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
                        ts = ts.astimezone(turkey_tz)
                    elif hasattr(ts, "tz_localize"):
                        with suppress(Exception):
                            ts = ts.tz_localize("UTC").tz_convert(turkey_tz)
                    time_val = ts.strftime("%Y-%m-%d %H:%M")
                else:
                    time_val = ts.strftime("%Y-%m-%d")

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
            "timeframe": timeframe,
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


def _run_startup_sequence() -> None:
    """Uygulama baslangicinda gerekli senkron hazirligi yapar."""
    from db_session import init_db

    init_db()


async def _start_realtime_services() -> None:
    """Real-time servislerini baslatir."""
    try:
        from bist_service import bist_service
        from websocket_manager import ws_manager

        ws_manager.on("ticker", broadcast_ticker)
        bist_service.on_update(broadcast_bist_update)

        await ws_manager.start()
        await bist_service.start()
        print("Real-time WebSocket services started")
        print("Otonom Analiz API baslatildi")
    except Exception as e:
        print(f"Real-time services failed to start: {e}")


async def _stop_realtime_services() -> None:
    """Real-time servislerini kapatir."""
    try:
        from bist_service import bist_service
        from websocket_manager import ws_manager

        await ws_manager.stop()
        await bist_service.stop()
        print("Real-time services stopped")
    except Exception as e:
        print(f"Error stopping real-time services: {e}")
