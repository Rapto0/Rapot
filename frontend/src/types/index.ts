// ===== SIGNAL TYPES =====
export interface Signal {
    id: string;
    symbol: string;
    type: 'HUNTER' | 'COMBO';
    direction: 'LONG' | 'SHORT';
    entry: number;
    target: number;
    stopLoss: number;
    confidence: number;
    timestamp: Date;
    status: 'ACTIVE' | 'HIT_TARGET' | 'HIT_STOP' | 'EXPIRED';
    marketType: 'BIST' | 'Kripto';
    timeframe: string;
    score: string;
    metadata?: {
        timeframe: string;
        indicators: string[];
        notes?: string;
    };
}

// ===== TRADE TYPES =====
export interface Trade {
    id: string;
    signalId?: string;
    symbol: string;
    direction: 'LONG' | 'SHORT';
    entryPrice: number;
    exitPrice?: number;
    currentPrice: number;
    quantity: number;
    leverage: number;
    status: 'OPEN' | 'CLOSED' | 'LIQUIDATED';
    pnl: number;
    pnlPercent: number;
    openedAt: Date;
    closedAt?: Date;
    fees: number;
    marketType: 'BIST' | 'Kripto';
}

// ===== MARKET DATA TYPES =====
export interface MarketData {
    symbol: string;
    price: number;
    change24h: number;
    changePercent24h: number;
    volume24h: number;
    high24h: number;
    low24h: number;
    lastUpdate: Date;
}

export interface MarketTicker {
    symbol: string;
    name: string;
    price: number;
    change: number;
    changePercent: number;
}

export interface CandlestickData {
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

// ===== SYSTEM HEALTH TYPES =====
export interface SystemHealth {
    status: 'HEALTHY' | 'DEGRADED' | 'DOWN';
    uptime: string;
    lastHeartbeat: Date;
    services: ServiceStatus[];
    resources: SystemResources;
}

export interface ServiceStatus {
    name: string;
    status: 'UP' | 'DOWN';
    latency?: number;
}

export interface SystemResources {
    cpu: number;
    memory: number;
    disk: number;
}

export interface BotHealth {
    cpuUsage: number;
    memoryUsage: number;
    uptime: string;
    lastScan: string;
    totalScans: number;
    activeSymbols: number;
    apiStatus: 'healthy' | 'degraded' | 'down';
}

// ===== KPI TYPES =====
export interface KPI {
    totalPnL: number;
    totalPnLPercent: number;
    winRate: number;
    totalTrades: number;
    openPositions: number;
    activeSignals: number;
    avgRiskReward: number;
    maxDrawdown: number;
    sharpeRatio: number;
}

export interface DashboardStats {
    totalPnL: number;
    totalPnLPercent: number;
    winRate: number;
    openPositions: number;
    closedPositions: number;
    totalTrades: number;
    lastScanTime: string;
    totalSignals: number;
    todaySignals: number;
}

// ===== LOG TYPES =====
export interface LogEntry {
    id: number;
    timestamp: string;
    level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
    message: string;
}

// ===== SCAN TYPES =====
export interface ScanResult {
    id: number;
    scanType: 'BIST' | 'Kripto';
    symbolsScanned: number;
    signalsFound: number;
    duration: number;
    createdAt: string;
}

// ===== API RESPONSE TYPES =====
export interface ApiResponse<T> {
    success: boolean;
    data?: T;
    error?: string;
    message?: string;
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}

// ===== WEBSOCKET MESSAGE TYPES =====
export type WebSocketMessageType =
    | 'SIGNAL_UPDATE'
    | 'NEW_SIGNAL'
    | 'TRADE_UPDATE'
    | 'PRICE_UPDATE'
    | 'HEALTH_UPDATE';

export interface WebSocketMessage<T = unknown> {
    type: WebSocketMessageType;
    payload: T;
    timestamp: number;
}

export interface PriceUpdatePayload {
    symbol: string;
    price: number;
    timestamp: number;
}

// ===== FILTER TYPES =====
export interface SignalFilters {
    marketType?: 'BIST' | 'Kripto' | 'all';
    strategy?: 'COMBO' | 'HUNTER' | 'all';
    direction?: 'LONG' | 'SHORT' | 'all';
    status?: Signal['status'] | 'all';
    searchQuery?: string;
}

export interface TradeFilters {
    marketType?: 'BIST' | 'Kripto' | 'all';
    status?: 'OPEN' | 'CLOSED' | 'all';
    direction?: 'LONG' | 'SHORT' | 'all';
}

// ===== SETTINGS TYPES =====
export interface AppSettings {
    telegramChatId: string;
    telegramToken: string;
    binanceApiKey: string;
    binanceSecretKey: string;
    rsiOversold: number;
    rsiOverbought: number;
    macdSignalThreshold: number;
    hunterMinScore: number;
    scanInterval: number;
    notifications: boolean;
}
