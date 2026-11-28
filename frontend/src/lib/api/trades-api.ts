import { API_BASE_URL, fetchApi } from './core';
import type { ApiStats, ApiTrade, TradesParams } from './types';

export async function fetchTrades(params: TradesParams = {}, signal?: AbortSignal): Promise<ApiTrade[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.status) searchParams.set('status', params.status);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/trades${query ? `?${query}` : ''}`;

    return fetchApi<ApiTrade[]>(url, { signal });
}

export async function fetchStats(signal?: AbortSignal): Promise<ApiStats> {
    return fetchApi<ApiStats>(`${API_BASE_URL}/stats`, { signal });
}
