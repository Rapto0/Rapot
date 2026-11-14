import assert from 'node:assert/strict';
import test from 'node:test';
import * as React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { load, hooks, nodes, text, primitives } from './view-harness.mjs';

const operations = [
  { id: 'screener.fundamental', label: 'Temel tarama' },
  { id: 'screener.technical', label: 'Teknik tarama' },
  { id: 'company.actions', label: 'Şirket işlemleri' },
];

test('scanner gates the private workspace behind an admin session', () => {
  for (const allowed of [false, true]) {
    let mounts = 0;
    const page = load('../src/app/scanner/page.tsx', { ...primitives,
      react: React,
      '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: 'admin:100' }) },
      '@/components/market-data-status': { MarketDataStatus: () => null },
      '@/components/scanner/scanner-workspace': { ScannerWorkspace: () => { mounts++; return React.createElement('p', null, 'RSI_TRACKER'); } },
    });
    const html = renderToStaticMarkup(React.createElement(page.default));
    assert.equal(mounts, allowed ? 1 : 0);
    assert.equal(html.includes('RSI_TRACKER'), allowed);
    assert.ok(!/COMBO|HUNTER|Sinyal Geçmişi|scanHistory/.test(html));
    if (!allowed) assert.ok(html.includes('/login?next=%2Fscanner'));
  }
});

test('advanced scan is available on demand and unmounts when collapsed', () => {
  const state = hooks();
  const page = load('../src/components/scanner/scanner-workspace.tsx', { ...primitives,
    react: state.react,
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: true, sessionKey: 'admin:100' }) },
    '@/components/market-data-status': { MarketDataStatus: () => null },
    '@/components/scanner/rsi-tracker': { RsiTracker: 'rsi-tracker' },
    '@/components/scanner/borsapy-screener': { BorsapyScreener: 'advanced-scanner' },
  });
  const render = () => { state.reset(); return page.ScannerWorkspace(); };
  let tree = render();
  assert.equal(nodes(tree).filter(node => node.type === 'advanced-scanner').length, 0);
  nodes(tree).find(node => node.type === 'button').props.onClick(); tree = render();
  assert.equal(nodes(tree).filter(node => node.type === 'advanced-scanner').length, 1);
  assert.equal(nodes(tree).find(node => node.type === 'button').props['aria-expanded'], true);
  nodes(tree).find(node => node.type === 'button').props.onClick(); tree = render();
  assert.equal(nodes(tree).filter(node => node.type === 'advanced-scanner').length, 0);
});

test('screener offers only fundamental/technical operations and selection has no automatic query/write', async () => {
  const state = hooks(); let query; const calls = [];
  const component = load('../src/components/scanner/borsapy-screener.tsx', { ...primitives,
    react: state.react,
    '@tanstack/react-query': { useQuery: options => { query = options; return { data: { operations } }; } },
    'next/navigation': { useRouter: () => ({ push: path => calls.push(['navigate', path]) }) },
    '@/lib/api/borsapy-api': { fetchResearchCatalog: signal => calls.push(['catalog', signal]) },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: true, sessionKey: 'admin:100' }) },
    '@/components/research/operation-panel': { OperationPanel: 'operation-panel' },
  });
  const render = () => { state.reset(); return component.BorsapyScreener(); };
  let tree = render(); const select = nodes(tree).find(node => node.type === 'select');
  assert.equal(nodes(select).filter(node => node.type === 'option').length, 2);
  assert.equal(query.enabled, true); assert.deepEqual(Array.from(query.queryKey), ['borsapy-catalog', 'admin:100']);
  assert.equal(nodes(tree).find(node => node.type === 'operation-panel').props.operation.id, 'screener.fundamental');
  select.props.onChange({ target: { value: 'screener.technical' } }); tree = render();
  const panel = nodes(tree).find(node => node.type === 'operation-panel');
  assert.equal(panel.props.operation.id, 'screener.technical'); assert.deepEqual(calls, []);
  assert.doesNotMatch(text(tree), /arşiv|sinyal akışı/i);
  const signal = new AbortController().signal; await query.queryFn({ signal });
  assert.deepEqual(calls, [['catalog', signal]]);
  panel.props.onConnection(); assert.deepEqual(calls.at(-1), ['navigate', '/research?tab=connection']);
});

test('screener reports missing catalog instead of inventing options', () => {
  const component = load('../src/components/scanner/borsapy-screener.tsx', { ...primitives, react: React,
    '@tanstack/react-query': { useQuery: () => ({ isError: true }) },
    'next/navigation': { useRouter: () => ({}) }, '@/lib/api/borsapy-api': {},
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed: true, sessionKey: 'admin:100' }) },
    '@/components/research/operation-panel': { OperationPanel: () => { throw Error('No fabricated operation'); } },
  });
  assert.match(renderToStaticMarkup(React.createElement(component.BorsapyScreener)), /Tarama seçenekleri alınamadı/);
});

test('symbol requests forward cancellation to the correct market endpoint', async () => {
  const requests = [];
  const api = load('../src/lib/api/ops-api.ts', {
    './core': { API_BASE_URL: '/api', fetchApi: (url, options) => { requests.push([url, options]); return Promise.resolve({ symbols: [], count: 0 }); } },
  });
  const signal = new AbortController().signal;
  await api.fetchBistSymbols(signal);
  await api.fetchCryptoSymbols(signal);
  assert.deepEqual(requests.map(([url]) => url), ['/api/symbols/bist', '/api/symbols/crypto']);
  assert.ok(requests.every(([, options]) => options.signal === signal));
});
