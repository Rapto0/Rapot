import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function load(relativePath, imports = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(relativePath, import.meta.url), 'utf8'), {
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
const { deriveBotHealth } = healthModel;
const status = {
  bot: { is_running: true, state: 'running', database: 'connected', is_scanning: false, uptime_human: '1h' },
  scanning: { data_available: true, last_scan_available: true, last_scan_time: '2026-09-10T10:00:00Z', scan_count: 12, signal_count: 3 },
  errors: { error_count: 0 },
};
const query = { data: status, isLoading: false, isError: false, isFetching: false, isStale: false };

test('missing, malformed and contradictory server flags never imply running or stopped', () => {
  assert.equal(deriveBotHealth({ ...query, data: {} }).state, 'unknown');
  for (const bot of [undefined, {}, { is_running: true }, { is_running: false },
    { ...status.bot, state: 'unknown' }, { ...status.bot, is_running: 'true' },
    { ...status.bot, state: 'stopped' }, { ...status.bot, database: 'disconnected' }]) {
    const data = bot ? { ...status, bot } : undefined;
    const health = deriveBotHealth({ ...query, data });
    assert.equal(health.state, 'unknown');
    assert.equal(health.isRunning, null);
    assert.equal(health.label, 'Bilinmiyor');
  }
});

test('current explicit running and stopped remain distinct', () => {
  assert.equal(deriveBotHealth(query).state, 'running');
  const stopped = deriveBotHealth({ ...query, data: { ...status, bot: { ...status.bot, state: 'stopped', is_running: false } } });
  assert.equal(stopped.state, 'stopped');
  assert.equal(stopped.isRunning, false);
  assert.equal(stopped.label, 'Durdu');
});

test('failed or stale refresh cannot display an older true response as active', () => {
  for (const flags of [{ isError: true }, { isStale: true }, { isError: true, isFetching: true }]) {
    const health = deriveBotHealth({ ...query, ...flags });
    assert.equal(health.state, 'unknown');
    assert.equal(health.isRunning, null);
    assert.equal(health.scanCount, null);
    assert.equal(health.uptime, '--');
  }
  for (const flags of [{ isLoading: true, data: undefined }, { isFetching: true }]) {
    const health = deriveBotHealth({ ...query, ...flags });
    assert.equal(health.state, 'loading');
    assert.equal(health.isRunning, null);
  }
});

test('DB and counter failures remain unavailable; explicit zero is real data', () => {
  const disconnected = deriveBotHealth({ ...query, data: { ...status, bot: { ...status.bot, database: 'disconnected' } } });
  for (const key of ['scanCount', 'signalCount', 'errorCount', 'lastScan', 'isScanning']) assert.equal(disconnected[key], null);
  const unavailable = deriveBotHealth({ ...query, data: { ...status, scanning: { ...status.scanning, data_available: false } } });
  assert.equal(unavailable.scanCount, null);
  assert.equal(unavailable.signalCount, null);
  assert.equal(unavailable.lastScan, status.scanning.last_scan_time);
  const zero = deriveBotHealth({ ...query, data: { ...status, scanning: { ...status.scanning, scan_count: 0 } } });
  assert.equal(zero.scanCount, 0);
});

test('hook uses the same model and existing 30-second polling freshness window', () => {
  let options;
  const hook = load('../src/lib/hooks/use-health.ts', {
    '@tanstack/react-query': { useQuery: (value) => { options = value; return { ...query, isError: true }; } },
    '@/lib/api/client': {}, '@/lib/health-status': healthModel,
  });
  assert.equal(hook.useBotHealth().state, 'unknown');
  assert.equal(options.refetchInterval, 30000);
  assert.equal(options.staleTime, 30000);
  assert.equal(Array.from(options.queryKey).join('/'), 'bot/status');
});

function renderHealth(health) {
  const page = load('../src/app/health/page.tsx', {
    react: React, 'react/jsx-runtime': jsxRuntime,
    '@tanstack/react-query': { useQuery: () => ({ data: [], isLoading: false, isError: false }) },
    '@/lib/api/client': {}, '@/lib/hooks/use-health': { useBotHealth: () => health },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    '@/components/ui/page-shell': { PageShell: ({ children, actions }) => React.createElement('main', null, actions, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: ({ items }) => React.createElement('section', null, ...items.map((item) => React.createElement('span', { key: item.label }, `${item.label}:${item.value}`))) },
    '@/components/ui/button': { Button: 'button' }, '@/components/scanner/scan-status': { ScanStatus: () => null },
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

test('health page SSR renders unknown/loading without an active or stopped badge', () => {
  for (const flags of [{ isError: true }, { isStale: true }, { isLoading: true, data: undefined }]) {
    const health = deriveBotHealth({ ...query, ...flags });
    const html = renderHealth(health);
    assert.ok(html.includes(health.label));
    assert.ok(!html.includes('signal-buy'));
    assert.ok(!html.includes('signal-sell'));
    assert.ok(html.includes('Toplam:--'));
    assert.ok(!html.includes('Hazır'));
  }
  assert.ok(renderHealth(deriveBotHealth(query)).includes('Çalışıyor'));
  assert.ok(renderHealth(deriveBotHealth({ ...query, data: { ...status, bot: { ...status.bot, state: 'stopped', is_running: false } } })).includes('Durdu'));
});

test('header SSR does not mark an unconfirmed API connection green', () => {
  for (const flags of [{ isLoading: true, data: undefined }, { isError: true }, { isStale: true }]) {
    const header = load('../src/components/layout/header.tsx', {
      react: React, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
      'lucide-react': { Bell: () => null, Check: () => null, X: () => null },
      '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
      '@/lib/hooks/use-signals': { useSpecialNotificationSignals: () => ({ data: [] }) },
      '@/lib/hooks/use-health': { useBotHealth: () => deriveBotHealth({ ...query, ...flags }) },
      '@/components/auth/session-controls': { SessionControls: () => null },
    });
    const html = renderToStaticMarkup(React.createElement(header.Header));
    assert.ok(!html.includes('API Bağlı'));
    assert.ok(!html.includes('bg-profit'));
  }
});

test('scanner page SSR uses the same explicit status instead of defaulting to active', () => {
  const primitive = ({ children }) => React.createElement('div', null, children);
  const icons = Object.fromEntries(['AlertTriangle', 'Check', 'ListPlus', 'RefreshCw', 'Search', 'Settings2', 'Star', 'StarOff'].map((name) => [name, () => null]));
  for (const flags of [{ isError: true }, { isLoading: true, data: undefined }, {}]) {
    const health = deriveBotHealth({ ...query, ...flags });
    const page = load('../src/app/scanner/page.tsx', {
      react: React, 'react/jsx-runtime': jsxRuntime, 'lucide-react': icons,
      '@tanstack/react-query': { useQuery: () => ({ data: undefined, isLoading: false, isError: false }) },
      '@/lib/api/client': {}, '@/lib/hooks/use-health': { useBotHealth: () => health },
      '@/components/ui/button': { Button: primitive }, '@/components/ui/input': { Input: () => null },
      '@/components/ui/select': { Select: primitive }, '@/components/ui/action-dialog': { ActionDialog: () => null },
      '@/components/ui/toast': { useToast: () => ({ addToast: () => {} }) },
      '@/components/scanner/scan-status': { ScanStatus: () => null },
      '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), getTimeAgo: () => '--' },
    });
    const html = renderToStaticMarkup(React.createElement(page.default));
    assert.ok(html.includes('Bot Durumu'));
    assert.match(html, new RegExp(`Bot Durumu</span><span[^>]*>${health.label}</span>`));
    assert.ok(!html.includes('AKTIF'));
    assert.ok(!html.includes('PASIF'));
  }
});

test('bot dashboard SSR does not render cached success after a query error', () => {
  const primitive = ({ children }) => React.createElement('div', null, children);
  const dashboard = load('../src/components/dashboard/bot-dashboard.tsx', {
    'react/jsx-runtime': jsxRuntime,
    '@/components/ui/card': { Card: primitive, CardContent: primitive, CardHeader: primitive, CardTitle: primitive },
    '@/components/ui/badge': { Badge: primitive }, '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    'lucide-react': Object.fromEntries(['Bot', 'Pause', 'Activity', 'TrendingUp', 'Clock'].map((name) => [name, () => null])),
    '@tanstack/react-query': { useQuery: () => ({ data: undefined }) }, '@/lib/api/client': {},
    '@/lib/hooks/use-health': { useBotHealth: () => deriveBotHealth({ ...query, isError: true }) },
    '@/lib/metric-display': { formatMetric: () => '--', formatMetricPercent: () => '--', formatTradePrice: () => '--', metricTextClass: () => '' },
  });
  const html = renderToStaticMarkup(React.createElement(dashboard.BotDashboard));
  assert.ok(html.includes('Bilinmiyor'));
  assert.ok(!html.includes('AKTİF'));
  assert.ok(!html.includes('DURDURULDU'));
  assert.ok(html.includes('Uptime: --'));
});
