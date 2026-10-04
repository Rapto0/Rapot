import { API_BASE_URL, fetchApi } from './core';
import type {
    CandlesResponse,
    EconomicCalendarResponse,
    EconomicCalendarParams,
    GlobalIndexData,
    MarketMetricsItem,
    MarketOverviewResponse,
    TickerData,
} from './types';

export async function fetchCandles(
    symbol: string,
    marketType: string = 'BIST',
    timeframe: string = '1d',
    limit: number = 500,
    options: { signal?: AbortSignal } = {}
): Promise<CandlesResponse> {
    if (marketType === 'BIST') {
        const params = new URLSearchParams({ interval: timeframe, limit: String(limit) });
        return fetchApi(`${API_BASE_URL}/borsapy/candles/${encodeURIComponent(symbol)}?${params}`, options);
    }
    const params = new URLSearchParams({ market_type: marketType, timeframe, limit: String(limit) });
    return fetchApi<CandlesResponse>(
        `${API_BASE_URL}/candles/${encodeURIComponent(symbol)}?${params}`,
        options
    );
}

export async function fetchTicker(): Promise<TickerData[]> {
    return fetchApi<TickerData[]>(`${API_BASE_URL}/borsapy/market/ticker`);
}

export async function fetchMarketOverview(): Promise<MarketOverviewResponse> {
    return fetchApi<MarketOverviewResponse>(`${API_BASE_URL}/borsapy/market/overview`);
}

export async function fetchGlobalIndices(
    symbols: string[],
    options: { signal?: AbortSignal } = {}
): Promise<GlobalIndexData[]> {
    if (symbols.length > 50) throw new Error('Bir sorguda en fazla 50 sembol kullanılabilir.');
    const params = new URLSearchParams();
    symbols.forEach((value) => params.append('symbol', value));
    const query = params.toString();
    return fetchApi<GlobalIndexData[]>(
        `${API_BASE_URL}/borsapy/market/indices${query ? `?${query}` : ''}`,
        options
    );
}

export async function fetchMarketMetrics(keys: string[], options: { signal?: AbortSignal } = {}): Promise<Record<string, MarketMetricsItem>> {
    if (keys.length > 50) throw new Error('Bir sorguda en fazla 50 sembol kullanılabilir.');
    if (keys.some((key) => !key.startsWith('BIST:') && !key.startsWith('Kripto:'))) {
        throw new Error('Desteklenmeyen piyasa.');
    }
    const responses = await Promise.all([
        ['BIST:', 'metrics'], ['Kripto:', 'crypto-metrics'],
    ].map(async ([prefix, endpoint]) => {
        const group = keys.filter((key) => key.startsWith(prefix));
        if (!group.length) return {};
        const searchParams = new URLSearchParams();
        group.forEach((value) => searchParams.append('key', value));
        return fetchApi<Record<string, MarketMetricsItem>>(
            `${API_BASE_URL}/borsapy/market/${endpoint}?${searchParams}`, options
        );
    }));
    return Object.assign({}, ...responses);
}

export async function fetchEconomicCalendar(
    params: EconomicCalendarParams = {}, options: { signal?: AbortSignal } = {}
): Promise<EconomicCalendarResponse> {
    const searchParams = new URLSearchParams();
    if (params.from_date) searchParams.set('from_date', params.from_date);
    if (params.to_date) searchParams.set('to_date', params.to_date);
    if (params.country) searchParams.set('country', params.country);
    if (params.importance) searchParams.set('importance', params.importance);
    const query = searchParams.toString();
    return fetchApi<EconomicCalendarResponse>(
        `${API_BASE_URL}/calendar${query ? `?${query}` : ''}`, options
    );
}
