'use client';

import { useCallback, useEffect, useRef } from 'react';

import { createRealtimeConnection } from './connection';
import { useRealtimeStore } from './store';
import { resolveRealtimeWsBaseUrl } from './url';
import { getSession, getAccessToken } from '../auth/session';

interface UseRealtimeConnectionOptions {
  autoConnect?: boolean;
}

export function useRealtimeConnection(options: UseRealtimeConnectionOptions = {}) {
  const { autoConnect = true } = options;
  const connectionRef = useRef<ReturnType<typeof createRealtimeConnection> | null>(null);
  const session = getSession();
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled);
  const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : 'guest';


  useEffect(() => {
    useRealtimeStore.getState().resetPrivateData();
    if (!allowed) return;
    // Each effect setup owns a fresh controller, including StrictMode's second setup.
    const connection = createRealtimeConnection({
      getToken: getAccessToken,
      baseUrl: () => resolveRealtimeWsBaseUrl(
        window.location.origin,
        process.env.NEXT_PUBLIC_API_URL,
        process.env.NEXT_PUBLIC_WS_URL,
      ),
      getStore: useRealtimeStore.getState,
    });
    connectionRef.current = connection;
    if (autoConnect) connection.connect();
    return () => {
      connectionRef.current = null;
      connection.dispose();
      useRealtimeStore.getState().resetPrivateData();
    };
  }, [autoConnect, allowed, sessionKey]);

  const connect = useCallback(() => connectionRef.current?.connect(), []);
  const disconnect = useCallback(() => connectionRef.current?.disconnect(), []);
  const subscribe = useCallback((type: 'ticker' | 'kline' | 'trade', symbol: string, interval = '1m') =>
    connectionRef.current?.subscribe(type, symbol, interval) ?? (() => {}), []);

  return { connect, disconnect, subscribe };
}
