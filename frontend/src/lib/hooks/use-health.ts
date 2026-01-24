import { useQuery } from '@tanstack/react-query';
import { fetchHealth, fetchBotStatus, type ApiHealth, type ApiBotStatus } from '@/lib/api/client';

// Health check hook
export function useHealthCheck() {
    return useQuery({
        queryKey: ['health'],
        queryFn: fetchHealth,
        refetchInterval: 5000, // Check every 5 seconds
    });
}

// Bot status hook - more detailed
export function useBotStatus() {
    return useQuery({
        queryKey: ['bot', 'status'],
        queryFn: fetchBotStatus,
        refetchInterval: 10000, // Refresh every 10 seconds
    });
}

// Simplified hook for components
export function useBotHealth() {
    const { data: status, isLoading, isError } = useBotStatus();

    return {
        isRunning: status?.bot.is_running ?? true,
        isScanning: status?.bot.is_scanning ?? false,
        uptime: status?.bot.uptime_human ?? 'N/A',
        lastScan: status?.scanning.last_scan_time ?? null,
        scanCount: status?.scanning.scan_count ?? 0,
        errorCount: status?.errors.error_count ?? 0,
        isLoading,
        isError,
    };
}
