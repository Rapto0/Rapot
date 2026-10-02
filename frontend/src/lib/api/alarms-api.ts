import { API_BASE_URL, fetchApi } from './core';

export type ServerAlarmIndicator = 'rsi' | 'wr' | 'combo' | 'hunter';
export type ServerAlarmTimeframe = '1h' | '4h' | '1d';
export type ServerAlarmSide = 'dip' | 'top';
export interface ServerAlarmSymbol { symbol: string; market_type: 'BIST' | 'Kripto' }

export interface AlarmWrite {
    name: string;
    symbols: ServerAlarmSymbol[];
    indicator: ServerAlarmIndicator;
    timeframe: ServerAlarmTimeframe;
    side: ServerAlarmSide;
    threshold: number;
    mode: 'on_enter' | 'once_per_bar';
    enabled: boolean;
    notify_telegram: boolean;
}

export interface ServerAlarmRule extends AlarmWrite {
    id: string;
    created_at: string;
    updated_at: string;
    last_checked_at: string | null;
    last_error: string | null;
    last_triggered_at: string | null;
    state: 'pending' | 'active' | 'error' | 'paused';
}

export interface ServerAlarmList {
    rules: ServerAlarmRule[];
    runtime: {
        running: boolean;
        last_cycle_at: string | null;
        last_cycle_error?: string | null;
        telegram_configured: boolean;
        poll_interval_seconds: number;
    };
    limits: { max_rules: number; max_symbols_per_rule: number; max_subscriptions: number };
}

export interface ServerAlarmEvent {
    id: number;
    rule_id: string;
    rule_name: string;
    symbol: string;
    market_type: 'BIST' | 'Kripto';
    indicator: ServerAlarmIndicator;
    timeframe: ServerAlarmTimeframe;
    side: ServerAlarmSide;
    value: number;
    bar_time: string;
    created_at: string;
    delivery_status: 'not_requested' | 'pending' | 'sent' | 'failed';
    delivery_error: string | null;
}

export function fetchServerAlarms(signal?: AbortSignal): Promise<ServerAlarmList> {
    return fetchApi(`${API_BASE_URL}/alarms`, { signal });
}

export function fetchServerAlarmEvents(signal?: AbortSignal): Promise<{ events: ServerAlarmEvent[] }> {
    return fetchApi(`${API_BASE_URL}/alarms/events?limit=100`, { signal });
}

export function createServerAlarm(rule: AlarmWrite): Promise<ServerAlarmRule> {
    return fetchApi(`${API_BASE_URL}/alarms`, { method: 'POST', body: JSON.stringify(rule) });
}

export function updateServerAlarm(id: string, rule: AlarmWrite): Promise<ServerAlarmRule> {
    return fetchApi(`${API_BASE_URL}/alarms/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(rule) });
}

export function deleteServerAlarm(id: string): Promise<unknown> {
    return fetchApi(`${API_BASE_URL}/alarms/${encodeURIComponent(id)}`, { method: 'DELETE' });
}
