import { API_BASE_URL, fetchApi } from './core';
import type { Candle, CandlesResponse, VolumeQuality } from './types';

export const BORSAPY_INTERVALS = new Set(['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1wk', '1mo']);

export interface BorsapyChartSnapshot {
    state: string;
    message: string;
    candles: Array<{ time?: number; timestamp?: number; open: number; high: number; low: number; close: number; volume?: number | null }>;
    volume_quality?: VolumeQuality;
    quote: { timestamp?: number; last?: number } | null;
    received_at?: string | null;
}

export function fetchBorsapyCandles(symbol: string, interval: string, signal?: AbortSignal): Promise<CandlesResponse> {
    return fetchApi(`${API_BASE_URL}/borsapy/candles/${encodeURIComponent(symbol)}?${new URLSearchParams({ interval, limit: '1000' })}`, { signal });
}

export function fetchBorsapyChartSnapshot(symbol: string, interval: string, signal?: AbortSignal, subscriberId?: string): Promise<BorsapyChartSnapshot> {
    const params = new URLSearchParams({ symbol, interval });
    if (subscriberId) params.set('subscriber_id', subscriberId);
    return fetchApi(`${API_BASE_URL}/borsapy/stream?${params}`, { signal });
}

export function releaseBorsapyChart(symbol: string, interval: string, subscriberId: string): Promise<{ closed: boolean }> {
    return fetchApi(`${API_BASE_URL}/borsapy/stream?${new URLSearchParams({ symbol, interval, subscriber_id: subscriberId })}`, { method: 'DELETE' });
}

/** Live volume cannot certify older history; show the strongest known limitation. */
export function borsapyVolumeWarning(...qualities: Array<VolumeQuality | undefined>): string | null {
    const missing = qualities.filter(quality => quality && !quality.verified);
    return (missing.find(quality => quality?.state === 'unavailable') ?? missing[0])?.message ?? null;
}

/** Only merge the matching query's stream into a successfully loaded history. */
export function mergeBorsapyCandles(history: Candle[], updates: BorsapyChartSnapshot['candles']): Candle[] {
    const byTime = new Map<number, Candle>();
    for (const candle of history) {
        const time = Date.parse(candle.time);
        if (Number.isFinite(time)) byTime.set(time, candle);
    }
    for (const candle of updates) {
        const seconds = candle.time ?? candle.timestamp;
        if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0 || seconds > 32_503_680_000) continue;
        const { open, high, low, close } = candle;
        const volume = candle.volume ?? null;
        if (![open, high, low, close].every(Number.isFinite)
            || (volume !== null && (!Number.isFinite(volume) || volume < 0 || volume >= 1e99)) || low <= 0
            || high < Math.max(open, low, close) || low > Math.min(open, high, close)) continue;
        const time = seconds * 1000;
        byTime.set(time, { time: new Date(time).toISOString(), open, high, low, close, volume });
    }
    return [...byTime.entries()].sort((left, right) => left[0] - right[0]).slice(-2000).map(([, candle]) => candle);
}
