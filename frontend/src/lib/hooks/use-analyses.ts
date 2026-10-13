"use client"

import { usePrivateMarket } from './use-private-market';
import { useQuery } from '@tanstack/react-query';
import { fetchAnalyses, fetchAnalysis, transformAnalysis, type AnalysesParams } from '@/lib/api/client';

export interface AIAnalysis {
    id: number;
    signalId: number | null;
    symbol: string;
    marketType: 'BIST' | 'Kripto';
    scenarioName: string;
    signalType: 'AL' | 'SAT' | null;
    analysisText: string;
    technicalData: Record<string, unknown> | null;
    provider: string | null;
    model: string | null;
    backend: string | null;
    promptVersion: string | null;
    sentimentScore: number | null;
    sentimentLabel: string | null;
    confidenceScore: number | null;
    riskLevel: string | null;
    technicalBias: string | null;
    technicalStrength: number | null;
    newsBias: string | null;
    newsStrength: number | null;
    headlineCount: number | null;
    latencyMs: number | null;
    errorCode: string | null;
    createdAt: string;
}

interface UseAnalysesOptions {
    symbol?: string;
    marketType?: 'BIST' | 'Kripto';
    limit?: number;
}

/**
 * Hook to fetch AI analyses list
 */
export function useAnalyses(options: UseAnalysesOptions = {}) {
    const { symbol, marketType, limit = 50 } = options;
    const { allowed, sessionKey } = usePrivateMarket();

    return useQuery({
        queryKey: ['analyses', sessionKey, symbol, marketType, limit],
        enabled: allowed,
        queryFn: async () => {
            const params: AnalysesParams = { limit };
            if (symbol) params.symbol = symbol;
            if (marketType) params.market_type = marketType;

            const apiAnalyses = await fetchAnalyses(params);
            return apiAnalyses.filter(item => item.signal_id === null).map(transformAnalysis);
        },
        staleTime: 60000, // Cache for 1 minute
    });
}

/**
 * Hook to fetch a single AI analysis by ID
 */
export function useAnalysis(id: number) {
    const { allowed, sessionKey } = usePrivateMarket();
    return useQuery({
        queryKey: ['analysis', sessionKey, id],
        queryFn: async () => {
            const apiAnalysis = await fetchAnalysis(id);
            return transformAnalysis(apiAnalysis);
        },
        enabled: allowed && id > 0,
    });
}

/**
 * Hook to fetch recent AI analyses (last N)
 */
export function useRecentAnalyses(limit: number = 5) {
    const { allowed, sessionKey } = usePrivateMarket();
    return useQuery({
        queryKey: ['analyses', 'recent', sessionKey, limit],
        enabled: allowed,
        queryFn: async () => {
            const apiAnalyses = await fetchAnalyses({ limit });
            return apiAnalyses.filter(item => item.signal_id === null).map(transformAnalysis);
        },
        staleTime: 30000,
    });
}
