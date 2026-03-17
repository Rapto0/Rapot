import { useQuery } from '@tanstack/react-query';
import { fetchStats, fetchTrades, transformTrade, type TradesParams } from '@/lib/api/client';

export interface Trade {
    id: number;
    symbol: string;
    marketType: 'BIST' | 'Kripto';
    direction: 'BUY' | 'SELL';
    entryPrice: number;
    currentPrice: number;
    quantity: number;
    pnl: number;
    pnlPercent: number;
    status: 'OPEN' | 'CLOSED' | 'CANCELLED';
    createdAt: string;
    closedAt?: string;
}

interface UseTradesOptions {
    status?: 'all' | 'OPEN' | 'CLOSED';
}

// Fetch trades from API or fallback to mock data
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
            return {
                total: stats.total_trades,
                open: stats.open_trades,
                closed: Math.max(0, stats.total_trades - stats.open_trades),
                totalPnL: stats.total_pnl,
                winRate: stats.win_rate,
                openPnL: 0,
                closedPnL: stats.total_pnl,
            };
        },
    });
}
