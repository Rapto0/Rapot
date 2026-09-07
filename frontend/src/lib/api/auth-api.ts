import { setSession, type AuthUser } from '../auth/session';
import { API_BASE_URL, ApiError, fetchApi } from './core';

interface TokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export async function signIn(username: string, password: string): Promise<void> {
    const token = await fetchApi<TokenResponse>(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        body: JSON.stringify({ username, password }),
    });
    if (!token.access_token || !Number.isFinite(token.expires_in) || token.expires_in <= 0) {
        throw new ApiError('Geçersiz oturum yanıtı.', 502);
    }
    const user = await fetchApi<AuthUser>(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token.access_token}` },
    });
    if (user.disabled) throw new ApiError('Kullanıcı devre dışı.', 403);
    setSession({ accessToken: token.access_token, expiresAt: Date.now() + token.expires_in * 1000, user });
}
