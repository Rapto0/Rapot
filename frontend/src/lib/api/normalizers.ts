import type { ApiAIAnalysis, ApiSignal, ApiStats, ApiTrade } from './types';
import type { OpsOverviewReadModel } from './types';

const VALID_MARKET_TYPES = new Set(['BIST', 'Kripto'] as const);
const VALID_STRATEGIES = new Set(['COMBO', 'HUNTER'] as const);
const VALID_SIGNAL_TYPES = new Set(['AL', 'SAT'] as const);
const VALID_SPECIAL_TAGS = new Set(['BELES', 'COK_UCUZ', 'PAHALI', 'FAHIS_FIYAT'] as const);
const VALID_DIRECTIONS = new Set(['BUY', 'SELL'] as const);
const VALID_TRADE_STATUSES = new Set(['OPEN', 'CLOSED', 'CANCELLED'] as const);

export function toMarketType(value: string | null | undefined): 'BIST' | 'Kripto' {
    return VALID_MARKET_TYPES.has(value as 'BIST' | 'Kripto') ? (value as 'BIST' | 'Kripto') : 'BIST';
}

export function toStrategy(value: string | null | undefined): 'COMBO' | 'HUNTER' {
    return VALID_STRATEGIES.has(value as 'COMBO' | 'HUNTER') ? (value as 'COMBO' | 'HUNTER') : 'COMBO';
}

export function toSignalType(value: string | null | undefined): 'AL' | 'SAT' {
    return VALID_SIGNAL_TYPES.has(value as 'AL' | 'SAT') ? (value as 'AL' | 'SAT') : 'AL';
}

export function toNullableSignalType(value: string | null | undefined): 'AL' | 'SAT' | null {
    if (!value) return null;
    return VALID_SIGNAL_TYPES.has(value as 'AL' | 'SAT') ? (value as 'AL' | 'SAT') : null;
}

export function toSpecialTag(
    value: string | null | undefined
): 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT' | null {
    if (!value) return null;
    return VALID_SPECIAL_TAGS.has(value as 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT')
        ? (value as 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT')
        : null;
}

export function toTradeDirection(value: string | null | undefined): 'BUY' | 'SELL' {
    return VALID_DIRECTIONS.has(value as 'BUY' | 'SELL') ? (value as 'BUY' | 'SELL') : 'BUY';
}

export function toTradeStatus(value: string | null | undefined): 'OPEN' | 'CLOSED' | 'CANCELLED' {
    return VALID_TRADE_STATUSES.has(value as 'OPEN' | 'CLOSED' | 'CANCELLED')
        ? (value as 'OPEN' | 'CLOSED' | 'CANCELLED')
        : 'OPEN';
}

export function safeParseTechnicalData(value: string | null): Record<string, unknown> | null {
    if (!value) return null;
    try {
        const parsed = JSON.parse(value);
        return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
            ? (parsed as Record<string, unknown>)
            : null;
    } catch {
        return null;
    }
}

export function transformSignal(apiSignal: ApiSignal) {
    return {
        id: apiSignal.id,
        symbol: apiSignal.symbol,
        marketType: toMarketType(apiSignal.market_type),
        strategy: toStrategy(apiSignal.strategy),
        signalType: toSignalType(apiSignal.signal_type),
        timeframe: apiSignal.timeframe,
        score: apiSignal.score || '',
        price: apiSignal.price,
        createdAt: apiSignal.created_at || new Date().toISOString(),
        specialTag: toSpecialTag(apiSignal.special_tag),
    };
}

export function transformTrade(apiTrade: ApiTrade) {
    const entryPrice = Number.isFinite(apiTrade.price) ? apiTrade.price : 0;
    const pnl = Number.isFinite(apiTrade.pnl) ? apiTrade.pnl : 0;
    return {
        id: apiTrade.id,
        symbol: apiTrade.symbol,
        marketType: toMarketType(apiTrade.market_type),
        direction: toTradeDirection(apiTrade.direction),
        entryPrice,
        currentPrice: entryPrice,
        quantity: apiTrade.quantity,
        pnl,
        pnlPercent: entryPrice > 0 ? (pnl / entryPrice) * 100 : 0,
        status: toTradeStatus(apiTrade.status),
        createdAt: apiTrade.created_at || new Date().toISOString(),
    };
}

export function transformStats(apiStats: ApiStats) {
    return {
        totalPnL: apiStats.total_pnl,
        totalPnLPercent: 0,
        winRate: apiStats.win_rate,
        openPositions: apiStats.open_trades,
        closedPositions: apiStats.total_trades - apiStats.open_trades,
        totalTrades: apiStats.total_trades,
        lastScanTime: new Date().toISOString(),
        totalSignals: apiStats.total_signals,
        todaySignals: 0,
    };
}

export function transformOpsOverviewReadModel(overview: OpsOverviewReadModel) {
    const closedTrades = Math.max(0, overview.total_trades - overview.open_trades);
    return {
        totalPnL: overview.total_pnl,
        totalPnLPercent: 0,
        winRate: 0,
        openPositions: overview.open_trades,
        closedPositions: closedTrades,
        totalTrades: overview.total_trades,
        lastScanTime: overview.last_scan_at || new Date().toISOString(),
        totalSignals: overview.total_signals,
        todaySignals: 0,
    };
}

export function transformAnalysis(apiAnalysis: ApiAIAnalysis) {
    return {
        id: apiAnalysis.id,
        signalId: apiAnalysis.signal_id,
        symbol: apiAnalysis.symbol,
        marketType: toMarketType(apiAnalysis.market_type),
        scenarioName: apiAnalysis.scenario_name || '',
        signalType: toNullableSignalType(apiAnalysis.signal_type),
        analysisText: apiAnalysis.analysis_text,
        technicalData: safeParseTechnicalData(apiAnalysis.technical_data),
        provider: apiAnalysis.provider ?? null,
        model: apiAnalysis.model ?? null,
        backend: apiAnalysis.backend ?? null,
        promptVersion: apiAnalysis.prompt_version ?? null,
        sentimentScore: apiAnalysis.sentiment_score ?? null,
        sentimentLabel: apiAnalysis.sentiment_label ?? null,
        confidenceScore: apiAnalysis.confidence_score ?? null,
        riskLevel: apiAnalysis.risk_level ?? null,
        technicalBias: apiAnalysis.technical_bias ?? null,
        technicalStrength: apiAnalysis.technical_strength ?? null,
        newsBias: apiAnalysis.news_bias ?? null,
        newsStrength: apiAnalysis.news_strength ?? null,
        headlineCount: apiAnalysis.headline_count ?? null,
        latencyMs: apiAnalysis.latency_ms ?? null,
        errorCode: apiAnalysis.error_code ?? null,
        createdAt: apiAnalysis.created_at || new Date().toISOString(),
    };
}
