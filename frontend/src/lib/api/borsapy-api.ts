import { API_BASE_URL, fetchApi } from './core';

export interface ResearchField {
    name: string;
    label: string;
    type: 'text' | 'number' | 'select' | 'date' | 'textarea';
    default?: unknown;
    options?: { value: string; label: string }[];
    required?: boolean;
    min?: number;
    max?: number;
}
export interface ResearchOperation {
    id: string;
    group: string;
    label: string;
    description: string;
    source: string;
    fields: ResearchField[];
    requires?: string[];
    view: 'table' | 'chart' | 'replay' | 'portfolio' | 'backtest' | 'stream';
    transport?: 'query' | 'stream';
}
export interface ResearchCatalog {
    version: string | number;
    groups: { id: string; label: string; description: string }[];
    operations: ResearchOperation[];
}
export interface ResearchTable {
    name: string;
    columns: string[];
    rows: Record<string, unknown>[];
    total_rows: number;
    truncated: boolean;
}
export interface ResearchCandle { time: number; open: number; high: number; low: number; close: number; volume?: number }
export interface ResearchResult {
    operation: string;
    source: string;
    as_of: string;
    tables: ResearchTable[];
    summary: Record<string, unknown>;
    warnings: string[];
    candles?: ResearchCandle[];
}
export interface ResearchConnection {
    installed: boolean;
    version: string | null;
    configured: boolean;
    authenticated: boolean;
    evds_configured: boolean;
    twitter_configured: boolean;
    state: string;
    message: string;
}
export interface ResearchSecrets { session?: string; session_sign?: string; evds_key?: string; twitter_auth_token?: string; twitter_ct0?: string }
export interface ResearchStream {
    state: string;
    message: string;
    quote: Record<string, unknown> | null;
    candles: ResearchCandle[];
    study: Record<string, unknown> | null;
    source: string;
    received_at: string | null;
    realtime_verified: boolean;
}

export const fetchResearchCatalog = (signal?: AbortSignal): Promise<ResearchCatalog> =>
    fetchApi(`${API_BASE_URL}/borsapy/catalog`, { signal });
export const runResearchQuery = (operation: string, params: Record<string, unknown>, signal?: AbortSignal): Promise<ResearchResult> =>
    fetchApi(`${API_BASE_URL}/borsapy/query`, { method: 'POST', body: JSON.stringify({ operation, params }), signal });
export const fetchResearchConnection = (signal?: AbortSignal): Promise<ResearchConnection> =>
    fetchApi(`${API_BASE_URL}/borsapy/connection`, { signal });
export const saveResearchConnection = (secrets: ResearchSecrets, signal?: AbortSignal): Promise<ResearchConnection> =>
    fetchApi(`${API_BASE_URL}/borsapy/connection`, { method: 'POST', body: JSON.stringify(secrets), signal });
export const verifyResearchConnection = (signal?: AbortSignal): Promise<ResearchConnection> =>
    fetchApi(`${API_BASE_URL}/borsapy/connection/verify`, { method: 'POST', signal });
export const clearResearchConnection = (signal?: AbortSignal): Promise<unknown> =>
    fetchApi(`${API_BASE_URL}/borsapy/connection`, { method: 'DELETE', signal });
export interface ResearchSubscription { symbol: string; interval: string; study?: string; studyInputs?: Record<string, string | number | boolean>; subscriberId: string }
function streamParams(subscription: ResearchSubscription): URLSearchParams {
    const params = new URLSearchParams({ symbol: subscription.symbol, interval: subscription.interval, subscriber_id: subscription.subscriberId });
    if (subscription.study) params.set('study', subscription.study);
    if (subscription.studyInputs && Object.keys(subscription.studyInputs).length) params.set('study_inputs', JSON.stringify(subscription.studyInputs));
    return params;
}
export function fetchResearchStream(subscription: ResearchSubscription, signal?: AbortSignal): Promise<ResearchStream> {
    const params = streamParams(subscription);
    return fetchApi(`${API_BASE_URL}/borsapy/stream?${params}`, { signal });
}
export const stopResearchStream = (subscription: ResearchSubscription): Promise<unknown> =>
    fetchApi(`${API_BASE_URL}/borsapy/stream?${streamParams(subscription)}`, { method: 'DELETE' });

export interface SavedResearch { id: string; name: string; operation: string; params: Record<string, unknown>; updated_at: string }
export const fetchSavedResearch = (signal?: AbortSignal): Promise<SavedResearch[]> =>
    fetchApi(`${API_BASE_URL}/borsapy/saved`, { signal });
export const saveResearch = (name: string, operation: string, params: Record<string, unknown>, signal?: AbortSignal): Promise<SavedResearch> =>
    fetchApi(`${API_BASE_URL}/borsapy/saved`, { method: 'POST', body: JSON.stringify({ name, operation, params }), signal });
export const deleteSavedResearch = (id: string, signal?: AbortSignal): Promise<unknown> =>
    fetchApi(`${API_BASE_URL}/borsapy/saved/${encodeURIComponent(id)}`, { method: 'DELETE', signal });
