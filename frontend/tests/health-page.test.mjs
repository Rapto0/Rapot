import assert from 'node:assert/strict';
import test from 'node:test';
import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { load, primitives } from './view-harness.mjs';

function health(allowed, response = {}) {
  const queries = [], requests = [];
  const page = load('../src/app/health/page.tsx', { ...primitives,
    '@/lib/hooks/use-session': { useSession: () => allowed ? { user: { username: 'admin', is_admin: true }, expiresAt: 123 } : null },
    '@tanstack/react-query': { useQuery: options => { queries.push(options); return { data: [], ...response }; } },
    '@/lib/api/client': { fetchLogs: n => requests.push(n) },
    '@/lib/hooks/use-health': { useApiHealth: () => ({ apiState: 'unknown', label: 'Bilinmiyor' }), useAlarmRuntimeHealth: () => ({ label: 'Doğrulanamadı', lastCycle: null, telegramConfigured: null }) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: () => null },
  });
  return { html: renderToStaticMarkup(React.createElement(page.default)), queries, requests };
}

test('health exposes API and user alarm runtime without any scan query or history', async () => {
  const h = health(true);
  assert.match(h.html, /Sunucu alarm motoru/); assert.match(h.html, /Telegram yalnız kendi alarmınızda/);
  assert.doesNotMatch(h.html, /Tarama geçmişi|Tarama arşivi|COMBO|HUNTER|Sinyal/);
  assert.deepEqual(h.queries.map(q => Array.from(q.queryKey)), [['logs', 'admin', 123]]);
  await h.queries[0].queryFn(); assert.deepEqual(h.requests, [60]);
  assert.equal(h.queries[0].refetchIntervalInBackground, false);
});

test('anonymous health hides previously cached private log rows and disables queries', () => {
  const h = health(false, { data: [{ id: 1, message: 'PRIVATE_SENTINEL', timestamp: 'now', level: 'INFO' }] });
  assert.ok(h.queries.every(q => q.enabled === false));
  assert.doesNotMatch(h.html, /PRIVATE_SENTINEL/); assert.match(h.html, /Giriş yap/);
  assert.deepEqual(h.requests, []);
});
