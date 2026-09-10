'use client';

import { useEffect } from 'react';
import { useRealtimeConnection } from '@/lib/realtime/use-realtime-connection';
import { useRealtimeStore } from '@/lib/realtime/store';

/** One connection owner for the active session, beneath QueryClientProvider. */
export function RealtimeBridge() {
  useEffect(() => {
    useRealtimeStore.getState().clearSignals();
    return () => useRealtimeStore.getState().clearSignals();
  }, []);
  useRealtimeConnection();
  return null;
}
