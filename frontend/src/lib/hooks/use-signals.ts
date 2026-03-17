import { useQuery } from '@tanstack/react-query';
import { fetchSignals, transformSignal, type SignalsParams } from '@/lib/api/client';

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
    specialTag: 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT' | null;
}

const SPECIAL_NOTIFICATION_RULES = [
    { strategy: 'HUNTER' as const, special_tag: 'BELES' as const },
    { strategy: 'HUNTER' as const, special_tag: 'COK_UCUZ' as const },
    { strategy: 'COMBO' as const, special_tag: 'BELES' as const },
    { strategy: 'COMBO' as const, special_tag: 'COK_UCUZ' as const },
];

interface UseSignalsOptions {
    marketType?: 'all' | 'BIST' | 'Kripto';
    strategy?: 'all' | 'COMBO' | 'HUNTER';
    direction?: 'all' | 'AL' | 'SAT';
    specialTag?: 'all' | 'BELES' | 'COK_UCUZ' | 'PAHALI' | 'FAHIS_FIYAT';
    searchQuery?: string;
    limit?: number;
}

// Fetch signals from API
async function fetchSignalsData(options: UseSignalsOptions = {}): Promise<Signal[]> {
    const { marketType, strategy, direction, specialTag, limit = 300 } = options;

    // Build API params - fetch more for pagination
    const params: SignalsParams = { limit };
    if (strategy && strategy !== 'all') params.strategy = strategy;
    if (direction && direction !== 'all') params.signal_type = direction;
    if (specialTag && specialTag !== 'all') params.special_tag = specialTag;

    // If specific market type requested, use API filter
    if (marketType && marketType !== 'all') {
        params.market_type = marketType;
        const apiSignals = await fetchSignals(params);
        return apiSignals.map(transformSignal);
    }

    // For 'all' markets, fetch both BIST and Kripto separately to ensure balanced results
    const perMarketLimit = Math.max(1, Math.ceil(limit / 2));
    const [bistSignals, kriptoSignals] = await Promise.all([
        fetchSignals({ ...params, market_type: 'BIST', limit: perMarketLimit }),
        fetchSignals({ ...params, market_type: 'Kripto', limit: perMarketLimit }),
    ]);

    // Combine and sort by date
    const allSignals = [...bistSignals, ...kriptoSignals]
        .map(transformSignal)
        .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

    return allSignals.slice(0, limit);
}

export function useSignals(options: UseSignalsOptions = {}) {
    const {
        marketType = 'all',
        strategy = 'all',
        direction = 'all',
        specialTag = 'all',
        searchQuery = '',
        limit = 300,
    } = options;

    return useQuery({
        queryKey: ['signals', marketType, strategy, direction, specialTag, searchQuery, limit],
        queryFn: () => fetchSignalsData({ marketType, strategy, direction, specialTag, limit }),
        refetchInterval: 45000, // Reduce API pressure while keeping UI fresh
        staleTime: 15000,
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
        queryFn: () => fetchSignalsData({ limit }),
        refetchInterval: 45000,
        staleTime: 15000,
    });
}

export function useSpecialNotificationSignals(limit: number = 100) {
    return useQuery({
        queryKey: ['signals', 'special-notifications', limit],
        queryFn: async () => {
            const perRuleLimit = Math.max(1, Math.ceil(limit / SPECIAL_NOTIFICATION_RULES.length));

            const responses = await Promise.all(
                SPECIAL_NOTIFICATION_RULES.map((rule) =>
                    fetchSignals({
                        strategy: rule.strategy,
                        special_tag: rule.special_tag,
                        limit: perRuleLimit,
                    })
                )
            );

            const deduped = new Map<number, Signal>();
            responses
                .flat()
                .map(transformSignal)
                .forEach((signal) => {
                    deduped.set(signal.id, signal);
                });

            return Array.from(deduped.values())
                .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
                .slice(0, limit);
        },
        refetchInterval: 45000,
        staleTime: 15000,
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
