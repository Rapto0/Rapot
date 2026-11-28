export interface AuthUser {
    username: string;
    is_admin: boolean;
    disabled: boolean;
}

export interface AuthSession {
    accessToken?: string;
    expiresAt: number;
    user: AuthUser;
}

// Session metadata lives only in memory; the actual browser session credential is an HttpOnly cookie.
let session: AuthSession | null = null;
let sessionGeneration = 0;
let sessionChecked = false;
let expiryTimer: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();

export function getSession(): AuthSession | null {
    return session;
}

export function getSessionGeneration(): number {
    return sessionGeneration;
}

export function getSessionChecked(): boolean {
    return sessionChecked;
}

export function markSessionChecked(): void {
    if (sessionChecked) return;
    sessionChecked = true;
    listeners.forEach((listener) => listener());
}

export function subscribeSession(listener: () => void): () => void {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
}

export function setSession(next: AuthSession | null): void {
    if (expiryTimer !== undefined) clearTimeout(expiryTimer);
    expiryTimer = undefined;
    sessionGeneration += 1;
    sessionChecked = true;
    session = next && next.expiresAt > Date.now() ? next : null;
    if (session) {
        expiryTimer = setTimeout(() => setSession(null), session.expiresAt - Date.now());
    }
    listeners.forEach((listener) => listener());
}

export function clearSession(expected?: string | number): void {
    // An old request's 401 must not sign out a newer login.
    if (typeof expected === 'string' && session?.accessToken !== expected) return;
    if (typeof expected === 'number' && sessionGeneration !== expected) return;
    setSession(null);
}

export function hasActiveSession(): boolean {
    if (session && session.expiresAt <= Date.now()) {
        clearSession();
        return false;
    }
    return session !== null;
}

export function getAccessToken(): string | null {
    if (session && session.expiresAt <= Date.now()) clearSession();
    return session?.accessToken ?? null;
}
