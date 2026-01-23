/**
 * Rapot API Client
 * Connects to FastAPI backend on port 8000 and Flask health API on port 5000
 */

// API Base URLs
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const HEALTH_API_URL = process.env.NEXT_PUBLIC_HEALTH_API_URL || 'http://localhost:5000';

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
    limit?: number;
}

export async function fetchSignals(params: SignalsParams = {}): Promise<ApiSignal[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.strategy) searchParams.set('strategy', params.strategy);
    if (params.signal_type) searchParams.set('signal_type', params.signal_type);
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

// ==================== ANALYSIS API ====================

export async function analyzeSymbol(symbol: string, marketType: string = 'BIST'): Promise<{ message: string; status: string }> {
    return fetchApi(`${API_BASE_URL}/analyze/${symbol}?market_type=${marketType}`, {
        method: 'POST',
    });
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
