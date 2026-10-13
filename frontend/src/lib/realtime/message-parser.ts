import type { BISTStock, KlineData, TickerData, TradeData } from './types';

interface TickerMessageHandlers {
  onInit: (payload: { crypto?: Record<string, unknown>; bist?: unknown }) => void;
  onTicker: (ticker: TickerData) => void;
  onBist: (stocks: BISTStock[]) => void;
  onKline: (kline: KlineData) => void;
  onTrade: (trade: TradeData) => void;
  onUnknownType?: (type: string) => void;
  onParseError?: (error: unknown) => void;
}

function parseTicker(data: unknown): TickerData | null {
  if (!data || typeof data !== 'object') return null;
  const ticker = data as Record<string, unknown>;
  if (typeof ticker.symbol !== 'string' || !ticker.symbol ||
      typeof ticker.price !== 'number' || !Number.isFinite(ticker.price) || ticker.price <= 0) return null;
  const finiteOrNull = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null;
  return { ...ticker,
    priceChange: finiteOrNull(ticker.priceChange),
    priceChangePercent: finiteOrNull(ticker.priceChangePercent),
  } as unknown as TickerData;
}

function parseSocketMessage(data: string): Record<string, unknown> {
  const parsed = JSON.parse(data) as unknown;
  if (!parsed || typeof parsed !== 'object') {
    throw new Error('Invalid websocket payload');
  }
  return parsed as Record<string, unknown>;
}

export function dispatchTickerSocketMessage(
  rawData: string,
  handlers: TickerMessageHandlers
): void {
  try {
    const message = parseSocketMessage(rawData);
    const messageType = String(message.type ?? '');

    switch (messageType) {
      case 'init': {
        const crypto: Record<string, TickerData> = {};
        if (message.crypto && typeof message.crypto === 'object') {
          for (const value of Object.values(message.crypto)) {
            const ticker = parseTicker(value);
            if (ticker) crypto[ticker.symbol] = ticker;
          }
        }
        handlers.onInit({
          crypto,
          bist: message.bist,
        });
        break;
      }
      case 'ticker': {
        const ticker = parseTicker(message.data);
        if (ticker) handlers.onTicker(ticker);
        break;
      }
      case 'bist':
        handlers.onBist(message.data as BISTStock[]);
        break;
      case 'kline':
        handlers.onKline(message.data as KlineData);
        break;
      case 'trade':
        handlers.onTrade(message.data as TradeData);
        break;
      case 'heartbeat':
        break;
      default:
        handlers.onUnknownType?.(messageType);
        break;
    }
  } catch (error) {
    handlers.onParseError?.(error);
  }
}
