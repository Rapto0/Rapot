import {
    clearSession,
    getAccessToken,
    getSessionGeneration,
    hasActiveSession,
} from '../auth/session';

function normalizeBaseUrl(rawValue: string | undefined, fallback: string): string {
    const value = rawValue?.trim();
    if (!value) return fallback;
    return value.length > 1 && value.endsWith('/') ? value.slice(0, -1) : value;
}

export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL, '/api');

const CSRF_COOKIE_NAME = 'rapot_csrf';
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

function isCoreApiUrl(url: string): boolean {
    if (typeof window === 'undefined') return false;
    const base = new URL(API_BASE_URL, window.location.origin);
    const target = new URL(url, window.location.origin);
    const prefix = base.pathname.replace(/\/$/, '');
    return target.origin === base.origin && (
        target.pathname === prefix || target.pathname.startsWith(`${prefix}/`)
    );
}

function readBrowserCookie(name: string): string | null {
    if (typeof document === 'undefined' || typeof document.cookie !== 'string') return null;
    for (const part of document.cookie.split(';')) {
        const trimmed = part.trim();
        if (!trimmed) continue;
        const eq = trimmed.indexOf('=');
        if (eq <= 0) continue;
        const key = trimmed.slice(0, eq).trim();
        if (key === name) {
            const raw = trimmed.slice(eq + 1).trim();
            try {
                return decodeURIComponent(raw);
            } catch {
                return raw;
            }
        }
    }
    return null;
}

export class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.status = status;
        this.name = 'ApiError';
    }
}

export const DEFAULT_API_TIMEOUT_MS = 30_000;

const DETAIL_STATUSES = new Set([400, 404, 409, 422, 502, 503]);

function extractDetailMessage(payload: unknown): string | null {
    if (!payload || typeof payload !== 'object' || !('detail' in payload)) return null;
    const detail = payload.detail;
    if (typeof detail === 'string') {
        const cleaned = detail.trim().replace(/^Value error, /, '');
        if (!cleaned || cleaned.includes('\n')) return null;
        return cleaned.slice(0, 300);
    }
    if (Array.isArray(detail)) {
        const messages = detail.slice(0, 3).flatMap((item: unknown) =>
            item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string'
                ? [item.msg.trim().replace(/^Value error, /, '').slice(0, 300)]
                : []
        ).filter(Boolean);
        return messages.length ? messages.join(' ') : null;
    }
    return null;
}

export async function fetchApi<T>(
    url: string,
    options: RequestInit = {}
): Promise<T> {
    const headers = new Headers(options.headers);
    if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const coreApi = isCoreApiUrl(url);
    const activeSession = coreApi ? hasActiveSession() : false;
    const token = coreApi ? getAccessToken() : null;
    const generation = coreApi ? getSessionGeneration() : null;
    if (
        coreApi
        && /\/(?:borsapy(?:\/|\?|$)|calendar(?:\?|$))/.test(new URL(url, window.location.origin).pathname)
        && !activeSession
        && !headers.has('Authorization')
    ) {
        throw new ApiError('Bu işlem için giriş yapın.', 401);
    }
    if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);

    const method = (options.method ?? 'GET').toUpperCase();
    if (coreApi && !headers.has('Authorization') && MUTATING_METHODS.has(method) && !headers.has('X-CSRF-Token')) {
        const csrfToken = readBrowserCookie(CSRF_COOKIE_NAME);
        if (csrfToken) headers.set('X-CSRF-Token', csrfToken);
    }

    let controller: AbortController | null = null;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let timedOut = false;
    let signal = options.signal;
    if (!signal && typeof AbortController === 'function') {
        controller = new AbortController();
        signal = controller.signal;
        timeoutId = setTimeout(() => {
            timedOut = true;
            controller?.abort();
        }, DEFAULT_API_TIMEOUT_MS);
    }

    let response: Response;
    try {
        response = await fetch(url, {
            ...options,
            headers,
            signal,
            credentials: options.credentials ?? (coreApi ? 'same-origin' : undefined),
            cache: options.cache ?? 'no-store',
        });
    } catch (error) {
        if (timedOut) {
            throw new ApiError('İstek zaman aşımına uğradı. Lütfen tekrar deneyin.', 408);
        }
        throw error;
    } finally {
        if (timeoutId !== null) clearTimeout(timeoutId);
    }

    if (!response.ok) {
        if (response.status === 401) {
            if (token && headers.get('Authorization') === `Bearer ${token}`) {
                clearSession(token);
            } else if (coreApi && activeSession && generation !== null && !headers.has('Authorization')) {
                clearSession(generation);
            }
        }
        let message = response.status === 401 ? 'Bu işlem için giriş yapın.'
            : response.status === 403 ? 'Bu işlem için yetkiniz bulunmuyor.'
                : response.status === 429 ? 'İstek sınırına ulaşıldı. Biraz sonra tekrar deneyin.'
                    : `API error: ${response.statusText}`;
        if (DETAIL_STATUSES.has(response.status)) {
            try {
                const payload: unknown = await response.json();
                const detail = extractDetailMessage(payload);
                if (detail) message = detail;
            } catch { /* Keep the bounded HTTP status message if JSON detail is unavailable. */ }
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
