'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import { createRealtimeConnection } from './connection';
import { useRealtimeStore } from './store';
import type { SignalData } from './types';
import { resolveRealtimeWsBaseUrl } from './url';

interface UseRealtimeConnectionOptions {
  autoConnect?: boolean;
  onSignal?: (signal: SignalData) => void;
}

export function useRealtimeConnection(options: UseRealtimeConnectionOptions = {}) {
  const { autoConnect = true, onSignal } = options;
  const queryClient = useQueryClient();
  const connectionRef = useRef<ReturnType<typeof createRealtimeConnection> | null>(null);
  const onSignalRef = useRef(onSignal);

  useEffect(() => { onSignalRef.current = onSignal; }, [onSignal]);

  useEffect(() => {
    // Each effect setup owns a fresh controller, including StrictMode's second setup.
    const connection = createRealtimeConnection({
      baseUrl: () => resolveRealtimeWsBaseUrl(
        window.location.origin,
        process.env.NEXT_PUBLIC_API_URL,
        process.env.NEXT_PUBLIC_WS_URL,
      ),
      getStore: useRealtimeStore.getState,
      onSignal: (signal) => onSignalRef.current?.(signal),
      refreshSignals: () => {
        // A continuous feed must not keep cancelling slower REST requests.
        const options = { cancelRefetch: false };
        void queryClient.invalidateQueries({ queryKey: ['signals'] }, options);
        void queryClient.invalidateQueries({ queryKey: ['signal-analysis'] }, options);
        void queryClient.invalidateQueries({ queryKey: ['analyses'] }, options);
        void queryClient.invalidateQueries({ queryKey: ['scanner-v2', 'signals'] }, options);
      },
    });
    connectionRef.current = connection;
    if (autoConnect) connection.connect();
    return () => {
      connectionRef.current = null;
      connection.dispose();
    };
  }, [autoConnect, queryClient]);

  const connect = useCallback(() => connectionRef.current?.connect(), []);
  const disconnect = useCallback(() => connectionRef.current?.disconnect(), []);
  const subscribe = useCallback((type: 'ticker' | 'kline' | 'trade', symbol: string, interval = '1m') =>
    connectionRef.current?.subscribe(type, symbol, interval) ?? (() => {}), []);

  return { connect, disconnect, subscribe };
}
