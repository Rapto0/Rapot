import type { BISTStock, KlineData, SignalData, TickerData, TradeData } from './types';

interface TickerMessageHandlers {
  onInit: (payload: { crypto?: Record<string, unknown>; bist?: unknown }) => void;
  onTicker: (ticker: TickerData) => void;
  onBist: (stocks: BISTStock[]) => void;
  onKline: (kline: KlineData) => void;
  onTrade: (trade: TradeData) => void;
  onSignal: (signal: SignalData) => void;
  onUnknownType?: (type: string) => void;
  onParseError?: (error: unknown) => void;
}

interface SignalMessageHandlers {
  onSignal: (signal: SignalData) => void;
  onParseError?: (error: unknown) => void;
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
      case 'init':
        handlers.onInit({
          crypto: (message.crypto as Record<string, unknown> | undefined) ?? undefined,
          bist: message.bist,
        });
        break;
      case 'ticker':
        handlers.onTicker(message.data as TickerData);
        break;
      case 'bist':
        handlers.onBist(message.data as BISTStock[]);
        break;
      case 'kline':
        handlers.onKline(message.data as KlineData);
        break;
      case 'trade':
        handlers.onTrade(message.data as TradeData);
        break;
      case 'signal':
        handlers.onSignal(message.data as SignalData);
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

export function dispatchSignalSocketMessage(
  rawData: string,
  handlers: SignalMessageHandlers
): void {
  try {
    const message = parseSocketMessage(rawData);
    if (message.type === 'signal') {
      handlers.onSignal(message.data as SignalData);
    }
  } catch (error) {
    handlers.onParseError?.(error);
  }
}
