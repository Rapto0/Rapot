'use client';

import { useCallback, useEffect, useRef } from 'react';

import { dispatchSignalSocketMessage, dispatchTickerSocketMessage } from './message-parser';
import { useRealtimeStore } from './store';
import type { BISTStock, SignalData, TickerData } from './types';

interface UseRealtimeConnectionOptions {
  autoConnect?: boolean;
  onSignal?: (signal: SignalData) => void;
}

function resolveRealtimeWsBaseUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const explicitWsUrl = process.env.NEXT_PUBLIC_WS_URL?.trim();
  if (explicitWsUrl) {
    return `${explicitWsUrl.replace(/\/$/, '')}/realtime/ws`;
  }

  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configuredApiUrl && /^https?:\/\//.test(configuredApiUrl)) {
    try {
      const parsed = new URL(configuredApiUrl);
      return `${protocol}//${parsed.host}/realtime/ws`;
    } catch {
      // Continue with hostname fallback when URL parsing fails.
    }
  }

  const host = `${window.location.hostname}:8000`;
  return `${protocol}//${host}/realtime/ws`;
}

export function useRealtimeConnection(options: UseRealtimeConnectionOptions = {}) {
  const { autoConnect = true, onSignal } = options;
  const tickerWsRef = useRef<WebSocket | null>(null);
  const signalWsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const signalReconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onSignalRef = useRef(onSignal);

  useEffect(() => {
    onSignalRef.current = onSignal;
  }, [onSignal]);

  const handleRealtimeSignal = useCallback((signal: SignalData) => {
    const store = useRealtimeStore.getState();
    store.addSignal(signal);
    onSignalRef.current?.(signal);
  }, []);

  const ensureSignalSocket = useCallback(() => {
    if (signalWsRef.current?.readyState === WebSocket.OPEN) return;
    if (signalWsRef.current?.readyState === WebSocket.CONNECTING) return;

    try {
      const signalWs = new WebSocket(`${resolveRealtimeWsBaseUrl()}/signals`);

      signalWs.onmessage = (event) => {
        dispatchSignalSocketMessage(event.data, {
          onSignal: handleRealtimeSignal,
          onParseError: (error) => {
            console.error('[Realtime] Failed to parse signal message:', error);
          },
        });
      };

      signalWs.onclose = () => {
        signalWsRef.current = null;
        if (tickerWsRef.current?.readyState === WebSocket.OPEN) {
          if (signalReconnectTimeoutRef.current) clearTimeout(signalReconnectTimeoutRef.current);
          signalReconnectTimeoutRef.current = setTimeout(() => {
            ensureSignalSocket();
          }, 3000);
        }
      };

      signalWs.onerror = () => {
        // Avoid noisy logs; onclose handles retry.
      };

      signalWsRef.current = signalWs;
    } catch (error) {
      console.error('[Realtime] Signal socket connection error:', error);
    }
  }, [handleRealtimeSignal]);

  const connect = useCallback(() => {
    if (tickerWsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const store = useRealtimeStore.getState();
    store.setConnectionState('connecting');

    try {
      const tickerWs = new WebSocket(`${resolveRealtimeWsBaseUrl()}/ticker`);

      tickerWs.onopen = () => {
        useRealtimeStore.getState().setConnectionState('connected');
        reconnectAttemptsRef.current = 0;
        console.log('[Realtime] Connected to WebSocket');
        ensureSignalSocket();
      };

      tickerWs.onmessage = (event) => {
        const storeState = useRealtimeStore.getState();
        dispatchTickerSocketMessage(event.data, {
          onInit: (payload) => {
            if (payload.crypto) {
              Object.values(payload.crypto).forEach((ticker) => {
                storeState.updateTicker(ticker as TickerData);
              });
            }
            if (payload.bist) {
              storeState.updateBistStocks(payload.bist as BISTStock[]);
            }
          },
          onTicker: (ticker) => storeState.updateTicker(ticker),
          onBist: (stocks) => storeState.updateBistStocks(stocks),
          onKline: (kline) => storeState.updateKline(kline),
          onTrade: (trade) => storeState.addTrade(trade),
          onSignal: handleRealtimeSignal,
          onUnknownType: (messageType) => {
            console.log('[Realtime] Unknown message type:', messageType);
          },
          onParseError: (error) => {
            console.error('[Realtime] Failed to parse message:', error);
          },
        });
      };

      tickerWs.onclose = () => {
        useRealtimeStore.getState().setConnectionState('disconnected');
        if (signalWsRef.current) {
          signalWsRef.current.close();
          signalWsRef.current = null;
        }

        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(2000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          useRealtimeStore.getState().setConnectionState('reconnecting');
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current === 5) {
          console.warn(
            '[Realtime] Backend unavailable - real-time features disabled. Data will load via REST API.'
          );
        }
      };

      tickerWs.onerror = () => {
        useRealtimeStore.getState().setConnectionState('error');
      };

      tickerWsRef.current = tickerWs;
    } catch (error) {
      useRealtimeStore.getState().setConnectionState('error');
      console.error('[Realtime] Connection error:', error);
    }
  }, [ensureSignalSocket, handleRealtimeSignal]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (signalReconnectTimeoutRef.current) {
      clearTimeout(signalReconnectTimeoutRef.current);
    }
    if (tickerWsRef.current) {
      tickerWsRef.current.close();
      tickerWsRef.current = null;
    }
    if (signalWsRef.current) {
      signalWsRef.current.close();
      signalWsRef.current = null;
    }
    useRealtimeStore.getState().setConnectionState('disconnected');
  }, []);

  const subscribe = useCallback((type: 'ticker' | 'kline' | 'trade', symbol: string) => {
    if (tickerWsRef.current?.readyState === WebSocket.OPEN) {
      tickerWsRef.current.send(JSON.stringify({
        action: 'subscribe',
        type,
        symbol,
      }));
    }
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    connect,
    disconnect,
    subscribe,
  };
}
