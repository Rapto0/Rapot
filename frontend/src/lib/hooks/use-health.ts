import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from '@/lib/api/client';
import { fetchAdvancedAlarmStatus } from '@/lib/api/advanced-alarms-api';
import { deriveApiHealth, deriveAlarmRuntime } from '@/lib/health-status';
import { useSession } from './use-session';

export function useApiHealth() {
    const session = useSession();
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled);
    const query = useQuery({
        queryKey: ['api-health', session?.user.username, session?.expiresAt],
        queryFn: ({ signal }) => fetchHealth(signal),
        enabled: allowed,
        refetchInterval: 30_000,
        staleTime: 30_000,
        refetchIntervalInBackground: false,
        retry: false,
    });
    return deriveApiHealth({ ...query, data: allowed ? query.data : undefined });
}

export function useAlarmRuntimeHealth() {
    const session = useSession();
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled);
    const query = useQuery({
        queryKey: ['advanced-alarm-status', session?.user.username, session?.expiresAt],
        queryFn: ({ signal }) => fetchAdvancedAlarmStatus(signal),
        enabled: allowed,
        refetchInterval: 15_000,
        staleTime: 15_000,
        refetchIntervalInBackground: false,
        retry: false,
    });
    return deriveAlarmRuntime({ ...query, data: allowed ? query.data : undefined });
}
