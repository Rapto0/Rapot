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

export function toTradeDirection(value: string | null | undefined): 'BUY' | 'SELL' | null {
    return VALID_DIRECTIONS.has(value as 'BUY' | 'SELL') ? (value as 'BUY' | 'SELL') : null;
}

export function toTradeStatus(value: string | null | undefined): 'OPEN' | 'CLOSED' | 'CANCELLED' | null {
    return VALID_TRADE_STATUSES.has(value as 'OPEN' | 'CLOSED' | 'CANCELLED')
        ? (value as 'OPEN' | 'CLOSED' | 'CANCELLED')
        : null;
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

function finiteNumber(value: unknown): number | null {
    return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function count(value: unknown): number | null {
    const number = finiteNumber(value);
    return number !== null && Number.isInteger(number) && number >= 0 ? number : null;
}

function timestamp(value: string | null | undefined): string | null {
    return value && Number.isFinite(Date.parse(value)) ? value : null;
}

export function transformTrade(apiTrade: ApiTrade) {
    const rawEntryPrice = finiteNumber(apiTrade.price);
    const entryPrice = rawEntryPrice !== null && rawEntryPrice > 0 ? rawEntryPrice : null;
    const rawQuantity = finiteNumber(apiTrade.quantity);
    const quantity = rawQuantity !== null && rawQuantity >= 0 ? rawQuantity : null;
    const status = toTradeStatus(apiTrade.status);
    // The API stores realized PnL on close; OPEN rows have an unmeasured default zero.
    const pnl = status === 'CLOSED' ? finiteNumber(apiTrade.pnl) : null;
    const notional = entryPrice !== null && quantity !== null ? entryPrice * quantity : null;
    const pnlPercent = pnl !== null && notional !== null && Number.isFinite(notional) && notional > 0
        ? finiteNumber((pnl / notional) * 100)
        : null;
    return {
        id: apiTrade.id,
        symbol: apiTrade.symbol,
        marketType: toMarketType(apiTrade.market_type),
        direction: toTradeDirection(apiTrade.direction),
        entryPrice,
        // /trades exposes no current quote or valuation timestamp.
        currentPrice: null,
        quantity,
        pnl,
        pnlPercent,
        status,
        createdAt: timestamp(apiTrade.created_at),
    };
}

export function transformStats(apiStats: ApiStats) {
    return {
        totalPnL: finiteNumber(apiStats.total_pnl),
        totalPnLPercent: null,
        winRate: finiteNumber(apiStats.win_rate),
        openPositions: count(apiStats.open_trades),
        closedPositions: count(apiStats.closed_trades),
        totalTrades: count(apiStats.total_trades),
        lastScanTime: null,
        totalSignals: count(apiStats.total_signals),
        todaySignals: null,
    };
}

export function transformOpsOverviewReadModel(overview: OpsOverviewReadModel) {
    return {
        totalPnL: finiteNumber(overview.total_pnl),
        totalPnLPercent: null,
        winRate: null,
        openPositions: count(overview.open_trades),
        closedPositions: null,
        totalTrades: count(overview.total_trades),
        lastScanTime: timestamp(overview.last_scan_at),
        totalSignals: count(overview.total_signals),
        todaySignals: null,
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
