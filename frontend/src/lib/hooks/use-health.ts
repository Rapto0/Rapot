import { useQuery } from '@tanstack/react-query';
import { fetchHealth, fetchBotStatus } from '@/lib/api/client';
import { deriveBotHealth } from '@/lib/health-status';

// Health check hook
export function useHealthCheck() {
    return useQuery({
        queryKey: ['health'],
        queryFn: fetchHealth,
        refetchInterval: 60000, // Check every 60 seconds
    });
}

// Bot status hook - more detailed
export function useBotStatus() {
    return useQuery({
        queryKey: ['bot', 'status'],
        queryFn: fetchBotStatus,
        refetchInterval: 30000, // Refresh every 30 seconds
        staleTime: 30000,
    });
}

// Simplified hook for components
export function useBotHealth() {
    return deriveBotHealth(useBotStatus());
}
