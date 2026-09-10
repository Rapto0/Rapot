import { useQuery } from '@tanstack/react-query';
import { fetchStats, fetchTrades, transformStats, transformTrade, type TradesParams } from '@/lib/api/client';

export type Trade = ReturnType<typeof transformTrade>;

interface UseTradesOptions {
    status?: 'all' | 'OPEN' | 'CLOSED' | 'CANCELLED';
}

// Fetch persisted trade records; valuation data is not part of this endpoint.
async function fetchTradesData(options: UseTradesOptions = {}): Promise<Trade[]> {
    const { status } = options;

    const params: TradesParams = { limit: 100 };
    if (status && status !== 'all') params.status = status;

    const apiTrades = await fetchTrades(params);
    return apiTrades.map(transformTrade);
}

export function useTrades(options: UseTradesOptions = {}) {
    const { status = 'all' } = options;

    return useQuery({
        queryKey: ['trades', status],
        queryFn: () => fetchTradesData({ status }),
    });
}

export function useOpenTrades() {
    return useTrades({ status: 'OPEN' });
}

export function useClosedTrades() {
    return useTrades({ status: 'CLOSED' });
}

export function useTradeStats() {
    return useQuery({
        queryKey: ['trades', 'stats'],
        queryFn: fetchStats,
        select: (stats) => {
            const normalized = transformStats(stats);
            return {
                total: normalized.totalTrades,
                open: normalized.openPositions,
                closed: normalized.closedPositions,
                totalPnL: normalized.totalPnL,
                winRate: normalized.winRate,
                openPnL: null,
                closedPnL: normalized.totalPnL,
            };
        },
    });
}
