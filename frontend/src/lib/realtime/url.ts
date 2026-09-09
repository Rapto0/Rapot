/** Keep WebSockets on the same proxy path as HTTP when the API URL is relative. */
export function resolveRealtimeWsBaseUrl(
  origin: string,
  apiUrl = '/api',
  explicitWsUrl?: string,
): string {
  if (explicitWsUrl?.trim()) {
    return `${explicitWsUrl.trim().replace(/\/$/, '')}/realtime/ws`;
  }

  let target: URL;
  try {
    target = new URL(apiUrl.trim() || '/api', origin);
    if (!['http:', 'https:'].includes(target.protocol)) throw new Error('Invalid API protocol');
  } catch {
    target = new URL('/api', origin);
  }
  const protocol = target.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${target.host}${target.pathname.replace(/\/$/, '')}/realtime/ws`;
}
