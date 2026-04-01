function normalizeBaseUrl(rawValue: string | undefined, fallback: string): string {
    const value = rawValue?.trim();
    if (!value) return fallback;
    return value.length > 1 && value.endsWith('/') ? value.slice(0, -1) : value;
}

export const API_BASE_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL, '/api');
export const HEALTH_API_URL = normalizeBaseUrl(process.env.NEXT_PUBLIC_HEALTH_API_URL, '/health-api');

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
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
    });

    if (!response.ok) {
        throw new ApiError(
            `API error: ${response.statusText}`,
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
