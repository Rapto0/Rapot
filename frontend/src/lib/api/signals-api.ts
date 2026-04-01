import { API_BASE_URL, fetchApi } from './core';
import type { ApiSignal, ApiStats, ApiTrade, SignalsParams, TradesParams } from './types';

export async function fetchSignals(params: SignalsParams = {}): Promise<ApiSignal[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.strategy) searchParams.set('strategy', params.strategy);
    if (params.signal_type) searchParams.set('signal_type', params.signal_type);
    if (params.market_type) searchParams.set('market_type', params.market_type);
    if (params.special_tag) searchParams.set('special_tag', params.special_tag);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/signals${query ? `?${query}` : ''}`;

    return fetchApi<ApiSignal[]>(url);
}

export async function fetchSignal(id: number): Promise<ApiSignal> {
    return fetchApi<ApiSignal>(`${API_BASE_URL}/signals/${id}`);
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

export async function fetchStats(): Promise<ApiStats> {
    return fetchApi<ApiStats>(`${API_BASE_URL}/stats`);
}
