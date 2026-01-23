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

// Fetch dashboard KPIs from API
async function fetchDashboardKPIs(): Promise<DashboardKPIs> {
    const apiStats = await fetchStats();
    return transformStats(apiStats);
}

export function useDashboardKPIs() {
    return useQuery({
        queryKey: ['dashboard', 'kpis'],
        queryFn: fetchDashboardKPIs,
        refetchInterval: 10000, // Refresh every 10 seconds
    });
}
