/**
 * Rapot API Client
 * Connects to FastAPI backend on port 8000 and Flask health API on port 5000
 */

// API Base URLs
// API Base URLs
// When running in Nginx (production), /api requests are proxied to localhost:8000
// When running locally, we need to ensure requests go to port 8000
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';
const HEALTH_API_URL = process.env.NEXT_PUBLIC_HEALTH_API_URL || '/health-api';

// ==================== TYPES ====================

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

// ==================== API CLIENT ====================

class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
        this.name = 'ApiError';
    }
}

async function fetchApi<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        throw new ApiError(
            `API error: ${response.statusText}`,
            response.status
        );
    }

    return response.json();
}

// ==================== SIGNALS API ====================

export interface SignalsParams {
    symbol?: string;
    strategy?: 'COMBO' | 'HUNTER';
    signal_type?: 'AL' | 'SAT';
    market_type?: 'BIST' | 'Kripto';
    limit?: number;
}

export async function fetchSignals(params: SignalsParams = {}): Promise<ApiSignal[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.strategy) searchParams.set('strategy', params.strategy);
    if (params.signal_type) searchParams.set('signal_type', params.signal_type);
    if (params.market_type) searchParams.set('market_type', params.market_type);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/signals${query ? `?${query}` : ''}`;

    return fetchApi<ApiSignal[]>(url);
}

export async function fetchSignal(id: number): Promise<ApiSignal> {
    return fetchApi<ApiSignal>(`${API_BASE_URL}/signals/${id}`);
}

// ==================== TRADES API ====================

export interface TradesParams {
    symbol?: string;
    status?: 'OPEN' | 'CLOSED';
    limit?: number;
}

export async function fetchTrades(params: TradesParams = {}): Promise<ApiTrade[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.status) searchParams.set('status', params.status);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/trades${query ? `?${query}` : ''}`;

    return fetchApi<ApiTrade[]>(url);
}

// ==================== STATS API ====================

export async function fetchStats(): Promise<ApiStats> {
    return fetchApi<ApiStats>(`${API_BASE_URL}/stats`);
}

// ==================== HEALTH API ====================

export async function fetchHealth(): Promise<ApiHealth> {
    return fetchApi<ApiHealth>(`${HEALTH_API_URL}/health`);
}

export async function fetchBotStatus(): Promise<ApiBotStatus> {
    return fetchApi<ApiBotStatus>(`${HEALTH_API_URL}/status`);
}

// ==================== SYMBOLS API ====================

export interface SymbolsResponse {
    count: number;
    symbols: string[];
}

export async function fetchBistSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/bist`);
}

export async function fetchCryptoSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/crypto`);
}

// ==================== CANDLE API ====================

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

export async function fetchCandles(
    symbol: string,
    marketType: string = 'BIST',
    timeframe: string = '1d',
    limit: number = 500
): Promise<CandlesResponse> {
    return fetchApi<CandlesResponse>(
        `${API_BASE_URL}/candles/${symbol}?market_type=${marketType}&timeframe=${timeframe}&limit=${limit}`
    );
}

// ==================== MARKET OVERVIEW API ====================

export interface TickerData {
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
}

export async function fetchTicker(): Promise<TickerData[]> {
    return fetchApi<TickerData[]>(`${API_BASE_URL}/market/ticker`);
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

export async function fetchMarketOverview(): Promise<MarketOverviewResponse> {
    return fetchApi<MarketOverviewResponse>(`${API_BASE_URL}/market/overview`);
}

export interface GlobalIndexData {
    symbol: string;
    regularMarketPrice: number;
    regularMarketChangePercent: number;
    shortName?: string;
}

export async function fetchGlobalIndices(symbols: string[]): Promise<GlobalIndexData[]> {
    const params = new URLSearchParams();
    symbols.forEach((value) => params.append("symbol", value));
    const query = params.toString();
    return fetchApi<GlobalIndexData[]>(
        `${API_BASE_URL}/market/indices${query ? `?${query}` : ""}`
    );
}

// ==================== SYSTEM API ====================

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

export async function fetchScanHistory(limit: number = 10): Promise<ScanHistory[]> {
    return fetchApi<ScanHistory[]>(`${API_BASE_URL}/scans?limit=${limit}`);
}

export interface LogEntry {
    timestamp: string;
    level: string;
    message: string;
}

export async function fetchLogs(limit: number = 50): Promise<LogEntry[]> {
    return fetchApi<LogEntry[]>(`${API_BASE_URL}/logs?limit=${limit}`);
}

// ==================== ANALYSIS API ====================

export async function analyzeSymbol(symbol: string, marketType: string = 'BIST'): Promise<{ message: string; status: string }> {
    return fetchApi(`${API_BASE_URL}/analyze/${symbol}?market_type=${marketType}`, {
        method: 'POST',
    });
}

// ==================== AI ANALYSIS API ====================

export interface AnalysesParams {
    symbol?: string;
    market_type?: string;
    limit?: number;
}

export async function fetchAnalyses(params: AnalysesParams = {}): Promise<ApiAIAnalysis[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.market_type) searchParams.set('market_type', params.market_type);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/analyses${query ? `?${query}` : ''}`;

    return fetchApi<ApiAIAnalysis[]>(url);
}

export async function fetchAnalysis(id: number): Promise<ApiAIAnalysis> {
    return fetchApi<ApiAIAnalysis>(`${API_BASE_URL}/analyses/${id}`);
}

export async function fetchSignalAnalysis(signalId: number): Promise<ApiAIAnalysis | null> {
    try {
        return await fetchApi<ApiAIAnalysis>(`${API_BASE_URL}/signals/${signalId}/analysis`);
    } catch {
        return null;
    }
}

export interface StructuredAIAnalysisResponse {
    symbol: string;
    market_type: string;
    score: string;
    summary: string;
    structured_analysis: any; // Using any for flexibility now, can type it later
    updated_at: string;
}

export async function fetchAIAnalysis(symbol: string, marketType: string = 'BIST'): Promise<StructuredAIAnalysisResponse> {
    return fetchApi<StructuredAIAnalysisResponse>(
        `${API_BASE_URL}/market/analysis?symbol=${symbol}&market_type=${marketType}`
    );
}

// Transform AI Analysis to frontend format
export function transformAnalysis(apiAnalysis: ApiAIAnalysis) {
    return {
        id: apiAnalysis.id,
        signalId: apiAnalysis.signal_id,
        symbol: apiAnalysis.symbol,
        marketType: apiAnalysis.market_type as 'BIST' | 'Kripto',
        scenarioName: apiAnalysis.scenario_name || '',
        signalType: apiAnalysis.signal_type as 'AL' | 'SAT' | null,
        analysisText: apiAnalysis.analysis_text,
        technicalData: apiAnalysis.technical_data ? JSON.parse(apiAnalysis.technical_data) : null,
        createdAt: apiAnalysis.created_at || new Date().toISOString(),
    };
}

// ==================== TRANSFORM HELPERS ====================

// Transform API signal to frontend format
export function transformSignal(apiSignal: ApiSignal) {
    return {
        id: apiSignal.id,
        symbol: apiSignal.symbol,
        marketType: apiSignal.market_type as 'BIST' | 'Kripto',
        strategy: apiSignal.strategy as 'COMBO' | 'HUNTER',
        signalType: apiSignal.signal_type as 'AL' | 'SAT',
        timeframe: apiSignal.timeframe,
        score: apiSignal.score || '',
        price: apiSignal.price,
        createdAt: apiSignal.created_at || new Date().toISOString(),
    };
}

// Transform API trade to frontend format
export function transformTrade(apiTrade: ApiTrade) {
    return {
        id: apiTrade.id,
        symbol: apiTrade.symbol,
        marketType: apiTrade.market_type as 'BIST' | 'Kripto',
        direction: apiTrade.direction as 'BUY' | 'SELL',
        entryPrice: apiTrade.price,
        currentPrice: apiTrade.price, // Would need real-time data
        quantity: apiTrade.quantity,
        pnl: apiTrade.pnl,
        pnlPercent: apiTrade.price > 0 ? (apiTrade.pnl / apiTrade.price) * 100 : 0,
        status: apiTrade.status as 'OPEN' | 'CLOSED',
        createdAt: apiTrade.created_at || new Date().toISOString(),
    };
}

// Transform API stats to frontend KPI format
export function transformStats(apiStats: ApiStats) {
    return {
        totalPnL: apiStats.total_pnl,
        totalPnLPercent: 0, // Need historical data for this
        winRate: apiStats.win_rate,
        openPositions: apiStats.open_trades,
        closedPositions: apiStats.total_trades - apiStats.open_trades,
        totalTrades: apiStats.total_trades,
        lastScanTime: new Date().toISOString(),
        totalSignals: apiStats.total_signals,
        todaySignals: 0, // Would need specific query
    };
}
