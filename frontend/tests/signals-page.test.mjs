import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import test from 'node:test';
import * as React from 'react';
import * as icons from 'lucide-react';
import { renderToStaticMarkup } from 'react-dom/server';
import { load, hooks, nodes, text, primitives } from './view-harness.mjs';
const admin = { user: { username: 'admin', is_admin: true, disabled: false }, expiresAt: 123 };

test('retired signal route redirects without fetching history; navigation prioritizes alarms and retains trades', () => {
  const calls = [];
  const page = load('../src/app/signals/page.tsx', { 'next/navigation': { redirect: value => calls.push(value) } });
  page.default(); assert.deepEqual(calls, ['/alarms']);
  const { navigation } = load('../src/components/layout/navigation.ts', { 'lucide-react': icons });
  assert.ok(!navigation.some(item => item.href === '/signals'));
  for (const href of ['/chart', '/alarms', '/trades', '/scanner', '/ai', '/research']) assert.ok(navigation.some(item => item.href === href));
});

test('legacy signal REST and socket entry points are absent, while native indicator calculation remains', () => {
  for (const file of ['lib/api/signals-api.ts', 'lib/hooks/use-signals.ts', 'lib/realtime/signals.ts', 'lib/signal-export.ts', 'components/scanner/scan-status.tsx']) {
    assert.ok(!existsSync(new URL(`../src/${file}`, import.meta.url)), file);
  }
  const chart = readFileSync(new URL('../src/components/charts/advanced-chart.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(chart, /fetchSignals|chart-watchlist-signals-feed|href="\/signals"|WatchlistSignalFeed/);
  assert.match(chart, /workerComputationState\.overlays\.combo/); assert.match(chart, /workerComputationState\.overlays\.hunter/);
});

function workspace(session, options = {}) {
  const queries = [], calls = [];
  const response = { data: { watchlists: [{ id: 'id / ? test', name: 'PRIVATE_LIST', symbols: [{ symbol: 'THYAO', market_type: 'BIST' }] }] }, ...options };
  const href = load('../src/lib/server-watchlists.ts');
  const component = load('../src/components/dashboard/alarm-workspace.tsx', { ...primitives,
    '@tanstack/react-query': { useQuery: value => { queries.push(value); return { ...response, refetch: () => calls.push('refresh') }; } },
    '@/lib/api/advanced-alarms-api': { fetchServerWatchlists: signal => calls.push(signal) },
    '@/lib/hooks/use-health': { useAlarmRuntimeHealth: () => ({ label: 'Doğrulanamadı' }) },
    '@/lib/hooks/use-session': { useSession: () => session }, '@/lib/server-watchlists': href,
  });
  return { tree: component.AlarmWorkspace(), queries, calls };
}

test('dashboard lists link to the selected server list, never creating or enabling an alarm', async () => {
  const h = workspace(admin); const links = nodes(h.tree).filter(node => node.type === 'a');
  assert.ok(links.some(node => node.props.href === '/chart?serverList=id%20%2F%20%3F%20test'));
  assert.ok(links.some(node => node.props.href === '/alarms?serverList=id%20%2F%20%3F%20test&action=new'));
  assert.ok(links.some(node => node.props.href === '/alarms?serverList=id%20%2F%20%3F%20test'));
  assert.deepEqual(h.calls, []); assert.equal(h.queries[0].enabled, true);
  const signal = new AbortController().signal; await h.queries[0].queryFn({ signal });
  assert.deepEqual(h.calls, [signal]); assert.equal(h.queries[0].refetchIntervalInBackground, false);
});

test('dashboard never exposes cached list names to guests, disabled accounts or non-admins', () => {
  for (const session of [null, { ...admin, user: { ...admin.user, disabled: true } }, { ...admin, user: { ...admin.user, is_admin: false } }]) {
    const h = workspace(session); assert.equal(h.queries[0].enabled, false);
    assert.doesNotMatch(text(h.tree), /PRIVATE_LIST/); assert.match(text(h.tree), /yönetici girişi/); assert.deepEqual(h.calls, []);
  }
});

test('dashboard keeps previous list rows on refresh failure but clearly marks the failure', () => {
  const h = workspace(admin, { isError: true }); assert.match(text(h.tree), /PRIVATE_LIST/);
  assert.match(text(h.tree), /Listeler yenilenemedi/);
  nodes(h.tree).find(node => node.type === 'button').props.onClick(); assert.deepEqual(h.calls, ['refresh']);
});

function aiHarness() {
  const state = hooks(), calls = [];
  const component = load('../src/components/ai/ai-terminal.tsx', { ...primitives, react: state.react, 'lucide-react': icons,
    '@/lib/api/client': { fetchAIAnalysis: async params => { calls.push(params); return { inspection: { timeframes: [] } }; } },
    '@/lib/hooks/use-analyses': { useRecentAnalyses: () => ({ data: [], refetch() {} }) },
    '@/components/indicators/strategy-inspector-panel': { StrategyInspectorPanel: 'indicator-inspector' },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: true, sessionKey: 'admin:123' }) },
  }, '\nexport { ManualAITerminal };');
  return { calls, render() { state.reset(); return component.ManualAITerminal(); } };
}

test('manual AI retains COMBO/HUNTER and timeframe inputs; only explicit analysis invokes paid work', async () => {
  const h = aiHarness(); let tree = h.render();
  assert.deepEqual(h.calls, []); assert.ok(nodes(tree).some(node => node.type === 'indicator-inspector'));
  const change = (label, value) => { nodes(tree).find(node => node.props['aria-label'] === label).props.onChange({ target: { value } }); tree = h.render(); };
  change('Analiz sembolü', 'garan'); change('Gösterge', 'COMBO'); change('Piyasa', 'BIST'); change('Periyot', '1W');
  assert.deepEqual(h.calls, []);
  await nodes(tree).find(node => node.type === 'button' && text(node).includes('AI Yorumla')).props.onClick();
  assert.deepEqual(JSON.parse(JSON.stringify(h.calls)), [{ symbol: 'GARAN', strategy: 'COMBO', market_type: 'BIST', timeframe: '1W' }]);
});

test('manual AI guest page does not mount private query or calculation components', () => {
  const component = load('../src/components/ai/ai-terminal.tsx', { ...primitives, react: React, 'lucide-react': icons,
    '@/lib/api/client': {}, '@/lib/hooks/use-analyses': { useRecentAnalyses() { throw Error('private query mounted'); } },
    '@/components/indicators/strategy-inspector-panel': { StrategyInspectorPanel() { throw Error('calculator mounted'); } },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: false, sessionKey: 'guest' }) },
  });
  assert.match(renderToStaticMarkup(React.createElement(component.AITerminal)), /Giriş yap/);
});

test('manual analysis history is session scoped and excludes legacy linked signal rows', async () => {
  let allowed = false, query;
  const hook = load('../src/lib/hooks/use-analyses.ts', {
    './use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: allowed ? 'admin:123' : 'guest' }) },
    '@tanstack/react-query': { useQuery: options => { query = options; return {}; } },
    '@/lib/api/client': { fetchAnalyses: async () => [{ id: 1, signal_id: null }, { id: 2, signal_id: 99 }], transformAnalysis: value => value },
  });
  hook.useRecentAnalyses(16); assert.equal(query.enabled, false);
  allowed = true; hook.useRecentAnalyses(16); assert.equal(query.enabled, true);
  assert.ok(query.queryKey.includes('admin:123')); assert.deepEqual((await query.queryFn()).map(row => row.id), [1]);
});

test('standalone COMBO/HUNTER inspection remains explicit and uses its current calculation endpoint', async () => {
  const state = hooks(), calls = [];
  const inspector = load('../src/components/indicators/strategy-inspector-panel.tsx', { ...primitives,
    react: state.react, 'lucide-react': icons,
    '@/lib/api/client': { fetchStrategyInspector: async params => { calls.push(params); return { timeframes: [], indicator_order: [], indicator_labels: {} }; } },
  });
  const render = () => { state.reset(); return inspector.StrategyInspectorPanel({ selectedSymbol: 'THYAO', selectedMarketType: 'BIST' }); };
  let tree = render(); assert.deepEqual(calls, []);
  const strategy = nodes(tree).find(node => node.type === 'select' && node.props.value === 'HUNTER');
  strategy.props.onChange({ target: { value: 'COMBO' } }); tree = render(); assert.deepEqual(calls, []);
  await nodes(tree).find(node => node.type === 'button' && text(node) === 'Hesapla').props.onClick();
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [{ symbol: 'THYAO', strategy: 'COMBO', market_type: 'BIST' }]);
});
