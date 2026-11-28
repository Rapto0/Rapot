import type { ApiHealth } from './api/types';
import type { AdvancedAlarmStatus } from './api/advanced-alarms-api';

interface StatusQuery<T> {
  data?: T;
  dataUpdatedAt?: number;
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
  isStale: boolean;
}

function usable<T>(query: StatusQuery<T>) {
  return !query.isError && !query.isLoading && !query.isFetching && !query.isStale;
}

export function lastHealthMeasurementAt(query: Pick<StatusQuery<unknown>, 'data' | 'dataUpdatedAt'>) {
  const time = query.dataUpdatedAt;
  return query.data != null && typeof time === 'number' && Number.isSafeInteger(time)
    && time > 0 && Number.isFinite(new Date(time).getTime()) ? time : null;
}

/** A reachable API, an alarm worker and fresh market data are separate facts. */
export function deriveApiHealth(query: StatusQuery<ApiHealth>) {
  const data = usable(query) ? query.data : undefined;
  const confirmed = data?.status === 'healthy' && data.database === 'connected'
    && data.realtime === 'running';
  const apiState = query.isError ? 'error' as const
    : query.isLoading || query.isFetching ? 'loading' as const
      : confirmed ? 'connected' as const : 'unknown' as const;
  return {
    apiState,
    label: { connected: 'Bağlı', error: 'Doğrulanamadı', loading: 'Yükleniyor', unknown: 'Bilinmiyor' }[apiState],
    tone: apiState === 'connected' ? 'profit' as const : apiState === 'error' ? 'loss' as const : 'neutral' as const,
    lastMeasuredAt: lastHealthMeasurementAt(query),
    uptime: confirmed && Number.isFinite(data.uptime_seconds) && data.uptime_seconds >= 0
      && typeof data.uptime_human === 'string' ? data.uptime_human : '—',
    database: data?.database === 'connected' ? 'Bağlı' : data?.database === 'error' ? 'Hata' : 'Bilinmiyor',
    realtime: data?.realtime === 'running' ? 'Çalışıyor' : data?.realtime === 'error' ? 'Hata' : 'Bilinmiyor',
  };
}

function optionalCount(value: unknown): number | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null;
}

export function deriveAlarmRuntime(query: StatusQuery<AdvancedAlarmStatus>, now = Date.now()) {
  const data = usable(query) ? query.data : undefined;
  const lastCycle = typeof data?.last_cycle_at === 'string' ? Date.parse(data.last_cycle_at) : NaN;
  const recentCycle = Number.isFinite(lastCycle) && now - lastCycle >= -5000 && now - lastCycle <= 30_000;
  const state = query.isLoading || query.isFetching ? 'loading'
    : !data || query.isError ? 'unknown'
      : data.last_error != null ? 'error'
        : data.running === false ? 'stopped'
          : data.running === true && recentCycle ? 'running'
            : data.running === true && data.last_cycle_at === null ? 'starting' : 'unknown';
  const market = data?.market && typeof data.market === 'object' && !Array.isArray(data.market) ? data.market : undefined;
  const custom = market?.custom_indicators && typeof market.custom_indicators === 'object' && !Array.isArray(market.custom_indicators)
    ? market.custom_indicators as Record<string, unknown> : undefined;
  return {
    state,
    label: { loading: 'Yükleniyor', unknown: 'Doğrulanamadı', error: 'Kontrol hatası', stopped: 'Durduruldu', running: 'Çalışıyor', starting: 'İlk kontrol bekleniyor' }[state],
    tone: state === 'running' ? 'profit' as const : state === 'error' || state === 'stopped' ? 'loss' as const : 'neutral' as const,
    lastMeasuredAt: lastHealthMeasurementAt(query),
    lastCycle: data && Number.isFinite(lastCycle) ? lastCycle : null,
    telegramConfigured: typeof data?.telegram_configured === 'boolean' ? data.telegram_configured : null,
    pendingDeliveries: optionalCount(data?.delivery?.pending),
    marketState: typeof market?.state === 'string' ? market.state : null,
    freshSymbols: optionalCount(market?.fresh_symbols ?? market?.ready_symbols),
    trackedSymbols: optionalCount(market?.tracked_symbols ?? market?.symbol_count),
    nativeStreamsConnected: optionalCount(custom?.native_streams_connected),
    nativeRegistered: optionalCount(custom?.native_subscriptions_registered),
    nativeCapacity: optionalCount(custom?.native_physical_capacity),
    nativeLeaseCertified: optionalCount(custom?.native_lease_certified),
    nativeLeasePending: optionalCount(custom?.native_lease_pending),
    liveQueuePending: optionalCount(custom?.live_queue_pending),
    liveQueueLimit: optionalCount(custom?.live_queue_limit),
    liveOverflowCount: optionalCount(custom?.live_overflow_count),
  };
}
