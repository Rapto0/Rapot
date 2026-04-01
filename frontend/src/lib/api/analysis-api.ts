import { API_BASE_URL, fetchApi } from './core';
import type {
    AIAnalysisParams,
    AnalysesParams,
    ApiAIAnalysis,
    StructuredAIAnalysisResponse,
} from './types';

export async function fetchAnalyses(params: AnalysesParams = {}): Promise<ApiAIAnalysis[]> {
    const searchParams = new URLSearchParams();
    if (params.symbol) searchParams.set('symbol', params.symbol);
    if (params.market_type) searchParams.set('market_type', params.market_type);
    if (params.limit) searchParams.set('limit', params.limit.toString());

    const query = searchParams.toString();
    const url = `${API_BASE_URL}/analyses${query ? `?${query}` : ''}`;

    return fetchApi<ApiAIAnalysis[]>(url);
}

export async function fetchAnalysis(id: number): Promise<ApiAIAnalysis> {
    return fetchApi<ApiAIAnalysis>(`${API_BASE_URL}/analyses/${id}`);
}

export async function fetchSignalAnalysis(signalId: number): Promise<ApiAIAnalysis | null> {
    try {
        return await fetchApi<ApiAIAnalysis>(`${API_BASE_URL}/signals/${signalId}/analysis`);
    } catch {
        return null;
    }
}

export async function fetchAIAnalysis(params: AIAnalysisParams): Promise<StructuredAIAnalysisResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('symbol', params.symbol);
    if (params.market_type && params.market_type !== 'AUTO') {
        searchParams.set('market_type', params.market_type);
    }
    if (params.strategy) {
        searchParams.set('strategy', params.strategy);
    }
    if (params.timeframe && params.timeframe !== 'ALL') {
        searchParams.set('timeframe', params.timeframe);
    }

    return fetchApi<StructuredAIAnalysisResponse>(
        `${API_BASE_URL}/market/analysis?${searchParams.toString()}`
    );
}
