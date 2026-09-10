import { dispatchSignalSocketMessage, dispatchTickerSocketMessage } from './message-parser';
import type { useRealtimeStore } from './store';
import type { BISTStock, ConnectionState, KlineData, SignalData, TickerData, TradeData } from './types';

interface SocketOptions {
  url: () => string;
  onMessage: (data: string) => void;
  onOpen?: () => void;
  onState?: (state: ConnectionState) => void;
}

/** Own one socket and its retries; retired sockets can never change current state. */
export function createReconnectingSocket(options: SocketOptions) {
  let socket: WebSocket | null = null;
  let retry: ReturnType<typeof setTimeout> | null = null;
  let attempts = 0;
  let enabled = false;
  let disposed = false;

  function retire() {
    const previous = socket;
    socket = null;
    if (!previous) return;
    previous.onopen = previous.onmessage = previous.onclose = previous.onerror = null;
    previous.close();
  }

  function scheduleRetry() {
    if (!enabled || disposed || retry !== null) return;
    options.onState?.('reconnecting');
    const delay = Math.min(1000 * 2 ** Math.min(attempts++, 5), 30_000);
    retry = setTimeout(() => {
      retry = null;
      open();
    }, delay);
  }

  function open() {
    if (!enabled || disposed || socket || retry !== null) return;
    options.onState?.(attempts ? 'reconnecting' : 'connecting');
    try {
      const current = new WebSocket(options.url());
      socket = current;
      const isCurrent = () => enabled && !disposed && socket === current;
      current.onopen = () => {
        if (!isCurrent()) return;
        attempts = 0;
        options.onState?.('connected');
        options.onOpen?.();
      };
      current.onmessage = (event) => {
        if (isCurrent()) options.onMessage(String(event.data));
      };
      current.onclose = () => {
        if (!isCurrent()) return;
        retire();
        scheduleRetry();
      };
      current.onerror = () => {
        if (!isCurrent()) return;
        retire();
        scheduleRetry();
      };
    } catch {
      retire();
      scheduleRetry();
    }
  }

  function disconnect() {
    const wasActive = enabled || socket !== null || retry !== null;
    enabled = false;
    if (retry !== null) clearTimeout(retry);
    retry = null;
    attempts = 0;
    retire();
    if (wasActive) options.onState?.('disconnected');
  }

  return {
    connect() {
      if (disposed) return;
      enabled = true;
      open();
    },
    disconnect,
    dispose() {
      disposed = true;
      disconnect();
    },
  };
}

/** A fixed window coalesces bursts without postponing refresh during a steady feed. */
export function createSignalRefreshScheduler(refresh: () => void, delay = 30_000) {
  let pending: ReturnType<typeof setTimeout> | null = null;
  return {
    schedule() {
      if (pending !== null) return;
      pending = setTimeout(() => {
        pending = null;
        refresh();
      }, delay);
    },
    flush() {
      if (pending !== null) clearTimeout(pending);
      pending = null;
      refresh();
    },
    cancel() {
      if (pending !== null) clearTimeout(pending);
      pending = null;
    },
  };
}

interface RealtimeConnectionOptions {
  baseUrl: () => string;
  getStore: typeof useRealtimeStore.getState;
  refreshSignals: () => void;
  onSignal?: (signal: SignalData) => void;
}

export function createRealtimeConnection(options: RealtimeConnectionOptions) {
  const refresh = createSignalRefreshScheduler(options.refreshSignals);
  const subscriptions = new Map<string, { count: number; socket: ReturnType<typeof createReconnectingSocket> }>();
  let disposed = false;

  const onSignal = (signal: SignalData) => {
    options.getStore().addSignal(signal);
    refresh.schedule();
    options.onSignal?.(signal);
  };
  const tickerHandlers = {
    onInit: (payload: { crypto?: Record<string, unknown>; bist?: unknown }) => {
      if (payload.crypto) Object.values(payload.crypto).forEach((ticker) => options.getStore().updateTicker(ticker as TickerData));
      if (payload.bist) options.getStore().updateBistStocks(payload.bist as BISTStock[]);
    },
    onTicker: (ticker: TickerData) => options.getStore().updateTicker(ticker),
    onBist: (stocks: BISTStock[]) => options.getStore().updateBistStocks(stocks),
    onKline: (kline: KlineData) => options.getStore().updateKline(kline),
    onTrade: (trade: TradeData) => options.getStore().addTrade(trade),
    onSignal,
  };
  const ticker = createReconnectingSocket({
    url: () => `${options.baseUrl()}/ticker`,
    onState: (state) => options.getStore().setConnectionState(state),
    onMessage: (raw) => dispatchTickerSocketMessage(raw, tickerHandlers),
  });
  const signals = createReconnectingSocket({
    url: () => `${options.baseUrl()}/signals`,
    onState: (state) => options.getStore().setSignalConnectionState(state),
    onOpen: () => {
      options.getStore().clearSignals();
      refresh.flush();
    },
    onMessage: (raw) => dispatchSignalSocketMessage(raw, {
      onSignal,
      onResync: () => {
        options.getStore().clearSignals();
        refresh.flush();
      },
    }),
  });

  function disconnect() {
    ticker.disconnect();
    signals.disconnect();
    for (const entry of subscriptions.values()) entry.socket.disconnect();
    refresh.cancel();
  }

  return {
    connect() {
      if (disposed) return;
      ticker.connect();
      signals.connect();
      for (const entry of subscriptions.values()) entry.socket.connect();
    },
    disconnect,
    subscribe(type: 'ticker' | 'kline' | 'trade', symbol: string, interval = '1m') {
      if (disposed) return () => {};
      // The ticker endpoint already broadcasts every tracked symbol.
      if (type === 'ticker') {
        ticker.connect();
        return () => {};
      }
      const normalizedSymbol = symbol.trim().toUpperCase();
      if (!normalizedSymbol) return () => {};
      const endpoint = type === 'kline'
        ? `/kline/${encodeURIComponent(normalizedSymbol)}?interval=${encodeURIComponent(interval)}`
        : `/trades/${encodeURIComponent(normalizedSymbol)}`;
      let entry = subscriptions.get(endpoint);
      if (!entry) {
        entry = {
          count: 0,
          socket: createReconnectingSocket({
            url: () => `${options.baseUrl()}${endpoint}`,
            onMessage: (raw) => dispatchTickerSocketMessage(raw, tickerHandlers),
          }),
        };
        subscriptions.set(endpoint, entry);
      }
      entry.count++;
      entry.socket.connect();
      const subscription = entry;
      let released = false;
      return () => {
        if (released) return;
        released = true;
        if (--subscription.count === 0) {
          subscription.socket.dispose();
          subscriptions.delete(endpoint);
        }
      };
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      disconnect();
      ticker.dispose();
      signals.dispose();
      for (const entry of subscriptions.values()) entry.socket.dispose();
      subscriptions.clear();
    },
  };
}
