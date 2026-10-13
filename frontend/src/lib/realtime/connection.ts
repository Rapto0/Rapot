import { dispatchTickerSocketMessage } from './message-parser';
import type { useRealtimeStore } from './store';
import type { BISTStock, ConnectionState, KlineData, TickerData, TradeData } from './types';

interface SocketOptions {
  url: () => string;
  onMessage: (data: string) => void;
  onOpen?: () => void;
  onState?: (state: ConnectionState) => void;
  getToken?: () => string | null;
  onAuthFailure?: () => void;
}

/** Own one socket and its retries; retired sockets can never change current state. */
export function createReconnectingSocket(options: SocketOptions) {
  let socket: WebSocket | null = null;
  let retry: ReturnType<typeof setTimeout> | null = null;
  let attempts = 0;
  let enabled = false;
  let disposed = false;
  let authTimeout: ReturnType<typeof setTimeout> | null = null;

  function retire() {
    if (authTimeout !== null) clearTimeout(authTimeout);
    authTimeout = null;
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
    const token = options.getToken?.();
    if (options.getToken && !token) { enabled = false; options.onState?.('disconnected'); return; }
    options.onState?.(attempts ? 'reconnecting' : 'connecting');
    try {
      const current = new WebSocket(options.url());
      socket = current;
      const isCurrent = () => enabled && !disposed && socket === current;
      let authenticated = !options.getToken;
      const ready = () => {
        attempts = 0;
        options.onState?.('connected');
        options.onOpen?.();
      };
      const deny = () => {
        enabled = false;
        retire();
        options.onState?.('disconnected');
        options.onAuthFailure?.();
      };
      current.onopen = () => {
        if (!isCurrent()) return;
        if (options.getToken) {
          current.send(JSON.stringify({ type: 'auth', token }));
          authTimeout = setTimeout(() => { if (isCurrent()) deny(); }, 5000);
        } else ready();
      };
      current.onmessage = (event) => {
        if (!isCurrent()) return;
        if (!authenticated) {
          try {
            if (JSON.parse(String(event.data)).type !== 'authenticated') return;
          } catch { return; }
          authenticated = true;
          if (authTimeout !== null) clearTimeout(authTimeout);
          authTimeout = null;
          ready();
          return;
        }
        options.onMessage(String(event.data));
      };
      current.onclose = (event) => {
        if (!isCurrent()) return;
        if (event.code === 4401 || event.code === 4403) { deny(); return; }
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

interface RealtimeConnectionOptions {
  baseUrl: () => string;
  getStore: typeof useRealtimeStore.getState;
  getToken?: () => string | null;
}

export function createRealtimeConnection(options: RealtimeConnectionOptions) {
  const subscriptions = new Map<string, { count: number; socket: ReturnType<typeof createReconnectingSocket> }>();
  let disposed = false;

  const tickerHandlers = {
    onInit: (payload: { crypto?: Record<string, unknown>; bist?: unknown }) => {
      if (payload.crypto) Object.values(payload.crypto).forEach((ticker) => options.getStore().updateTicker(ticker as TickerData));
      if (payload.bist) options.getStore().updateBistStocks(payload.bist as BISTStock[]);
    },
    onTicker: (ticker: TickerData) => options.getStore().updateTicker(ticker),
    onBist: (stocks: BISTStock[]) => options.getStore().updateBistStocks(stocks),
    onKline: (kline: KlineData) => options.getStore().updateKline(kline),
    onTrade: (trade: TradeData) => options.getStore().addTrade(trade),
  };
  const ticker = createReconnectingSocket({
    getToken: options.getToken,
    onAuthFailure: denyAll,
    url: () => `${options.baseUrl()}/ticker`,
    onState: (state) => options.getStore().setConnectionState(state),
    onMessage: (raw) => dispatchTickerSocketMessage(raw, tickerHandlers),
  });
  function disconnect() {
    ticker.disconnect();
    for (const entry of subscriptions.values()) entry.socket.disconnect();
  }

  function denyAll() {
    disposed = true;
    disconnect();
    options.getStore().resetPrivateData();
  }

  return {
    connect() {
      if (disposed) return;
      ticker.connect();
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
            getToken: options.getToken,
            onAuthFailure: denyAll,
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
      for (const entry of subscriptions.values()) entry.socket.dispose();
      subscriptions.clear();
    },
  };
}
