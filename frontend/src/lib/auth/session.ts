export interface AuthUser {
    username: string;
    is_admin: boolean;
    disabled: boolean;
}

export interface AuthSession {
    accessToken: string;
    expiresAt: number;
    user: AuthUser;
}

// Credentials live only in this tab's memory, never in browser storage.
let session: AuthSession | null = null;
let expiryTimer: ReturnType<typeof setTimeout> | undefined;
const listeners = new Set<() => void>();

export function getSession(): AuthSession | null {
    return session;
}

export function subscribeSession(listener: () => void): () => void {
    listeners.add(listener);
    return () => { listeners.delete(listener); };
}

export function setSession(next: AuthSession | null): void {
    if (expiryTimer !== undefined) clearTimeout(expiryTimer);
    expiryTimer = undefined;
    session = next && next.expiresAt > Date.now() ? next : null;
    if (session) {
        expiryTimer = setTimeout(() => setSession(null), session.expiresAt - Date.now());
    }
    listeners.forEach((listener) => listener());
}

export function clearSession(expectedToken?: string): void {
    // An old request's 401 must not sign out a newer login.
    if (expectedToken !== undefined && session?.accessToken !== expectedToken) return;
    setSession(null);
}

export function getAccessToken(): string | null {
    if (session && session.expiresAt <= Date.now()) clearSession();
    return session?.accessToken ?? null;
}
