import { clearSession, getAccessToken } from '../auth/session';

function normalizeBaseUrl(rawValue: string | undefined, fallback: string): string {
    const value = rawValue?.trim();
    if (!value) return fallback;
    return value.length > 1 && value.endsWith('/') ? value.slice(0, -1) : value;
}

export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL, '/api');

function isCoreApiUrl(url: string): boolean {
    if (typeof window === 'undefined') return false;
    const base = new URL(API_BASE_URL, window.location.origin);
    const target = new URL(url, window.location.origin);
    const prefix = base.pathname.replace(/\/$/, '');
    return target.origin === base.origin && (
        target.pathname === prefix || target.pathname.startsWith(`${prefix}/`)
    );
}

export class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
        this.name = 'ApiError';
    }
}

export async function fetchApi<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const headers = new Headers(options.headers);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const coreApi = isCoreApiUrl(url);
    const token = coreApi ? getAccessToken() : null;
    if (coreApi && /\/(?:borsapy(?:\/|\?|$)|calendar(?:\?|$))/.test(new URL(url, window.location.origin).pathname) && !token) {
        throw new ApiError('Bu işlem için giriş yapın.', 401);
    }
    if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
    const response = await fetch(url, {
        ...options,
        headers,
        cache: options.cache ?? 'no-store',
    });

    if (!response.ok) {
        if (response.status === 401 && token && headers.get('Authorization') === `Bearer ${token}`) {
            clearSession(token);
        }
        let message = response.status === 401 ? 'Bu işlem için giriş yapın.'
            : response.status === 403 ? 'Bu işlem için yetkiniz bulunmuyor.'
                : response.status === 429 ? 'İstek sınırına ulaşıldı. Biraz sonra tekrar deneyin.'
                    : `API error: ${response.statusText}`;
        if (response.status === 422 && /\/advanced-alarms(?:\/|$)/.test(url)) {
            try {
                const payload: unknown = await response.json();
                if (payload && typeof payload === 'object' && 'detail' in payload && Array.isArray(payload.detail)) {
                    const messages = payload.detail.slice(0, 3).flatMap((item: unknown) => item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string' ? [item.msg.replace(/^Value error, /, '').slice(0, 300)] : []);
                    if (messages.length) message = messages.join(' ');
                }
            } catch { /* Keep the bounded HTTP status message if validation JSON is unavailable. */ }
        }
        throw new ApiError(
            message,
            response.status
        );
    }

    try {
        const payload: unknown = await response.json();
        return payload as T;
    } catch {
        throw new ApiError('Invalid JSON response', response.status);
    }
}
