import { API_BASE_URL, fetchApi } from './core';
import type {
    CandlesResponse,
    EconomicCalendarEvent,
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
    limit: number = 500
): Promise<CandlesResponse> {
    return fetchApi<CandlesResponse>(
        `${API_BASE_URL}/candles/${symbol}?market_type=${marketType}&timeframe=${timeframe}&limit=${limit}`
    );
}

export async function fetchTicker(): Promise<TickerData[]> {
    return fetchApi<TickerData[]>(`${API_BASE_URL}/market/ticker`);
}

export async function fetchMarketOverview(): Promise<MarketOverviewResponse> {
    return fetchApi<MarketOverviewResponse>(`${API_BASE_URL}/market/overview`);
}

export async function fetchGlobalIndices(symbols: string[]): Promise<GlobalIndexData[]> {
    const params = new URLSearchParams();
    symbols.forEach((value) => params.append('symbol', value));
    const query = params.toString();
    return fetchApi<GlobalIndexData[]>(
        `${API_BASE_URL}/market/indices${query ? `?${query}` : ''}`
    );
}

export async function fetchMarketMetrics(keys: string[]): Promise<Record<string, MarketMetricsItem>> {
    const searchParams = new URLSearchParams();
    keys.forEach((value) => searchParams.append('key', value));
    const query = searchParams.toString();
    return fetchApi<Record<string, MarketMetricsItem>>(
        `${API_BASE_URL}/market/metrics${query ? `?${query}` : ''}`
    );
}

export async function fetchEconomicCalendar(
    params: EconomicCalendarParams = {}
): Promise<EconomicCalendarEvent[]> {
    const searchParams = new URLSearchParams();
    if (params.from_date) searchParams.set('from_date', params.from_date);
    if (params.to_date) searchParams.set('to_date', params.to_date);
    const query = searchParams.toString();
    return fetchApi<EconomicCalendarEvent[]>(
        `${API_BASE_URL}/calendar${query ? `?${query}` : ''}`
    );
}
