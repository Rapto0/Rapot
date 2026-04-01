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

export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'error';
