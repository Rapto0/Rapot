import { create } from 'zustand';

import type {
  BISTStock,
  ConnectionState,
  KlineData,
  SignalData,
  TickerData,
  TradeData,
} from './types';

interface RealtimeStore {
  connectionState: ConnectionState;
  setConnectionState: (state: ConnectionState) => void;

  tickers: Map<string, TickerData>;
  bistStocks: Map<string, BISTStock>;
  updateTicker: (ticker: TickerData) => void;
  updateBistStock: (stock: BISTStock) => void;
  updateBistStocks: (stocks: BISTStock[]) => void;

  priceChanges: Map<string, 'up' | 'down' | null>;
  setPriceChange: (symbol: string, direction: 'up' | 'down' | null) => void;

  realtimeSignals: SignalData[];
  addSignal: (signal: SignalData) => void;

  klineData: Map<string, KlineData>;
  updateKline: (kline: KlineData) => void;

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
  setPriceChange: (symbol, direction) => {
    const newChanges = new Map(get().priceChanges);
    newChanges.set(symbol, direction);
    set({ priceChanges: newChanges });

    if (direction) {
      setTimeout(() => {
        const current = get().priceChanges;
        if (current.get(symbol) === direction) {
          const cleared = new Map(current);
          cleared.set(symbol, null);
          set({ priceChanges: cleared });
        }
      }, 500);
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
