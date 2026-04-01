export interface ApiSignal {
    id: number;
    symbol: string;
    market_type: string;
    strategy: string;
    signal_type: string;
    timeframe: string;
    score: string | null;
    price: number;
    created_at: string | null;
    special_tag?: string | null;
    details?: unknown;
}

export interface ApiTrade {
    id: number;
    symbol: string;
    market_type: string;
    direction: string;
    price: number;
    quantity: number;
    pnl: number;
    status: string;
    created_at: string | null;
}

export interface ApiStats {
    total_signals: number;
    total_trades: number;
    open_trades: number;
    total_pnl: number;
    win_rate: number;
    scan_count: number;
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
    uptime_seconds: number;
    uptime_human: string;
    timestamp: string;
}

export interface ApiBotStatus {
    bot: {
        is_running: boolean;
        is_scanning: boolean;
        uptime_seconds: number;
        uptime_human: string;
        started_at: string;
    };
    scanning: {
        last_scan_time: string | null;
        scan_count: number;
        signal_count: number;
    };
    errors: {
        error_count: number;
        last_error: string | null;
    };
    timestamp: string;
}

export interface ApiSpecialTagHealthRow {
    tag: 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT';
    strategy: 'COMBO' | 'HUNTER';
    signal_type: 'AL' | 'SAT';
    target_timeframe: string;
    candidates: number;
    tagged: number;
    missing: number;
}

export interface ApiSpecialTagHealth {
    status: 'ok' | 'alert';
    stored_state: string | null;
    market_type: 'BIST' | 'Kripto' | 'ALL' | null;
    strategy: 'COMBO' | 'HUNTER' | null;
    checked_window_hours: number;
    checked_window_seconds: number;
    missing_total: number;
    last_checked_at: string | null;
    summary: string | null;
    rows: ApiSpecialTagHealthRow[];
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

export interface SignalsParams {
    symbol?: string;
    strategy?: 'COMBO' | 'HUNTER';
    signal_type?: 'AL' | 'SAT';
    market_type?: 'BIST' | 'Kripto';
    special_tag?: 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT';
    limit?: number;
}

export interface TradesParams {
    symbol?: string;
    status?: 'OPEN' | 'CLOSED';
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
    volume: number;
}

export interface CandlesResponse {
    symbol: string;
    market_type: string;
    timeframe: string;
    source: string;
    count: number;
    candles: Candle[];
}

export interface TickerData {
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
}

export interface MarketHistoryPoint {
    time: string;
    value: number;
}

export interface MarketData {
    currentValue: number;
    change: number;
    history: MarketHistoryPoint[];
}

export interface MarketOverviewResponse {
    bist: MarketData;
    crypto: MarketData;
}

export interface GlobalIndexData {
    symbol: string;
    regularMarketPrice: number;
    regularMarketChangePercent: number;
    shortName?: string;
}

export interface MarketMetricsItem {
    latest_price: number | null;
    change_pct: number | null;
    perf_7d: number | null;
    perf_30d: number | null;
    source?: string | null;
}

export interface EconomicCalendarEvent {
    country: string | null;
    event: string | null;
    impact: string | null;
    time: string | null;
    actual: number | null;
    estimate: number | null;
    previous: number | null;
    unit: string | null;
    currency: string | null;
}

export interface EconomicCalendarParams {
    from_date?: string;
    to_date?: string;
}

export interface ScanHistory {
    id: number;
    scan_type: string;
    mode: string;
    symbols_scanned: number;
    signals_found: number;
    errors_count: number;
    duration_seconds: number;
    created_at: string;
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
}

export interface SpecialTagHealthParams {
    market_type?: 'BIST' | 'Kripto' | 'ALL';
    strategy?: 'COMBO' | 'HUNTER';
    since_hours?: number;
    window_seconds?: number;
}

export interface StrategyInspectorParams {
    symbol: string;
    strategy: 'COMBO' | 'HUNTER';
    market_type?: 'AUTO' | 'BIST' | 'Kripto';
}

export interface OpsOverviewReadModel {
    total_signals: number;
    total_trades: number;
    open_trades: number;
    total_scans: number;
    total_pnl: number;
    last_signal_at: string | null;
    last_trade_at: string | null;
    last_scan_at: string | null;
    compatibility_wrappers?: OpsCompatibilityWrapperTelemetry | null;
}

export interface OpsCompatibilityWrapperItem {
    wrapper_module: string;
    canonical_module: string;
    usage_count: number;
    planned_removal: string;
    first_seen_at: string | null;
    last_seen_at: string | null;
}

export interface OpsCompatibilityWrapperTelemetry {
    total_wrappers: number;
    active_wrappers: number;
    total_import_events: number;
    planned_removal_buckets: Record<string, number>;
    details_requested: boolean;
    details_included: boolean;
    details_hidden_reason?: string | null;
    wrappers?: OpsCompatibilityWrapperItem[] | null;
}

export interface ScannerActivityItem {
    item_type: string;
    item_id: string;
    symbol: string | null;
    market_type: string | null;
    strategy: string | null;
    action: string | null;
    timeframe: string | null;
    status: string | null;
    numeric_value: number | null;
    created_at: string | null;
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
