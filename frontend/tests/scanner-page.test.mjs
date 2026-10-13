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

test('scanner mounts only the real screener for admin and no archived history tab', () => {
  for (const allowed of [false, true]) {
    let mounts = 0;
    const page = load('../src/app/scanner/page.tsx', { ...primitives,
      '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: 'admin:100' }) },
      '@/components/market-data-status': { MarketDataStatus: () => null },
      '@/components/scanner/borsapy-screener': { BorsapyScreener: () => { mounts++; return React.createElement('p', null, 'CURRENT_SCREENER'); } },
    });
    const html = renderToStaticMarkup(React.createElement(page.default));
    assert.equal(mounts, allowed ? 1 : 0);
    assert.equal(html.includes('CURRENT_SCREENER'), allowed);
    assert.ok(!/COMBO|HUNTER|Sinyal Geçmişi|scanHistory/.test(html));
    if (!allowed) assert.ok(html.includes('/login?next=%2Fscanner'));
  }
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
