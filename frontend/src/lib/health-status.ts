import type { ApiBotStatus } from './api/types';

export type BotState = 'loading' | 'unknown' | 'running' | 'stopped';

interface StatusQuery {
  data?: ApiBotStatus;
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
  isStale: boolean;
}

/** Old successful responses cannot assert current liveness during an error or refresh. */
export function deriveBotHealth(query: StatusQuery) {
  const status = query.data;
  let state: BotState = 'unknown';
  if (query.isError) state = 'unknown';
  else if (query.isLoading || query.isFetching) state = 'loading';
  else if (!query.isStale && status?.bot?.database === 'connected') {
    if (status.bot.state === 'running' && status.bot.is_running === true) state = 'running';
    else if (status.bot.state === 'stopped' && status.bot.is_running === false) state = 'stopped';
  }

  const usable = !query.isError && !query.isLoading && !query.isFetching && !query.isStale
    && status?.bot?.database === 'connected';
  const countersUsable = usable && status?.scanning?.data_available !== false;
  const isRunning = state === 'running' ? true : state === 'stopped' ? false : null;
  const isScanning = usable && isRunning !== null
    && typeof status.bot.is_scanning === 'boolean' ? status.bot.is_scanning : null;
  return {
    state,
    label: { loading: 'Yükleniyor', unknown: 'Bilinmiyor', running: 'Çalışıyor', stopped: 'Durdu' }[state],
    tone: state === 'running' ? 'profit' as const : state === 'stopped' ? 'loss' as const : 'neutral' as const,
    isRunning,
    isScanning,
    scanningLabel: isScanning === true ? 'Sürüyor' : isScanning === false ? 'Bekliyor' : 'Bilinmiyor',
    uptime: usable && isRunning !== null ? status?.bot.uptime_human ?? '--' : '--',
    lastScan: usable && status?.scanning?.last_scan_available !== false ? status?.scanning?.last_scan_time ?? null : null,
    scanCount: countersUsable ? status?.scanning?.scan_count ?? null : null,
    signalCount: countersUsable ? status?.scanning?.signal_count ?? null : null,
    errorCount: usable ? status?.errors?.error_count ?? null : null,
    apiState: query.isError ? 'error' as const : query.isLoading || query.isFetching ? 'loading' as const
      : query.isStale || !status ? 'unknown' as const : 'connected' as const,
    isLoading: query.isLoading,
    isError: query.isError,
  };
}
