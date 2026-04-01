"""
Otonom Analiz - FastAPI REST API
Sinyal, trade ve bot istatistiklerine erişim sağlar.

Kullanım:
    uvicorn api.main:app --reload --port 8000
"""

import math
import unicodedata
from datetime import datetime, timedelta

import yfinance as yf  # noqa: E402
from fastapi import FastAPI, HTTPException, Query, Request, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel, ConfigDict  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402

from api.contracts.health_contract import build_health_payload  # noqa: E402
from api.rate_limit import limiter  # noqa: E402
from api.realtime import router as realtime_router  # noqa: E402
from api.routes.auth_routes import router as auth_router  # noqa: E402
from api.routes.calendar_routes import router as calendar_router  # noqa: E402
from api.routes.symbols_routes import router as symbols_router  # noqa: E402
from api.routes.system_routes import router as system_router  # noqa: E402
from api.runtime.realtime_bootstrap import (  # noqa: E402
    start_realtime_services as runtime_start_realtime_services,
)
from api.runtime.realtime_bootstrap import (  # noqa: E402
    stop_realtime_services as runtime_stop_realtime_services,
)
from logger import get_logger  # noqa: E402
from settings import settings  # noqa: E402
from state_keys import SPECIAL_TAG_HEALTH_STATE_KEY, SPECIAL_TAG_HEALTH_SUMMARY_KEY  # noqa: E402
from strategy_inspector import (  # noqa: E402
    StrategyInspectorError,
    build_strategy_ai_payload,
    inspect_strategy,
    normalize_inspector_timeframe,
)

# Başlangıç zamanı
_start_time = datetime.now()

import threading  # noqa: E402
from contextlib import asynccontextmanager, suppress  # noqa: E402

RUN_EMBEDDED_BOT = bool(settings.run_embedded_bot)
CORS_ALLOW_ORIGINS = settings.cors_origins_list
# Credentials + wildcard kombinasyonu tarayici tarafinda desteklenmez.
CORS_ALLOW_CREDENTIALS = bool(settings.cors_allow_credentials)
if "*" in CORS_ALLOW_ORIGINS:
    CORS_ALLOW_CREDENTIALS = False

logger = get_logger(__name__)

_RUNTIME_STATE = {
    "db_ready": False,
    "realtime_ready": False,
    "realtime_error": None,
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
                logger.info("Embedded bot mode enabled in API process.")
                from scheduler import start_bot

                # Async modda çalıştır (kendi event loop'unu yönetir)
                start_bot(use_async=True)
            except Exception:
                logger.exception("Embedded bot thread error.")

        # Daemon thread: Ana process kapanınca bu da kapanır
        bot_thread = threading.Thread(target=run_scheduler, daemon=True)
        bot_thread.start()

    try:
        yield
    finally:
        await _stop_realtime_services()
        logger.info("API shutting down.")
        logger.info("Otonom Analiz API kapatildi")


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
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Real-time WebSocket Router
app.include_router(realtime_router)
app.include_router(auth_router)
app.include_router(calendar_router)
app.include_router(symbols_router)
app.include_router(system_router)

# ==================== SCHEMAS ====================


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı."""

    status: str
    uptime_seconds: float
    uptime_human: str
    database: str
    realtime: str
    version: str
    timestamp: str


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
    details: dict[str, float | int | str | bool | None] | str | None = None

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


class MarketHistoryPointResponse(BaseModel):
    """Single market history datapoint."""

    time: str
    value: float


class MarketSeriesResponse(BaseModel):
    """Market overview row."""

    currentValue: float
    change: float
    history: list[MarketHistoryPointResponse]


class MarketOverviewResponse(BaseModel):
    """Market overview payload."""

    bist: MarketSeriesResponse
    crypto: MarketSeriesResponse


class MarketIndexResponse(BaseModel):
    """Global index/ticker row for landing feed."""

    symbol: str
    regularMarketPrice: float
    regularMarketChangePercent: float
    shortName: str


class MarketTickerResponse(BaseModel):
    """Ticker strip row."""

    symbol: str
    name: str
    price: float
    change: float
    changePercent: float


class MarketMetricsItemResponse(BaseModel):
    """Scanner metrics row."""

    latest_price: float
    change_pct: float | None = None
    perf_7d: float | None = None
    perf_30d: float | None = None
    source: str | None = None


class CandlePointResponse(BaseModel):
    """Single candle row."""

    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class CandlesResponse(BaseModel):
    """Candles endpoint response."""

    symbol: str
    market_type: str
    timeframe: str
    source: str
    count: int
    candles: list[CandlePointResponse]


# ==================== ENDPOINTS ====================

_SPECIAL_TAG_CODES = {"BELES", "COK_UCUZ", "PAHALI", "FAHIS_FIYAT"}
_SPECIAL_TAG_HEALTH_STATE_KEY = SPECIAL_TAG_HEALTH_STATE_KEY
_SPECIAL_TAG_HEALTH_SUMMARY_KEY = SPECIAL_TAG_HEALTH_SUMMARY_KEY
_MARKET_INDEX_CANONICAL = {
    # Yahoo tarafinda spot altin/gumus bazi hesaplarda 404 donebildigi icin
    # emtia futures sembollerine canonical map uyguluyoruz.
    "XAUUSD=X": "GC=F",
    "XAGUSD=X": "SI=F",
}
_MARKET_INDEX_FALLBACKS = {
    "XAUUSD=X": "GC=F",
    "XAGUSD=X": "SI=F",
}
_MARKET_INDEX_CACHE_TTL = timedelta(seconds=5)
_market_index_cache: dict[str, tuple[datetime, dict[str, float | str]]] = {}
_MARKET_OVERVIEW_CACHE_TTL = timedelta(seconds=15)
_market_overview_cache: tuple[datetime, dict[str, dict]] | None = None
_MARKET_TICKER_CACHE_TTL = timedelta(seconds=10)
_market_ticker_cache: tuple[datetime, list[dict[str, float | str]]] | None = None
_market_data_provider = None


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


def _fetch_history_with_fallback(
    symbol: str,
    *,
    period: str = "2d",
    fallback_period: str | None = "5d",
    interval: str | None = None,
    auto_adjust: bool = False,
    actions: bool = False,
):
    """Fetch yfinance history with an optional fallback period."""
    ticker = yf.Ticker(symbol)
    kwargs = {"period": period, "auto_adjust": auto_adjust, "actions": actions}
    if interval:
        kwargs["interval"] = interval
    df = ticker.history(**kwargs)
    if fallback_period and df.empty:
        kwargs["period"] = fallback_period
        df = ticker.history(**kwargs)
    return df


def _fetch_yfinance_download(tickers: str | list[str]):
    """Batch download helper for yfinance."""
    return yf.download(
        tickers=tickers,
        period="3mo",
        interval="1d",
        auto_adjust=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )


def _fetch_binance_klines(symbol: str, interval: str, limit: int):
    """Blocking Binance client call extracted for thread offload."""
    from binance.client import Client

    client = Client()
    return client.get_klines(symbol=symbol, interval=interval, limit=limit)


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
async def health_check(request: Request, response: Response):
    """
    Sistem sağlık kontrolü.

    Bot durumu, uptime ve veritabanı bağlantısını kontrol eder.
    """
    uptime = (datetime.now() - _start_time).total_seconds()

    # Veritabanı kontrolü
    db_ok = bool(_RUNTIME_STATE.get("db_ready"))
    db_status = "error"
    if db_ok:
        try:
            from db_session import get_table_stats

            _ = get_table_stats()
            db_status = "connected"
        except Exception:
            db_ok = False
            db_status = "error"
            logger.exception("Health check DB probe failed.")

    realtime_ok = bool(_RUNTIME_STATE.get("realtime_ready"))
    realtime_status = "running" if realtime_ok else "error"

    overall_status = "healthy" if db_ok and realtime_ok else "unhealthy"
    if overall_status != "healthy":
        response.status_code = 503

    payload = build_health_payload(
        status=overall_status,
        uptime_seconds=uptime,
        database=db_status,
        realtime=realtime_status,
        version="1.0.0",
    )
    return HealthResponse(**payload)


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
    from infrastructure.persistence.ops_repository import (
        get_bot_stat,
        get_bot_stats_last_updated,
        get_special_tag_coverage,
    )

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

    last_checked_raw = get_bot_stats_last_updated(
        (_SPECIAL_TAG_HEALTH_STATE_KEY, _SPECIAL_TAG_HEALTH_SUMMARY_KEY)
    )
    if isinstance(last_checked_raw, datetime):
        last_checked_at = last_checked_raw.isoformat()
    elif last_checked_raw:
        last_checked_at = str(last_checked_raw)
    else:
        last_checked_at = None

    stored_state = get_bot_stat(_SPECIAL_TAG_HEALTH_STATE_KEY)
    summary = get_bot_stat(_SPECIAL_TAG_HEALTH_SUMMARY_KEY)

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
    from application.services.signal_trade_service import list_signals as list_signals_service

    normalized_special_tag = _normalize_special_tag(special_tag)
    if special_tag is not None and normalized_special_tag is None:
        return []

    signal_rows = list_signals_service(
        symbol=symbol,
        strategy=strategy,
        signal_type=signal_type,
        market_type=market_type,
        special_tag=normalized_special_tag,
        limit=limit,
    )
    return [SignalResponse(**row) for row in signal_rows]


@app.get("/signals/{signal_id}", response_model=SignalResponse, tags=["Signals"])
async def get_signal(signal_id: int):
    """Belirli bir sinyali döndürür."""
    from application.services.signal_trade_service import get_signal_by_id

    signal = get_signal_by_id(signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Sinyal bulunamadı")
    return SignalResponse(**signal)


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
    from application.services.signal_trade_service import list_trades as list_trades_service

    trade_rows = list_trades_service(symbol=symbol, status=status, limit=limit)
    return [TradeResponse(**row) for row in trade_rows]


@app.get("/stats", response_model=StatsResponse, tags=["Statistics"])
@limiter.limit("60/minute")
async def get_stats(request: Request):
    """
    Bot ve trade istatistiklerini döndürür.
    """
    from application.services.signal_trade_service import get_trade_stats_summary

    stats = get_trade_stats_summary()
    return StatsResponse(**stats)


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
    from application.services.analysis_service import list_ai_analyses

    analyses = list_ai_analyses(symbol=symbol, market_type=market_type, limit=limit)
    return [_build_ai_analysis_response(a) for a in analyses]


@app.get("/analyses/{analysis_id}", response_model=AIAnalysisResponse, tags=["AI Analysis"])
async def get_analysis(analysis_id: int):
    """Belirli bir AI analizini döndürür."""
    from application.services.analysis_service import get_ai_analysis_by_id

    analysis = get_ai_analysis_by_id(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı")
    return _build_ai_analysis_response(analysis)


@app.get(
    "/signals/{signal_id}/analysis", response_model=AIAnalysisResponse | None, tags=["AI Analysis"]
)
async def get_signal_analysis(signal_id: int):
    """Belirli bir sinyale ait AI analizini döndürür."""
    from application.services.analysis_service import get_ai_analysis_by_signal_id

    analysis = get_ai_analysis_by_signal_id(signal_id)
    if not analysis:
        return None
    return _build_ai_analysis_response(analysis)


@app.get("/market/overview", response_model=MarketOverviewResponse, tags=["Market Data"])
@limiter.limit("5/minute")
async def get_market_overview(request: Request):
    """
    Piyasa genel bakış verilerini döndürür (BIST 100 ve Bitcoin).
    Son 24 saatlik mini grafik verisi içerir.
    """
    global _market_overview_cache
    now = datetime.now()
    if _market_overview_cache and now - _market_overview_cache[0] <= _MARKET_OVERVIEW_CACHE_TTL:
        return _market_overview_cache[1]

    try:
        from application.services.market_data_service import build_market_overview_payload

        data = await build_market_overview_payload(provider=_get_market_data_provider())
        _market_overview_cache = (now, data)
        return data

    except Exception:
        logger.exception("Market overview error.")
        fallback = {
            "bist": {"currentValue": 0, "change": 0, "history": []},
            "crypto": {"currentValue": 0, "change": 0, "history": []},
        }
        _market_overview_cache = (now, fallback)
        return fallback


@app.get("/market/indices", response_model=list[MarketIndexResponse], tags=["Market Data"])
@limiter.limit("240/minute")
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
        from application.services.market_data_service import build_market_indices_payload

        return await build_market_indices_payload(
            symbols=symbol,
            market_index_cache=_market_index_cache,
            market_index_cache_ttl=_MARKET_INDEX_CACHE_TTL,
            market_index_canonical=_MARKET_INDEX_CANONICAL,
            market_index_fallbacks=_MARKET_INDEX_FALLBACKS,
            provider=_get_market_data_provider(),
        )

    except Exception:
        logger.exception("Market indices error.")
        return []


@app.get("/market/ticker", response_model=list[MarketTickerResponse], tags=["Market Data"])
@limiter.limit("20/minute")
async def get_market_ticker(request: Request):
    """
    Header ticker için popüler sembol verilerini döndürür.
    """
    global _market_ticker_cache
    now = datetime.now()
    if _market_ticker_cache and now - _market_ticker_cache[0] <= _MARKET_TICKER_CACHE_TTL:
        return _market_ticker_cache[1]

    try:
        from application.services.market_data_service import build_market_ticker_payload

        tickers = await build_market_ticker_payload(provider=_get_market_data_provider())
        _market_ticker_cache = (now, tickers)
        return tickers

    except Exception:
        logger.exception("Ticker error.")
        _market_ticker_cache = (now, [])
        return []


def _extract_close_series_from_download(download_df, ticker: str):
    """yfinance multi/single download sonucundan close serisini cikarir."""
    try:
        import pandas as pd
    except Exception:
        return None

    if download_df is None or getattr(download_df, "empty", True):
        return None

    close_series = None

    columns = getattr(download_df, "columns", None)
    if isinstance(columns, pd.MultiIndex):
        level0 = set(columns.get_level_values(0))
        level1 = set(columns.get_level_values(1))

        if ticker in level0:
            with suppress(Exception):
                ticker_df = download_df[ticker]
                if "Close" in ticker_df.columns:
                    close_series = ticker_df["Close"]
        elif ticker in level1:
            with suppress(Exception):
                close_series = download_df["Close"][ticker]
    else:
        if "Close" in download_df.columns:
            close_series = download_df["Close"]

    if close_series is None:
        return None
    close_series = close_series.dropna()
    if close_series.empty:
        return None
    return close_series


def _calculate_market_metric_payload(close_series):
    """Close serisinden latest/change/perf7/perf30 metriclerini hesaplar."""
    if close_series is None or len(close_series) == 0:
        return None

    latest = float(close_series.iloc[-1])
    previous = float(close_series.iloc[-2]) if len(close_series) > 1 else None
    latest_ts = close_series.index[-1]

    target_7 = latest_ts - timedelta(days=7)
    target_30 = latest_ts - timedelta(days=30)
    lookback_7 = close_series[close_series.index <= target_7]
    lookback_30 = close_series[close_series.index <= target_30]

    past_7 = float(lookback_7.iloc[-1]) if len(lookback_7) > 0 else None
    past_30 = float(lookback_30.iloc[-1]) if len(lookback_30) > 0 else None

    def pct(current: float | None, past: float | None) -> float | None:
        if current is None or past is None or past == 0:
            return None
        return ((current - past) / past) * 100.0

    return {
        "latest_price": latest,
        "change_pct": pct(latest, previous),
        "perf_7d": pct(latest, past_7),
        "perf_30d": pct(latest, past_30),
    }


def _to_float_or_none(value) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _normalize_binance_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized.endswith("-USD"):
        return normalized.replace("-USD", "USDT")
    return normalized


def _fetch_binance_24h_metrics(symbols: list[str]) -> dict[str, dict[str, float | None | str]]:
    """
    Binance 24h ticker endpoint'inden toplu fiyat/degisim alir.
    perf_7d ve perf_30d bu kaynakta olmadigi icin None birakilir.
    """
    if not symbols:
        return {}
    try:
        from binance.client import Client

        client = Client()
        rows = client.get_ticker()
    except Exception:
        logger.exception("Binance 24h ticker error.")
        return {}

    wanted = {_normalize_binance_symbol(symbol) for symbol in symbols}
    out: dict[str, dict[str, float | None | str]] = {}
    for row in rows or []:
        symbol = str(row.get("symbol", "")).upper()
        if symbol not in wanted:
            continue
        latest_price = _to_float_or_none(row.get("lastPrice"))
        if latest_price is None:
            continue
        out[symbol] = {
            "latest_price": latest_price,
            "change_pct": _to_float_or_none(row.get("priceChangePercent")),
            "perf_7d": None,
            "perf_30d": None,
            "source": "binance_24h",
        }
    return out


def _get_market_data_provider():
    global _market_data_provider
    if _market_data_provider is None:
        from api.providers.market_data_provider import CallableMarketDataProvider

        _market_data_provider = CallableMarketDataProvider(
            history_fetcher=_fetch_history_with_fallback,
            yfinance_download_fetcher=_fetch_yfinance_download,
            binance_klines_fetcher=_fetch_binance_klines,
            binance_24h_metrics_fetcher=_fetch_binance_24h_metrics,
            binance_symbol_normalizer=_normalize_binance_symbol,
        )
    return _market_data_provider


@app.get(
    "/market/metrics",
    response_model=dict[str, MarketMetricsItemResponse],
    tags=["Market Data"],
)
@limiter.limit("30/minute")
async def get_market_metrics(
    request: Request,
    key: list[str] | None = Query(
        None,
        description="Market key listesi (ornek: BIST:THYAO, Kripto:BTCUSDT)",
    ),
):
    """
    Scanner icin toplu piyasa metrikleri dondurur.
    Tek cagriyla birden fazla sembolun latest/change/perf7/perf30 degerini verir.
    """
    from application.services.market_data_service import build_market_metrics_payload

    return await build_market_metrics_payload(
        keys=key,
        extract_close_series_from_download=_extract_close_series_from_download,
        calculate_market_metric_payload=_calculate_market_metric_payload,
        provider=_get_market_data_provider(),
        logger=logger,
    )


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


@app.get("/market/analysis", response_model=MarketAnalysisResponse, tags=["AI Analysis"])
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
        logger.exception("Analiz hatasi.")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/candles/{symbol}", response_model=CandlesResponse, tags=["Market Data"])
@limiter.limit("180/minute")
async def get_candles(
    request: Request,
    symbol: str,
    market_type: str = Query("BIST", description="Piyasa türü (BIST/Kripto)"),
    timeframe: str = Query(
        "1d",
        description="Timeframe (15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d, 2d, 3d, 4d, 5d, 6d, 1wk, 2wk, 3wk, 1mo, 2mo, 3mo)",
    ),
    limit: int = Query(500, description="Number of candles (max 2000)"),
):
    from application.services.market_data_service import build_candles_payload

    return await build_candles_payload(
        symbol=symbol,
        market_type=market_type,
        timeframe=timeframe,
        limit=limit,
        provider=_get_market_data_provider(),
        logger=logger,
    )


# ==================== STARTUP/SHUTDOWN ====================


def _run_startup_sequence() -> None:
    """Uygulama baslangicinda gerekli senkron hazirligi yapar."""
    from db_session import init_db
    from infrastructure.persistence.ops_repository import reconcile_active_orders_on_startup

    _RUNTIME_STATE["db_ready"] = False
    try:
        init_db()
        reconcile_summary = reconcile_active_orders_on_startup()
        logger.info(
            "Startup order reconcile completed | checked=%s stale=%s unknown=%s exchange_sync=%s exchange_errors=%s",
            reconcile_summary.get("checked", 0),
            reconcile_summary.get("marked_stale", 0),
            reconcile_summary.get("marked_unknown", 0),
            reconcile_summary.get("exchange_sync_attempted", False),
            reconcile_summary.get("exchange_errors", 0),
        )
        try:
            from market_scanner import restore_scanner_state_from_db

            restore_scanner_state_from_db()
        except Exception as exc:
            logger.warning("Sync scanner state restore at startup failed: %s", exc)
        try:
            from async_scanner import restore_async_scanner_state_from_db

            restore_async_scanner_state_from_db()
        except Exception as exc:
            logger.warning("Async scanner state restore at startup failed: %s", exc)
        _RUNTIME_STATE["db_ready"] = True
        logger.info("Startup DB initialization completed.")
    except Exception:
        logger.exception("Startup DB initialization failed.")
        raise


async def _start_realtime_services() -> None:
    """Real-time servislerini baslatir."""
    await runtime_start_realtime_services(runtime_state=_RUNTIME_STATE, logger=logger)


async def _stop_realtime_services() -> None:
    """Real-time servislerini kapatir."""
    await runtime_stop_realtime_services(runtime_state=_RUNTIME_STATE, logger=logger)
