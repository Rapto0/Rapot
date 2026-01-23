import { useQuery } from '@tanstack/react-query';
import { fetchStats, transformStats } from '@/lib/api/client';
import { mockKPIStats } from '@/lib/mock-data';

export interface DashboardKPIs {
    totalPnL: number;
    totalPnLPercent: number;
    winRate: number;
    openPositions: number;
    closedPositions: number;
    totalTrades: number;
    lastScanTime: string;
    totalSignals: number;
    todaySignals: number;
}

// Fetch dashboard KPIs from API or fallback to mock data
async function fetchDashboardKPIs(): Promise<DashboardKPIs> {
    try {
        const apiStats = await fetchStats();
        return transformStats(apiStats);
    } catch (error) {
        console.warn('API unavailable, using mock data:', error);
        // Fallback to mock data
        return mockKPIStats;
    }
}

export function useDashboardKPIs() {
    return useQuery({
        queryKey: ['dashboard', 'kpis'],
        queryFn: fetchDashboardKPIs,
        refetchInterval: 10000, // Refresh every 10 seconds
    });
}
