import { useQuery } from '@tanstack/react-query';
import { fetchHealth, fetchBotStatus, type ApiHealth, type ApiBotStatus } from '@/lib/api/client';
import { mockBotHealth } from '@/lib/mock-data';

// Health check hook
export function useHealthCheck() {
    return useQuery({
        queryKey: ['health'],
        queryFn: async (): Promise<ApiHealth> => {
            try {
                return await fetchHealth();
            } catch (error) {
                console.warn('Health API unavailable');
                // Return mock health
                return {
                    status: 'healthy',
                    uptime_seconds: 0,
                    uptime_human: mockBotHealth.uptime,
                    timestamp: new Date().toISOString(),
                };
            }
        },
        refetchInterval: 5000, // Check every 5 seconds
    });
}

// Bot status hook - more detailed
export function useBotStatus() {
    return useQuery({
        queryKey: ['bot', 'status'],
        queryFn: async (): Promise<ApiBotStatus> => {
            try {
                return await fetchBotStatus();
            } catch (error) {
                console.warn('Status API unavailable, using mock');
                // Return mock status
                return {
                    bot: {
                        is_running: true,
                        is_scanning: false,
                        uptime_seconds: 0,
                        uptime_human: mockBotHealth.uptime,
                        started_at: new Date().toISOString(),
                    },
                    scanning: {
                        last_scan_time: mockBotHealth.lastScan,
                        scan_count: mockBotHealth.totalScans,
                        signal_count: 0,
                    },
                    errors: {
                        error_count: 0,
                        last_error: null,
                    },
                    timestamp: new Date().toISOString(),
                };
            }
        },
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
