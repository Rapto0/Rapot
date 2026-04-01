import { API_BASE_URL, HEALTH_API_URL, fetchApi } from './core';
import type {
    ApiBotStatus,
    ApiHealth,
    ApiSpecialTagHealth,
    ApiStrategyInspector,
    LogEntry,
    OpsOverviewReadModel,
    ScanHistory,
    ScannerActivityItem,
    SpecialTagHealthParams,
    StrategyInspectorParams,
    SymbolsResponse,
} from './types';

export async function fetchHealth(): Promise<ApiHealth> {
    return fetchApi<ApiHealth>(`${HEALTH_API_URL}/health`);
}

export async function fetchBotStatus(): Promise<ApiBotStatus> {
    return fetchApi<ApiBotStatus>(`${HEALTH_API_URL}/status`);
}

export async function fetchBistSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/bist`);
}

export async function fetchCryptoSymbols(): Promise<SymbolsResponse> {
    return fetchApi<SymbolsResponse>(`${API_BASE_URL}/symbols/crypto`);
}

export async function fetchScanHistory(limit: number = 10): Promise<ScanHistory[]> {
    return fetchApi<ScanHistory[]>(`${API_BASE_URL}/scans?limit=${limit}`);
}

export async function fetchLogs(limit: number = 50): Promise<LogEntry[]> {
    return fetchApi<LogEntry[]>(`${API_BASE_URL}/logs?limit=${limit}`);
}

export async function fetchSpecialTagHealth(
    params: SpecialTagHealthParams = {}
): Promise<ApiSpecialTagHealth> {
    const searchParams = new URLSearchParams();
    if (params.market_type) searchParams.set('market_type', params.market_type);
    if (params.strategy) searchParams.set('strategy', params.strategy);
    if (params.since_hours) searchParams.set('since_hours', params.since_hours.toString());
    if (params.window_seconds !== undefined) {
        searchParams.set('window_seconds', params.window_seconds.toString());
    }

    const query = searchParams.toString();
    return fetchApi<ApiSpecialTagHealth>(
        `${API_BASE_URL}/ops/special-tag-health${query ? `?${query}` : ''}`
    );
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

export async function fetchOpsOverviewReadModel(options?: {
    includeCompatTelemetry?: boolean;
    includeWrapperDetails?: boolean;
}): Promise<OpsOverviewReadModel> {
    const searchParams = new URLSearchParams();
    if (options?.includeCompatTelemetry) searchParams.set('include_compat_telemetry', 'true');
    if (options?.includeWrapperDetails) searchParams.set('include_wrapper_details', 'true');
    const query = searchParams.toString();

    return fetchApi<OpsOverviewReadModel>(
        `${API_BASE_URL}/ops/read-model/overview${query ? `?${query}` : ''}`
    );
}

export async function fetchScannerActivityReadModel(
    limit: number = 100
): Promise<ScannerActivityItem[]> {
    return fetchApi<ScannerActivityItem[]>(
        `${API_BASE_URL}/ops/read-model/scanner-feed?limit=${Math.max(1, limit)}`
    );
}

export async function analyzeSymbol(
    symbol: string,
    marketType: string = 'BIST'
): Promise<{ message: string; status: string }> {
    return fetchApi(`${API_BASE_URL}/analyze/${symbol}?market_type=${marketType}`, {
        method: 'POST',
    });
}
