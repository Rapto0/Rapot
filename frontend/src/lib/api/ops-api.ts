import { API_BASE_URL, fetchApi } from './core';
import type {
    ApiHealth,
    ApiStrategyInspector,
    LogEntry,
    StrategyInspectorParams,
    SymbolsResponse,
} from './types';

export async function fetchHealth(signal?: AbortSignal): Promise<ApiHealth> {
    return fetchApi<ApiHealth>(`${API_BASE_URL}/health`, { signal });
}

export async function fetchBistSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/bist`);
}

export async function fetchCryptoSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/crypto`);
}

export async function fetchLogs(limit: number = 50): Promise<LogEntry[]> {
    return fetchApi<LogEntry[]>(`${API_BASE_URL}/logs?limit=${limit}`);
}

export async function fetchStrategyInspector(
    params: StrategyInspectorParams
): Promise<ApiStrategyInspector> {
    const searchParams = new URLSearchParams();
    searchParams.set('symbol', params.symbol);
    searchParams.set('strategy', params.strategy);
    if (params.market_type && params.market_type !== 'AUTO') {
        searchParams.set('market_type', params.market_type);
    }

    return fetchApi<ApiStrategyInspector>(
        `${API_BASE_URL}/ops/strategy-inspector?${searchParams.toString()}`
    );
}
