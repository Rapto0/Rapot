'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import { useRealtimeConnection } from '@/lib/realtime/use-realtime-connection';
import { useRealtimeStore } from '@/lib/realtime/store';
import type {
  BISTStock,
  KlineData,
  SignalData,
  TickerData,
  TradeData,
} from '@/lib/realtime/types';

export type { BISTStock, KlineData, SignalData, TickerData, TradeData };
export { useRealtimeStore };

interface UseRealtimeOptions {
  autoConnect?: boolean;
  onSignal?: (signal: SignalData) => void;
}

export function useRealtime(options: UseRealtimeOptions = {}) {
  const { autoConnect = true, onSignal } = options;

  const connectionState = useRealtimeStore((state) => state.connectionState);
  const tickers = useRealtimeStore((state) => state.tickers);
  const bistStocks = useRealtimeStore((state) => state.bistStocks);
  const priceChanges = useRealtimeStore((state) => state.priceChanges);
  const realtimeSignals = useRealtimeStore((state) => state.realtimeSignals);

  const { connect, disconnect, subscribe } = useRealtimeConnection({
    autoConnect,
    onSignal,
  });

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

export function useTradeStream(symbol?: string) {
  const { recentTrades } = useRealtimeStore();

  const filteredTrades = useMemo(() => {
    if (!symbol) return recentTrades;
    return recentTrades.filter((t) => t.symbol === symbol);
  }, [recentTrades, symbol]);

  return filteredTrades;
}

export function useAnimatedNumber(value: number, duration: number = 300) {
  const [displayValue, setDisplayValue] = useState(value);
  const [direction, setDirection] = useState<'up' | 'down' | null>(null);
  const previousValue = useRef(value);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (value !== previousValue.current) {
      setDirection(value > previousValue.current ? 'up' : 'down');
      const startValue = previousValue.current;
      previousValue.current = value;

      const diff = value - startValue;
      const startTime = performance.now();

      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }

      const animate = (currentTime: number) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        setDisplayValue(startValue + diff * eased);

        if (progress < 1) {
          rafRef.current = requestAnimationFrame(animate);
        } else {
          rafRef.current = null;
        }
      };

      rafRef.current = requestAnimationFrame(animate);

      const timeout = setTimeout(() => setDirection(null), duration + 100);
      return () => {
        clearTimeout(timeout);
        if (rafRef.current !== null) {
          cancelAnimationFrame(rafRef.current);
          rafRef.current = null;
        }
      };
    }
  }, [value, duration]);

  return { displayValue, direction };
}
