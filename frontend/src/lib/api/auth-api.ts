import {
    clearSession,
    getSessionGeneration,
    markSessionChecked,
    setSession,
    type AuthUser,
} from '../auth/session';
import { API_BASE_URL, ApiError, fetchApi } from './core';

const SESSION_CHECK_TIMEOUT_MS = 8_000;

interface SessionStatusResponse {
    authenticated: boolean;
    user?: AuthUser | null;
    expires_in?: number | null;
    expires_at?: number | null;
}

interface WsTicketResponse {
    ticket: string;
    expires_in: number;
}

export async function signIn(username: string, password: string): Promise<void> {
    const result = await fetchApi<SessionStatusResponse>(`${API_BASE_URL}/auth/session`, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    if (
        !result.authenticated
        || !result.user
        || !Number.isFinite(result.expires_in)
        || (result.expires_in ?? 0) <= 0
    ) {
        throw new ApiError('Geçersiz oturum yanıtı.', 502);
    }
    if (result.user.disabled) throw new ApiError('Kullanıcı devre dışı.', 403);
    setSession({
        expiresAt: Date.now() + (result.expires_in as number) * 1000,
        user: result.user,
    });
}

export async function hydrateSession(): Promise<boolean> {
    const generationBefore = getSessionGeneration();
    try {
        const result = await fetchApi<SessionStatusResponse>(`${API_BASE_URL}/auth/session`, { timeoutMs: SESSION_CHECK_TIMEOUT_MS });
        if (getSessionGeneration() !== generationBefore) {
            return false;
        }
        if (
            result.authenticated
            && result.user
            && !result.user.disabled
            && Number.isFinite(result.expires_in)
            && (result.expires_in ?? 0) > 0
        ) {
            setSession({
                expiresAt: Date.now() + (result.expires_in as number) * 1000,
                user: result.user,
            });
            return true;
        }
        return false;
    } catch {
        return false;
    } finally {
        markSessionChecked();
    }
}

export async function signOut(): Promise<void> {
    try {
        await fetchApi(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
    } catch {
        // Always drop local session state even if the network request fails.
    } finally {
        clearSession();
    }
}

export async function fetchWsTicket(): Promise<string | null> {
    try {
        const response = await fetchApi<WsTicketResponse>(`${API_BASE_URL}/auth/ws-ticket`, {
            method: 'POST',
        });
        return typeof response.ticket === 'string' && response.ticket ? response.ticket : null;
    } catch {
        return null;
    }
}
