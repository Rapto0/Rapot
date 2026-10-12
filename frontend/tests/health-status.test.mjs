import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function load(relativePath, imports = {}, suffix = '') {
  const compiled = ts.transpileModule(readFileSync(new URL(relativePath, import.meta.url), 'utf8') + suffix, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({ exports: {}, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(compiled, context);
  return context.exports;
}

const healthModel = load('../src/lib/health-status.ts');
const { deriveApiHealth, deriveAlarmRuntime } = healthModel;
const now = Date.parse('2026-10-12T12:00:00Z');
const api = { status: 'healthy', database: 'connected', realtime: 'running', uptime_seconds: 3600, uptime_human: '1h', timestamp: '2026-10-12T12:00:00Z' };
const runtime = { running: true, last_cycle_at: '2026-10-12T11:59:59Z', last_error: null, telegram_configured: true, delivery: { pending: 0 } };
const query = { data: api, isLoading: false, isError: false, isFetching: false, isStale: false };
const admin = { user: { username: 'admin', is_admin: true, disabled: false }, expiresAt: 1000 };

test('only explicit current API database and realtime health imply a connection', () => {
  assert.equal(deriveApiHealth(query).apiState, 'connected');
  assert.equal(deriveApiHealth(query).uptime, '1h');
  for (const data of [undefined, {}, { ...api, status: 'unhealthy' }, { ...api, database: 'error' }, { ...api, realtime: undefined }, { ...api, realtime: 'error' }]) {
    assert.equal(deriveApiHealth({ ...query, data }).apiState, 'unknown');
    assert.equal(deriveApiHealth({ ...query, data }).uptime, '—');
  }
});

test('failed, stale or in-progress refresh never shows an older API response as connected', () => {
  for (const flags of [{ isError: true }, { isStale: true }, { isFetching: true }, { isLoading: true }]) {
    const health = deriveApiHealth({ ...query, ...flags });
    assert.notEqual(health.apiState, 'connected');
    assert.notEqual(health.tone, 'profit');
    assert.equal(health.uptime, '—');
  }
});

test('alarm health requires a recent completed cycle and does not infer market freshness', () => {
  const active = deriveAlarmRuntime({ ...query, data: runtime }, now);
  assert.equal(active.state, 'running');
  assert.equal(active.pendingDeliveries, 0);
  assert.equal(active.telegramConfigured, true);
  for (const data of [undefined, {}, { ...runtime, running: 'true' }, { ...runtime, last_cycle_at: 'bad' },
    { ...runtime, last_cycle_at: '2026-10-12T11:59:29Z' }, { ...runtime, last_cycle_at: '2026-10-12T12:00:06Z' }]) {
    assert.equal(deriveAlarmRuntime({ ...query, data }, now).state, 'unknown');
  }
  assert.equal(deriveAlarmRuntime({ ...query, data: { ...runtime, running: false } }, now).state, 'stopped');
  assert.equal(deriveAlarmRuntime({ ...query, data: { ...runtime, last_cycle_at: null } }, now).state, 'starting');
});

test('alarm errors and API health remain independent; stale runtime counts are hidden', () => {
  assert.equal(deriveApiHealth(query).apiState, 'connected');
  const failed = deriveAlarmRuntime({ ...query, data: { ...runtime, last_error: 'synthetic private failure' } }, now);
  assert.equal(failed.label, 'Kontrol hatası');
  assert.ok(!JSON.stringify(failed).includes('synthetic private'));
  for (const flags of [{ isError: true }, { isStale: true }, { isFetching: true }]) {
    const health = deriveAlarmRuntime({ ...query, data: runtime, ...flags }, now);
    assert.notEqual(health.state, 'running');
    assert.equal(health.pendingDeliveries, null);
    assert.equal(health.telegramConfigured, null);
  }
});

test('health hooks are session scoped and disabled for anonymous or non-admin users', async () => {
  let session = null;
  let options;
  const requests = [];
  const hooks = load('../src/lib/hooks/use-health.ts', {
    '@tanstack/react-query': { useQuery: value => { options = value; return query; } },
    '@/lib/api/client': { fetchHealth: signal => requests.push(['health', signal]) },
    '@/lib/api/advanced-alarms-api': { fetchAdvancedAlarmStatus: signal => requests.push(['alarm', signal]) },
    '@/lib/health-status': healthModel,
    './use-session': { useSession: () => session },
  });
  for (const value of [null, { ...admin, user: { ...admin.user, is_admin: false } }, { ...admin, user: { ...admin.user, disabled: true } }]) {
    session = value;
    assert.equal(hooks.useApiHealth().apiState, 'unknown');
    assert.equal(options.enabled, false);
    assert.equal(hooks.useAlarmRuntimeHealth().state, 'unknown');
    assert.equal(options.enabled, false);
  }
  assert.equal(requests.length, 0);
  session = admin;
  assert.equal(hooks.useApiHealth().apiState, 'connected');
  assert.deepEqual(Array.from(options.queryKey), ['api-health', 'admin', 1000]);
  assert.equal(options.refetchInterval, 30000);
  assert.equal(options.refetchIntervalInBackground, false);
  const signal = new AbortController().signal;
  await options.queryFn({ signal });
  hooks.useAlarmRuntimeHealth();
  assert.equal(options.enabled, true);
  assert.deepEqual(Array.from(options.queryKey), ['advanced-alarm-status', 'admin', 1000]);
  await options.queryFn({ signal });
  assert.deepEqual(requests, [['health', signal], ['alarm', signal]]);
});

function renderHealth(health, alarms, session = admin, onQuery = () => {}) {
  const page = load('../src/app/health/page.tsx', {
    react: React, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
    '@tanstack/react-query': { useQuery: options => { onQuery(options); return { data: [], isLoading: false, isError: false }; } },
    '@/lib/api/client': {}, '@/lib/hooks/use-health': { useApiHealth: () => health, useAlarmRuntimeHealth: () => alarms },
    '@/lib/hooks/use-session': { useSession: () => session },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    '@/components/ui/page-shell': { PageShell: ({ children, actions, title }) => React.createElement('main', null, title, actions, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: ({ items }) => React.createElement('section', null, ...items.map(item => React.createElement('span', { key: item.label }, item.label + ':' + item.value))) },
    '@/components/ui/button': { Button: 'button' }, '@/components/scanner/scan-status': { ScanStatus: () => null },
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

test('health page keeps API connected while the alarm worker is stopped and preserves opt-in Telegram', () => {
  const html = renderHealth(deriveApiHealth(query), deriveAlarmRuntime({ ...query, data: { ...runtime, running: false } }, now));
  assert.ok(html.includes('API:Bağlı'));
  assert.ok(html.includes('Durduruldu'));
  assert.ok(html.includes('Telegram yalnız kendi alarmınızda'));
  assert.ok(html.includes('href="/alarms"'));
  assert.ok(html.includes('Tarama arşivi'));
  assert.ok(html.includes('Yeni otomatik tarama çalıştırılmaz'));
  assert.ok(!html.includes('Bot durum ekranı'));
});

test('anonymous health page hides cached private content and disables both private queries', () => {
  const queries = [];
  const html = renderHealth(deriveApiHealth(query), deriveAlarmRuntime({ ...query, data: runtime }, now), null, value => queries.push(value));
  assert.equal(queries.length, 2);
  assert.ok(queries.every(value => value.enabled === false));
  assert.ok(html.includes('/login?next=%2Fhealth'));
  assert.ok(!html.includes('Telegram bağlantısı'));
  assert.ok(!html.includes('signal-buy'));
});

test('header SSR cannot mark failed or unconfirmed health green', () => {
  for (const flags of [{ isError: true }, { isStale: true }, { isLoading: true, data: undefined }]) {
    const header = load('../src/components/layout/header.tsx', {
      react: React, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
      'lucide-react': { Bell: () => null, Check: () => null, X: () => null },
      '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
      '@/lib/hooks/use-signals': { useSpecialNotificationSignals: () => ({ data: [] }) },
      '@/lib/hooks/use-health': { useApiHealth: () => deriveApiHealth({ ...query, ...flags }) },
      '@/components/auth/session-controls': { SessionControls: () => null },
    });
    const html = renderToStaticMarkup(React.createElement(header.Header));
    assert.ok(!html.includes('API Bağlı'));
    assert.ok(!html.includes('bg-profit'));
  }
});

test('scanner history renders API status without implying an automatic scanning process', () => {
  const primitive = ({ children }) => React.createElement('div', null, children);
  const page = load('../src/app/scanner/page.tsx', {
    react: React, 'react/jsx-runtime': jsxRuntime,
    'lucide-react': Object.fromEntries(['AlertTriangle', 'Check', 'ListPlus', 'RefreshCw', 'Search', 'Settings2', 'Star', 'StarOff'].map(name => [name, () => null])),
    '@tanstack/react-query': { useQuery: () => ({ data: undefined, isLoading: false, isError: false }) },
    '@/lib/api/client': {}, '@/lib/hooks/use-health': { useApiHealth: () => deriveApiHealth(query) },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: true, sessionKey: 'admin:123' }) },
    '@/components/market-data-status': { MarketDataStatus: () => null },
    '@/components/scanner/borsapy-screener': { BorsapyScreener: () => null },
    '@/components/ui/button': { Button: primitive }, '@/components/ui/input': { Input: () => null },
    '@/components/ui/select': { Select: primitive }, '@/components/ui/action-dialog': { ActionDialog: () => null },
    '@/components/ui/toast': { useToast: () => ({ addToast: () => {} }) },
    '@/components/scanner/scan-status': { ScanStatus: () => null },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), getTimeAgo: () => '--' },
  }, '\nexport { SignalHistoryScanner };');
  const html = renderToStaticMarkup(React.createElement(page.SignalHistoryScanner));
  assert.match(html, /API<\/span><span[^>]*>Bağlı<\/span>/);
  assert.ok(html.includes('Otomatik tarama kaldırıldı'));
  assert.ok(!html.includes('Bot Durumu'));
});
