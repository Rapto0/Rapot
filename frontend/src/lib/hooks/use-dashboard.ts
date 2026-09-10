import { useQuery } from '@tanstack/react-query';
import {
    fetchOpsOverviewReadModel,
    fetchStats,
    transformOpsOverviewReadModel,
    transformStats,
} from '@/lib/api/client';
import type { DashboardStats } from '@/types';

export type DashboardKPIs = DashboardStats;

// Fetch dashboard KPIs from API
async function fetchDashboardKPIs(): Promise<DashboardKPIs> {
    try {
        const overview = await fetchOpsOverviewReadModel();
        return transformOpsOverviewReadModel(overview);
    } catch {
        const apiStats = await fetchStats();
        return transformStats(apiStats);
    }
}

export function useDashboardKPIs() {
    return useQuery({
        queryKey: ['dashboard', 'kpis'],
        queryFn: fetchDashboardKPIs,
        refetchInterval: 10000, // Refresh every 10 seconds
    });
}
