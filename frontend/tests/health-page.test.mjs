import assert from 'node:assert/strict';
import test from 'node:test';
import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { load, primitives } from './view-harness.mjs';

const healthStatus = load('../src/lib/health-status.ts');

function health(allowed, response = {}, connectionData = undefined, providerQuery = {}) {
  const queries = [], requests = [];
  const page = load('../src/app/health/page.tsx', { ...primitives,
    react: React,
    '@/lib/hooks/use-session': { useSession: () => allowed ? { user: { username: 'admin', is_admin: true }, expiresAt: 123 } : null },
    '@tanstack/react-query': { useQuery: options => {
      queries.push(options);
      if (options.queryKey[0] === 'health-provider-connection') return { data: connectionData, isError: false, ...providerQuery };
      return { data: [], ...response };
    } },
    '@/lib/api/client': { fetchLogs: n => requests.push(['logs', n]) },
    '@/lib/api/borsapy-api': { fetchResearchConnection: signal => requests.push(['connection', signal]) },
    '@/lib/health-status': healthStatus,
    '@/lib/hooks/use-health': { useApiHealth: () => ({ apiState: 'unknown', label: 'Bilinmiyor' }), useAlarmRuntimeHealth: () => ({ label: 'Doğrulanamadı', lastCycle: null, telegramConfigured: null }) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: () => null },
    '@/components/dashboard/bist-session-status': { BistSessionStatus: () => 'Seans kapalı' },
    '@/components/ui/input': { Input: 'input' },
  });
  return { html: renderToStaticMarkup(React.createElement(page.default)), queries, requests };
}

test('health exposes API, provider protection and user alarm runtime without any scan query or history', async () => {
  const h = health(true, {}, {
    authenticated: true, state: 'authenticated',
    provider_protection: { blocked: false, reason: null, requests_admitted: 42, budget_waits: 1, requests_per_second: 4, burst: 4, auth_minimum_seconds: 300 },
  });
  assert.match(h.html, /Sunucu alarm motoru/); assert.match(h.html, /Telegram yalnız kendi alarmınızda/);
  assert.match(h.html, /Hesap koruması engelsiz/); assert.match(h.html, /4 iş\/sn/);
  assert.doesNotMatch(h.html, /Tarama geçmişi|Tarama arşivi|COMBO|HUNTER|Sinyal/);
  assert.deepEqual(h.queries.map(q => Array.from(q.queryKey)), [['logs', 'admin', 123], ['health-provider-connection', 'admin', 123]]);
  await h.queries[0].queryFn();
  const signal = new AbortController().signal;
  await h.queries[1].queryFn({ signal });
  assert.deepEqual(h.requests, [['logs', 120], ['connection', signal]]);
  assert.ok(h.queries.every(q => q.refetchIntervalInBackground === false));
});

test('anonymous health hides previously cached private log rows and disables queries', () => {
  const h = health(false, { data: [{ id: 1, message: 'PRIVATE_SENTINEL', timestamp: 'now', level: 'INFO' }] });
  assert.ok(h.queries.every(q => q.enabled === false));
  assert.doesNotMatch(h.html, /PRIVATE_SENTINEL/); assert.match(h.html, /Giriş yap/);
  assert.deepEqual(h.requests, []);
});

test('a provider refresh failure labels the last successful report and does not show an unconfirmed healthy badge', () => {
  const measuredAt = '2026-11-28T08:00:00.000Z';
  const h = health(true, {}, { authenticated: true }, { isError: true, dataUpdatedAt: Date.parse(measuredAt) });
  assert.match(h.html, /Yenileme başarısız/);
  assert.match(h.html, /Son alınan sağlayıcı durumu <time dateTime="2026-11-28T08:00:00.000Z">/);
  assert.match(h.html, /son başarılı sorgudan gösteriliyor/);
  assert.doesNotMatch(h.html, /Hesap koruması engelsiz/);
  assert.match(health(true, {}, undefined, { isError: true }).html, /Son alınan sağlayıcı durumu Henüz yok/);
});
