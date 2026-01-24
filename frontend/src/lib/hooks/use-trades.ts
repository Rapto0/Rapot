import { useQuery } from '@tanstack/react-query';
import { fetchTrades, transformTrade, type TradesParams } from '@/lib/api/client';

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
        queryFn: () => fetchTradesData({}),
        select: (data) => {
            const openTrades = data.filter(t => t.status === 'OPEN');
            const closedTrades = data.filter(t => t.status === 'CLOSED');
            const totalPnL = data.reduce((sum, t) => sum + t.pnl, 0);
            const winningTrades = closedTrades.filter(t => t.pnl > 0).length;
            const winRate = closedTrades.length > 0 ? (winningTrades / closedTrades.length) * 100 : 0;

            return {
                total: data.length,
                open: openTrades.length,
                closed: closedTrades.length,
                totalPnL,
                winRate,
                openPnL: openTrades.reduce((sum, t) => sum + t.pnl, 0),
                closedPnL: closedTrades.reduce((sum, t) => sum + t.pnl, 0),
            };
        },
    });
}
