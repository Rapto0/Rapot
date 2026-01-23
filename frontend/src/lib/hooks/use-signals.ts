import { useQuery } from '@tanstack/react-query';
import { fetchSignals, transformSignal, type SignalsParams } from '@/lib/api/client';
import { mockSignals } from '@/lib/mock-data';

export interface Signal {
    id: number;
    symbol: string;
    marketType: 'BIST' | 'Kripto';
    strategy: 'COMBO' | 'HUNTER';
    signalType: 'AL' | 'SAT';
    timeframe: string;
    score: string;
    price: number;
    createdAt: string;
}

interface UseSignalsOptions {
    marketType?: 'all' | 'BIST' | 'Kripto';
    strategy?: 'all' | 'COMBO' | 'HUNTER';
    direction?: 'all' | 'AL' | 'SAT';
    searchQuery?: string;
}

// Fetch signals from API or fallback to mock data
async function fetchSignalsData(options: UseSignalsOptions = {}): Promise<Signal[]> {
    const { marketType, strategy, direction } = options;

    try {
        // Build API params
        const params: SignalsParams = { limit: 100 };
        if (strategy && strategy !== 'all') params.strategy = strategy;
        if (direction && direction !== 'all') params.signal_type = direction;

        const apiSignals = await fetchSignals(params);

        // Transform and filter
        let signals = apiSignals.map(transformSignal);

        // Apply additional filters that API doesn't support
        if (marketType && marketType !== 'all') {
            signals = signals.filter(s => s.marketType === marketType);
        }

        return signals;
    } catch (error) {
        console.warn('API unavailable, using mock data:', error);
        // Fallback to mock data
        return mockSignals;
    }
}

export function useSignals(options: UseSignalsOptions = {}) {
    const { marketType = 'all', strategy = 'all', direction = 'all', searchQuery = '' } = options;

    return useQuery({
        queryKey: ['signals', marketType, strategy, direction],
        queryFn: () => fetchSignalsData({ marketType, strategy, direction }),
        select: (data) => {
            // Client-side search filter
            if (searchQuery) {
                return data.filter(signal =>
                    signal.symbol.toLowerCase().includes(searchQuery.toLowerCase())
                );
            }
            return data;
        },
    });
}

export function useRecentSignals(limit: number = 5) {
    return useQuery({
        queryKey: ['signals', 'recent', limit],
        queryFn: () => fetchSignalsData({}),
        select: (data) => data.slice(0, limit),
    });
}

export function useSignalStats() {
    return useQuery({
        queryKey: ['signals', 'stats'],
        queryFn: () => fetchSignalsData({}),
        select: (data) => ({
            total: data.length,
            byMarket: {
                BIST: data.filter(s => s.marketType === 'BIST').length,
                Kripto: data.filter(s => s.marketType === 'Kripto').length,
            },
            byStrategy: {
                COMBO: data.filter(s => s.strategy === 'COMBO').length,
                HUNTER: data.filter(s => s.strategy === 'HUNTER').length,
            },
            byDirection: {
                AL: data.filter(s => s.signalType === 'AL').length,
                SAT: data.filter(s => s.signalType === 'SAT').length,
            },
        }),
    });
}
