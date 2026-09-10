import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function loadSource(path, imports = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({
    exports: {}, URLSearchParams,
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const route = loadSource('../src/lib/chart-route.ts');
const page = loadSource('../src/app/chart/page.tsx', {
  'react/jsx-runtime': jsxRuntime,
  '@/lib/chart-route': route,
  '@/components/charts/advanced-chart': {
    AdvancedChartPage: props => React.createElement('output', {
      'data-symbol': props.initialSymbol, 'data-market': props.initialMarket,
    }),
  },
}).default;

const selection = params => JSON.parse(JSON.stringify(route.resolveChartSelection(params)));

test('chart awaits Next searchParams before selecting the requested crypto chart', async () => {
  let resolve;
  const searchParams = new Promise(done => { resolve = done; });
  let finished = false;
  const rendered = page({ searchParams }).then(element => {
    finished = true;
    return renderToStaticMarkup(element);
  });
  await Promise.resolve();
  assert.equal(finished, false);
  resolve({ symbol: ' btcusdt ', market: ' Kripto ' });
  assert.match(await rendered, /data-symbol="BTCUSDT" data-market="Kripto"/);
});

test('each route render forwards new symbol and market props without a stale selection', async () => {
  for (const [symbol, market] of [['ASELS', 'BIST'], ['ETHUSDT', 'Kripto'], ['THYAO', 'BIST']]) {
    const html = renderToStaticMarkup(await page({ searchParams: Promise.resolve({ symbol, market }) }));
    assert.ok(html.includes(`data-symbol="${symbol}" data-market="${market}"`));
  }
});

test('missing, repeated and mixed-case query values have deterministic defaults', () => {
  assert.deepEqual(selection(), { symbol: 'THYAO', market: 'BIST' });
  assert.deepEqual(selection({ market: 'KRIPTO' }), { symbol: 'BTCUSDT', market: 'Kripto' });
  assert.deepEqual(selection({ symbol: [' asels ', 'BTCUSDT'], market: ['bist', 'Kripto'] }), { symbol: 'ASELS', market: 'BIST' });
  assert.deepEqual(selection({ symbol: ['', 'ETHUSDT'], market: ['kripto', 'BIST'] }), { symbol: 'BTCUSDT', market: 'Kripto' });
  assert.deepEqual(selection({ symbol: [], market: [] }), { symbol: 'THYAO', market: 'BIST' });
  assert.deepEqual(selection({ symbol: 'asels', market: 'unknown' }), { symbol: 'ASELS', market: 'BIST' });
});

test('invalid symbol syntax falls back within the selected market', () => {
  for (const symbol of [' ', 'BTC/USDT', '../x', 'BTC?market_type=BIST', '<script>', 'A'.repeat(33), 'SI\nSE', 'İSCTR']) {
    assert.deepEqual(selection({ symbol, market: 'Kripto' }), { symbol: 'BTCUSDT', market: 'Kripto' });
    assert.deepEqual(selection({ symbol, market: 'BIST' }), { symbol: 'THYAO', market: 'BIST' });
  }
  assert.equal(selection({ symbol: '1000satsusdt', market: 'Kripto' }).symbol, '1000SATSUSDT');
  // A syntactically valid unknown ticker remains visible; this is not a symbol registry.
  assert.equal(selection({ symbol: 'NOTLISTED', market: 'BIST' }).symbol, 'NOTLISTED');
});

test('chart without searchParams renders the default BIST chart', async () => {
  assert.match(renderToStaticMarkup(await page({})), /data-symbol="THYAO" data-market="BIST"/);
});

test('candle requests preserve AbortSignal and encode route/query values', async () => {
  let requested;
  const response = { candles: [] };
  const market = loadSource('../src/lib/api/market-api.ts', {
    './core': { API_BASE_URL: '/api', fetchApi: async (url, options) => { requested = { url, options }; return response; } },
  });
  const controller = new AbortController();
  assert.equal(await market.fetchCandles('A/B?C', 'Kripto&x=1', '1d&limit=999', 320, { signal: controller.signal }), response);
  const url = new URL(requested.url, 'https://example.invalid');
  assert.equal(url.pathname, '/api/candles/A%2FB%3FC');
  assert.equal(url.searchParams.get('market_type'), 'Kripto&x=1');
  assert.equal(url.searchParams.get('timeframe'), '1d&limit=999');
  assert.equal(url.searchParams.get('limit'), '320');
  assert.equal(url.searchParams.get('x'), null);
  assert.equal(requested.options.signal, controller.signal);
  controller.abort();
  assert.equal(requested.options.signal.aborted, true);
});

test('existing four-argument candle callers keep their defaults', async () => {
  let requested;
  const market = loadSource('../src/lib/api/market-api.ts', {
    './core': { API_BASE_URL: '/api', fetchApi: async (url, options) => { requested = { url, options }; return { candles: [] }; } },
  });
  await market.fetchCandles('THYAO');
  assert.equal(requested.url, '/api/candles/THYAO?market_type=BIST&timeframe=1d&limit=500');
  assert.equal(requested.options.signal, undefined);
});
