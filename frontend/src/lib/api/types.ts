export interface ApiTrade {
    id: number;
    symbol: string;
    market_type: string;
    direction: string;
    price: number | null;
    quantity: number | null;
    pnl: number | null;
    status: string;
    created_at: string | null;
}

export interface ApiStats {
    total_trades: number;
    open_trades: number;
    closed_trades?: number | null;
    total_pnl: number;
    win_rate: number;
}

export interface ApiAIAnalysis {
    id: number;
    signal_id: number | null;
    symbol: string;
    market_type: string;
    scenario_name: string | null;
    signal_type: string | null;
    analysis_text: string;
    technical_data: string | null;
    provider?: string | null;
    model?: string | null;
    backend?: string | null;
    prompt_version?: string | null;
    sentiment_score?: number | null;
    sentiment_label?: string | null;
    confidence_score?: number | null;
    risk_level?: string | null;
    technical_bias?: string | null;
    technical_strength?: number | null;
    news_bias?: string | null;
    news_strength?: number | null;
    headline_count?: number | null;
    latency_ms?: number | null;
    error_code?: string | null;
    created_at: string | null;
}

export interface ApiHealth {
    status: string;
    database: string;
    realtime: string;
    version: string;
    uptime_seconds: number;
    uptime_human: string;
    timestamp: string;
}

export interface ApiStrategyInspectorTimeframe {
    code: string;
    label: string;
    available: boolean;
    signal_status: 'AL' | 'SAT' | 'NOTR' | 'YOK' | string;
    reason: string | null;
    price: number | string | null;
    date: string | null;
    active_indicators: string | null;
    primary_score: string | null;
    primary_score_label: string;
    secondary_score: string | null;
    secondary_score_label: string;
    raw_score: string | null;
    indicators: Record<string, number | string | null>;
}

export interface ApiStrategyInspector {
    symbol: string;
    market_type: 'BIST' | 'Kripto' | string;
    strategy: 'COMBO' | 'HUNTER' | string;
    indicator_order: string[];
    indicator_labels: Record<string, string>;
    generated_at: string;
    timeframes: ApiStrategyInspectorTimeframe[];
}

export interface ApiStructuredAnalysis {
    sentiment_score: number;
    sentiment_label: string;
    confidence_score: number;
    risk_level: string;
    summary: string[];
    explanation: string;
    technical_view: {
        bias: string;
        strength: number;
        conflicts: string[];
    };
    news_view: {
        bias: string;
        strength: number;
        headline_count: number;
    };
    key_levels: {
        support: string[];
        resistance: string[];
    };
    provider?: string | null;
    model?: string | null;
    backend?: string | null;
    prompt_version?: string | null;
    error?: string | null;
    error_code?: string | null;
}

export interface TradesParams {
    symbol?: string;
    status?: 'OPEN' | 'CLOSED' | 'CANCELLED';
    limit?: number;
}

export interface SymbolsResponse {
    count: number;
    symbols: string[];
}

export interface Candle {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number | null;
}

export interface VolumeQuality {
    state: 'verified' | 'unavailable' | 'unverified';
    verified: boolean;
    unavailable_rows: number | null;
    message: string;
}

export interface MarketSourceMetadata {
    source?: string | null;
    provider_time?: string | null;
    received_at?: string | null;
    state?: 'ok' | 'waiting' | 'stale' | 'error' | 'auth_required' | 'unsupported';
    realtime_verified?: boolean;
    message?: string | null;
}

export interface CandlesResponse extends MarketSourceMetadata {
    symbol: string;
    market_type: string;
    timeframe: string;
    source: string;
    count: number;
    candles: Candle[];
    volume_quality?: VolumeQuality;
}

export interface TickerData extends MarketSourceMetadata {
    symbol: string;
    name: string;
    price: number | null;
    change: number | null;
    changePercent: number | null;
}

export interface MarketHistoryPoint {
    time: string;
    value: number;
}

export interface MarketData extends MarketSourceMetadata {
    currentValue: number | null;
    change: number | null;
    history: MarketHistoryPoint[];
}

export interface MarketOverviewResponse {
    bist: MarketData;
    crypto: MarketData;
}

export interface GlobalIndexData extends MarketSourceMetadata {
    symbol: string;
    regularMarketPrice: number | null;
    regularMarketChangePercent: number | null;
    shortName?: string;
}

export interface MarketMetricsItem extends MarketSourceMetadata {
    latest_price: number | null;
    change_pct: number | null;
    perf_7d: number | null;
    perf_30d: number | null;
    source?: string | null;
}

export interface EconomicCalendarEvent {
    id: string;
    date: string;
    source_time?: string | null;
    timestamp?: null;
    country: string | null;
    event: string | null;
    impact: string | null;
    time: string | null;
    actual: number | string | null;
    estimate: number | string | null;
    previous: number | string | null;
    unit: string | null;
    currency: string | null;
}

export interface EconomicCalendarParams {
    from_date?: string;
    to_date?: string;
    country?: string;
    importance?: 'all' | 'low' | 'mid' | 'high';
}

export interface EconomicCalendarResponse {
    events: EconomicCalendarEvent[];
    meta: {
        source: string; state: 'ok' | 'empty' | 'stale'; fetched_at: string;
        source_timezone: null; display_timezone: string; warnings: string[];
        from_date: string; to_date: string; countries: string[];
        cache_hit: boolean; provider_cache_seconds: number;
    };
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
}

export interface StrategyInspectorParams {
    symbol: string;
    strategy: 'COMBO' | 'HUNTER';
    market_type?: 'AUTO' | 'BIST' | 'Kripto';
}

export interface AnalysesParams {
    symbol?: string;
    market_type?: string;
    limit?: number;
}

export interface StructuredAIAnalysisResponse {
    symbol: string;
    market_type: string;
    strategy: string;
    timeframe: string;
    score: string;
    summary: string;
    structured_analysis: ApiStructuredAnalysis;
    inspection: ApiStrategyInspector;
    updated_at: string;
}

export interface AIAnalysisParams {
    symbol: string;
    market_type?: 'BIST' | 'Kripto' | 'AUTO';
    strategy?: 'COMBO' | 'HUNTER';
    timeframe?: 'ALL' | '1D' | '1W' | '2W' | '3W' | '1M';
}
