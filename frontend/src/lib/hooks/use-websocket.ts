'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

// WebSocket connection states
export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error';

// Message types matching backend protocol
export interface WebSocketMessage<T = unknown> {
    type: 'SIGNAL_UPDATE' | 'NEW_SIGNAL' | 'TRADE_UPDATE' | 'PRICE_UPDATE' | 'HEALTH_UPDATE';
    payload: T;
    timestamp: number;
}

interface UseWebSocketOptions {
    url: string;
    reconnectInterval?: number;
    maxRetries?: number;
    onMessage?: (message: WebSocketMessage) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Event) => void;
}

interface UseWebSocketReturn {
    state: WebSocketState;
    lastMessage: WebSocketMessage | null;
    send: (data: unknown) => void;
    connect: () => void;
    disconnect: () => void;
}

/**
 * WebSocket hook for real-time updates
 *
 * Usage:
 * ```tsx
 * const { state, lastMessage } = useWebSocket({
 *   url: 'ws://localhost:8000/ws/signals',
 *   onMessage: (msg) => console.log(msg),
 * });
 * ```
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
    const {
        url,
        reconnectInterval = 5000,
        maxRetries = 5,
        onMessage,
        onConnect,
        onDisconnect,
        onError,
    } = options;

    const wsRef = useRef<WebSocket | null>(null);
    const retriesRef = useRef(0);
    const [state, setState] = useState<WebSocketState>('disconnected');
    const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);

    const connect = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            return;
        }

        setState('connecting');

        try {
            const ws = new WebSocket(url);

            ws.onopen = () => {
                setState('connected');
                retriesRef.current = 0;
                onConnect?.();
            };

            ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data) as WebSocketMessage;
                    setLastMessage(message);
                    onMessage?.(message);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };

            ws.onclose = () => {
                setState('disconnected');
                onDisconnect?.();

                // Auto-reconnect with exponential backoff
                if (retriesRef.current < maxRetries) {
                    retriesRef.current += 1;
                    const delay = reconnectInterval * Math.pow(2, retriesRef.current - 1);
                    setTimeout(connect, delay);
                }
            };

            ws.onerror = (error) => {
                setState('error');
                onError?.(error);
            };

            wsRef.current = ws;
        } catch (error) {
            setState('error');
            console.error('WebSocket connection error:', error);
        }
    }, [url, reconnectInterval, maxRetries, onConnect, onDisconnect, onMessage, onError]);

    const disconnect = useCallback(() => {
        if (wsRef.current) {
            wsRef.current.close();
            wsRef.current = null;
        }
        setState('disconnected');
    }, []);

    const send = useCallback((data: unknown) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(data));
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, [disconnect]);

    return { state, lastMessage, send, connect, disconnect };
}

// ==================== REAL-TIME SIGNAL UPDATES ====================

interface SignalUpdate {
    id: number;
    symbol: string;
    signalType: 'AL' | 'SAT';
    strategy: string;
    timestamp: string;
}

/**
 * Hook for polling-based real-time signal updates
 * Uses React Query invalidation for updates until WebSocket is available
 */
export function useSignalUpdates(onNewSignal?: (signal: SignalUpdate) => void) {
    const [lastSignalId, setLastSignalId] = useState<number | null>(null);
    const [newSignals, setNewSignals] = useState<SignalUpdate[]>([]);

    // Check for new signals by comparing IDs
    const checkNewSignal = useCallback((signals: SignalUpdate[]) => {
        if (signals.length > 0 && signals[0].id !== lastSignalId) {
            const newOnes = lastSignalId
                ? signals.filter(s => s.id > lastSignalId)
                : [];

            if (newOnes.length > 0) {
                setNewSignals(prev => [...newOnes, ...prev].slice(0, 10));
                newOnes.forEach(signal => onNewSignal?.(signal));
            }

            setLastSignalId(signals[0].id);
        }
    }, [lastSignalId, onNewSignal]);

    const clearNewSignals = useCallback(() => {
        setNewSignals([]);
    }, []);

    return { newSignals, clearNewSignals, checkNewSignal };
}

// ==================== CONNECTION STATUS ====================

/**
 * Hook to track overall connection status
 */
export function useConnectionStatus() {
    const [isOnline, setIsOnline] = useState(true);
    const [apiStatus, setApiStatus] = useState<'connected' | 'disconnected' | 'checking'>('checking');

    useEffect(() => {
        // Browser online/offline
        const handleOnline = () => setIsOnline(true);
        const handleOffline = () => setIsOnline(false);

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        // Check API connectivity
        const checkApi = async () => {
            try {
                const response = await fetch('http://localhost:8000/', {
                    method: 'GET',
                    signal: AbortSignal.timeout(3000),
                });
                setApiStatus(response.ok ? 'connected' : 'disconnected');
            } catch {
                setApiStatus('disconnected');
            }
        };

        checkApi();
        const interval = setInterval(checkApi, 30000);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
            clearInterval(interval);
        };
    }, []);

    return { isOnline, apiStatus };
}
