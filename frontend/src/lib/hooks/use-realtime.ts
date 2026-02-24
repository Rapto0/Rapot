'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { create } from 'zustand';

// ==================== TYPES ====================

export interface TickerData {
  symbol: string;
  price: number;
  priceChange: number;
  priceChangePercent: number;
  high24h: number;
  low24h: number;
  volume24h: number;
  quoteVolume24h: number;
  timestamp: string;
  market?: 'crypto' | 'bist';
}

export interface BISTStock {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
  open: number;
  prevClose: number;
  timestamp: string;
  market: 'BIST';
}

export interface KlineData {
  symbol: string;
  interval: string;
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  isClosed: boolean;
}

export interface TradeData {
  symbol: string;
  tradeId: number;
  price: number;
  quantity: number;
  side: 'BUY' | 'SELL';
  timestamp: string;
}

export interface SignalData {
  id: number;
  symbol: string;
  marketType: string;
  strategy: string;
  signalType: 'AL' | 'SAT';
  timeframe: string;
  score: string;
  price: number;
  createdAt: string;
}

export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error';

// ==================== ZUSTAND STORE ====================

interface RealtimeStore {
  // Connection state
  connectionState: ConnectionState;
  setConnectionState: (state: ConnectionState) => void;

  // Ticker data (both crypto and BIST)
  tickers: Map<string, TickerData>;
  bistStocks: Map<string, BISTStock>;
  updateTicker: (ticker: TickerData) => void;
  updateBistStock: (stock: BISTStock) => void;
  updateBistStocks: (stocks: BISTStock[]) => void;

  // Price change tracking for flash effects
  priceChanges: Map<string, 'up' | 'down' | null>;
  setPriceChange: (symbol: string, direction: 'up' | 'down' | null) => void;

  // Signals
  realtimeSignals: SignalData[];
  addSignal: (signal: SignalData) => void;

  // Kline data
  klineData: Map<string, KlineData>;
  updateKline: (kline: KlineData) => void;

  // Recent trades
  recentTrades: TradeData[];
  addTrade: (trade: TradeData) => void;
}

export const useRealtimeStore = create<RealtimeStore>((set, get) => ({
  connectionState: 'disconnected',
  setConnectionState: (state) => set({ connectionState: state }),

  tickers: new Map(),
  bistStocks: new Map(),

  updateTicker: (ticker) => {
    const { tickers, setPriceChange } = get();
    const existing = tickers.get(ticker.symbol);

    // Track price direction for flash effect
    if (existing) {
      if (ticker.price > existing.price) {
        setPriceChange(ticker.symbol, 'up');
      } else if (ticker.price < existing.price) {
        setPriceChange(ticker.symbol, 'down');
      }
    }

    const newTickers = new Map(tickers);
    newTickers.set(ticker.symbol, { ...ticker, market: 'crypto' });
    set({ tickers: newTickers });
  },

  updateBistStock: (stock) => {
    const { bistStocks, setPriceChange } = get();
    const existing = bistStocks.get(stock.symbol);

    if (existing && stock.price !== existing.price) {
      setPriceChange(stock.symbol, stock.price > existing.price ? 'up' : 'down');
    }

    const newStocks = new Map(bistStocks);
    newStocks.set(stock.symbol, stock);
    set({ bistStocks: newStocks });
  },

  updateBistStocks: (stocks) => {
    const { bistStocks } = get();
    const newStocks = new Map(bistStocks);
    stocks.forEach((stock) => {
      newStocks.set(stock.symbol, stock);
    });
    set({ bistStocks: newStocks });
  },

  priceChanges: new Map(),
  _flashTimers: new Map<string, NodeJS.Timeout>(),
  setPriceChange: (symbol, direction) => {
    const state = get() as any;
    const newChanges = new Map<string, 'up' | 'down' | null>(state.priceChanges);
    newChanges.set(symbol, direction);
    set({ priceChanges: newChanges });

    // Clear flash after animation, debounce per symbol
    if (direction) {
      const timers = state._flashTimers as Map<string, NodeJS.Timeout>;
      const existing = timers.get(symbol);
      if (existing) clearTimeout(existing);

      timers.set(symbol, setTimeout(() => {
        const current = get().priceChanges;
        if (current.get(symbol) === direction) {
          const cleared = new Map(current);
          cleared.set(symbol, null);
          set({ priceChanges: cleared });
        }
        timers.delete(symbol);
      }, 500));
    }
  },

  realtimeSignals: [],
  addSignal: (signal) => {
    set((state) => ({
      realtimeSignals: [signal, ...state.realtimeSignals].slice(0, 50),
    }));
  },

  klineData: new Map(),
  updateKline: (kline) => {
    const key = `${kline.symbol}_${kline.interval}`;
    const newKlines = new Map(get().klineData);
    newKlines.set(key, kline);
    set({ klineData: newKlines });
  },

  recentTrades: [],
  addTrade: (trade) => {
    set((state) => ({
      recentTrades: [trade, ...state.recentTrades].slice(0, 100),
    }));
  },
}));

// ==================== WEBSOCKET HOOK ====================

interface UseRealtimeOptions {
  autoConnect?: boolean;
  onSignal?: (signal: SignalData) => void;
}

export function useRealtime(options: UseRealtimeOptions = {}) {
  const { autoConnect = true, onSignal } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const onSignalRef = useRef(onSignal);

  // Keep onSignal ref updated
  useEffect(() => {
    onSignalRef.current = onSignal;
  }, [onSignal]);

  // Subscribe to store state (read-only)
  const connectionState = useRealtimeStore((state) => state.connectionState);
  const tickers = useRealtimeStore((state) => state.tickers);
  const bistStocks = useRealtimeStore((state) => state.bistStocks);
  const priceChanges = useRealtimeStore((state) => state.priceChanges);
  const realtimeSignals = useRealtimeStore((state) => state.realtimeSignals);

  const getWebSocketUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || 'localhost:8000';
    return `${protocol}//${host}/realtime/ws/ticker`;
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    const store = useRealtimeStore.getState();
    store.setConnectionState('connecting');

    try {
      const ws = new WebSocket(getWebSocketUrl());

      ws.onopen = () => {
        useRealtimeStore.getState().setConnectionState('connected');
        reconnectAttemptsRef.current = 0;
        console.log('[Realtime] Connected to WebSocket');
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const store = useRealtimeStore.getState();

          switch (message.type) {
            case 'init':
              // Initial data load
              if (message.crypto) {
                Object.values(message.crypto).forEach((ticker) => {
                  store.updateTicker(ticker as TickerData);
                });
              }
              if (message.bist) {
                store.updateBistStocks(message.bist as BISTStock[]);
              }
              break;

            case 'ticker':
              store.updateTicker(message.data as TickerData);
              break;

            case 'bist':
              store.updateBistStocks(message.data as BISTStock[]);
              break;

            case 'kline':
              store.updateKline(message.data as KlineData);
              break;

            case 'trade':
              store.addTrade(message.data as TradeData);
              break;

            case 'signal':
              const signal = message.data as SignalData;
              store.addSignal(signal);
              onSignalRef.current?.(signal);
              break;

            case 'heartbeat':
              // Connection alive
              break;

            default:
              console.log('[Realtime] Unknown message type:', message.type);
          }
        } catch (error) {
          console.error('[Realtime] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        useRealtimeStore.getState().setConnectionState('disconnected');

        // Auto-reconnect with exponential backoff (max 5 attempts)
        if (reconnectAttemptsRef.current < 5) {
          const delay = Math.min(2000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          useRealtimeStore.getState().setConnectionState('reconnecting');
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        } else if (reconnectAttemptsRef.current === 5) {
          console.warn('[Realtime] Backend unavailable - real-time features disabled. Data will load via REST API.');
        }
      };

      ws.onerror = () => {
        useRealtimeStore.getState().setConnectionState('error');
        // Suppress verbose error logging - onclose handles reconnection
      };

      wsRef.current = ws;
    } catch (error) {
      useRealtimeStore.getState().setConnectionState('error');
      console.error('[Realtime] Connection error:', error);
    }
  }, [getWebSocketUrl]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    useRealtimeStore.getState().setConnectionState('disconnected');
  }, []);

  const subscribe = useCallback((type: 'ticker' | 'kline' | 'trade', symbol: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        type,
        symbol,
      }));
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoConnect]);

  return {
    connectionState,
    connect,
    disconnect,
    subscribe,
    tickers,
    bistStocks,
    priceChanges,
    realtimeSignals,
  };
}

// ==================== TICKER HOOK ====================

export function useTickerData(symbols?: string[]) {
  const { tickers, bistStocks, priceChanges } = useRealtimeStore();

  const filteredTickers = useMemo(() => {
    if (!symbols || symbols.length === 0) {
      return Array.from(tickers.values());
    }
    return symbols
      .map((s) => tickers.get(s))
      .filter((t): t is TickerData => t !== undefined);
  }, [tickers, symbols]);

  const filteredBist = useMemo(() => {
    if (!symbols || symbols.length === 0) {
      return Array.from(bistStocks.values());
    }
    return symbols
      .map((s) => bistStocks.get(s))
      .filter((s): s is BISTStock => s !== undefined);
  }, [bistStocks, symbols]);

  // Combined data for ticker strip
  const combinedTickers = useMemo(() => {
    const crypto = Array.from(tickers.values()).slice(0, 20).map((t) => ({
      symbol: t.symbol,
      name: t.symbol.replace('USDT', ''),
      price: t.price,
      change: t.priceChange,
      changePercent: t.priceChangePercent,
      market: 'crypto' as const,
      flash: priceChanges.get(t.symbol),
    }));

    const bist = Array.from(bistStocks.values()).slice(0, 20).map((s) => ({
      symbol: s.symbol,
      name: s.name || s.symbol,
      price: s.price,
      change: s.change,
      changePercent: s.changePercent,
      market: 'bist' as const,
      flash: priceChanges.get(s.symbol),
    }));

    return [...crypto, ...bist];
  }, [tickers, bistStocks, priceChanges]);

  return {
    tickers: filteredTickers,
    bistStocks: filteredBist,
    combinedTickers,
    priceChanges,
  };
}

// ==================== KLINE HOOK ====================

export function useKlineStream(symbol: string, interval: string = '1m') {
  const { subscribe } = useRealtime({ autoConnect: false });
  const { klineData } = useRealtimeStore();

  const key = `${symbol}_${interval}`;
  const kline = klineData.get(key);

  useEffect(() => {
    subscribe('kline', symbol);
  }, [symbol, interval, subscribe]);

  return kline;
}

// ==================== TRADE STREAM HOOK ====================

export function useTradeStream(symbol?: string) {
  const { recentTrades } = useRealtimeStore();

  const filteredTrades = useMemo(() => {
    if (!symbol) return recentTrades;
    return recentTrades.filter((t) => t.symbol === symbol);
  }, [recentTrades, symbol]);

  return filteredTrades;
}

// ==================== ANIMATED NUMBER HOOK ====================

export function useAnimatedNumber(value: number, duration: number = 300) {
  const [displayValue, setDisplayValue] = useState(value);
  const [direction, setDirection] = useState<'up' | 'down' | null>(null);
  const previousValue = useRef(value);
  const animFrameRef = useRef<number | null>(null);

  useEffect(() => {
    if (value !== previousValue.current) {
      setDirection(value > previousValue.current ? 'up' : 'down');
      const startValue = previousValue.current;
      previousValue.current = value;
      const diff = value - startValue;
      const startTime = performance.now();

      // Cancel any ongoing animation
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }

      const animate = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Easing function
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplayValue(startValue + diff * eased);

        if (progress < 1) {
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
          animFrameRef.current = null;
        }
      };

      animFrameRef.current = requestAnimationFrame(animate);

      // Clear direction after animation
      const timeout = setTimeout(() => setDirection(null), duration + 100);
      return () => {
        clearTimeout(timeout);
        if (animFrameRef.current) {
          cancelAnimationFrame(animFrameRef.current);
        }
      };
    }
  }, [value, duration]);

  return { displayValue, direction };
}
