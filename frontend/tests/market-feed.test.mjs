import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function load(path, imports = {}, globals = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {},
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
    fetch() { assert.fail('Market tests must never access the network'); },
    ...globals,
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const feed = load('../src/lib/market-feed.ts');
const plain = value => JSON.parse(JSON.stringify(value));
const now = 1_800_000_000_000;
const requestState = {
  receivedAt: now, now, available: 3, total: 3,
  isError: false, isFetching: false, isPaused: false,
};
const describe = overrides => feed.describeMarketRequest({ ...requestState, ...overrides });

test('finite prices preserve numeric zero and reject coercible or nonfinite values', () => {
  for (const value of [0, -0, -12.5, 0.001, 1234]) assert.equal(feed.finiteNumber(value), true);
  for (const value of [null, undefined, NaN, Infinity, -Infinity, '0', '12.5', '', true, {}, []]) {
    assert.equal(feed.finiteNumber(value), false);
  }
});

test('normalization accepts only requested symbols with finite prices and optional finite changes', () => {
  const values = [
    { symbol: 'zero', regularMarketPrice: 0, regularMarketChangePercent: 0 },
    { symbol: 'PRICE', regularMarketPrice: 12.5, regularMarketChangePercent: null },
    { symbol: 'NEG', regularMarketPrice: -2, regularMarketChangePercent: -1.25 },
    { symbol: 'OTHER', regularMarketPrice: 99, regularMarketChangePercent: 3 },
    { symbol: 'BAD', regularMarketPrice: '12.5' },
    null, undefined, false, {}, { symbol: 12, regularMarketPrice: 1 },
  ];
  assert.deepEqual(plain(feed.normalizeMarketQuotes(values, ['ZERO', 'price', 'NEG', 'BAD'])), {
    ZERO: { value: 0, change: 0 }, PRICE: { value: 12.5 }, NEG: { value: -2, change: -1.25 },
  });
  for (const invalid of [null, undefined, NaN, Infinity, -Infinity, '0']) {
    assert.deepEqual(plain(feed.normalizeMarketQuotes([
      { symbol: 'BAD', regularMarketPrice: invalid, regularMarketChangePercent: 9 },
    ], ['BAD'])), {});
    const quote = feed.normalizeMarketQuotes([
      { symbol: 'GOOD', regularMarketPrice: 1, regularMarketChangePercent: invalid },
    ], ['GOOD']).GOOD;
    assert.equal(quote.value, 1);
    assert.equal(Object.hasOwn(quote, 'change'), false);
  }
});

test('partial and empty successful responses never carry omitted symbols forward', () => {
  const first = feed.normalizeMarketQuotes([
    { symbol: 'A', regularMarketPrice: 1 }, { symbol: 'B', regularMarketPrice: 2 },
  ], ['A', 'B']);
  const partial = feed.normalizeMarketQuotes([{ symbol: 'B', regularMarketPrice: 3 }], ['A', 'B']);
  assert.deepEqual(plain(partial), { B: { value: 3 } });
  assert.deepEqual(plain(feed.normalizeMarketQuotes([], ['A', 'B'])), {});
  assert.deepEqual(plain(first), { A: { value: 1 }, B: { value: 2 } });
  for (const payload of [null, undefined, {}, { data: [] }, '[]', 0]) {
    assert.throws(() => feed.normalizeMarketQuotes(payload, ['A']), /Geçersiz piyasa yanıtı/);
  }
});

test('initial loading, partial data, empty success and background refresh have distinct notices', () => {
  const loading = describe({ receivedAt: 0, available: 0 });
  assert.equal(loading.label, 'Yükleniyor');
  assert.equal(loading.loading, true);
  const partial = describe({ available: 1 });
  assert.equal(partial.label, 'Eksik veri');
  assert.equal(partial.warning, true);
  assert.match(partial.description, /2 enstrümanın/);
  const empty = describe({ available: 0 });
  assert.equal(empty.label, 'Veri yok');
  assert.equal(empty.loading, false);
  assert.equal(empty.warning, true);
  assert.equal(describe({}).label, 'Veri alındı');
  const refreshing = describe({ isFetching: true });
  assert.equal(refreshing.label, 'Veri alındı', 'Background polling must not churn the live status label');
  assert.equal(refreshing.warning, false);
  assert.equal(refreshing.loading, true);
});

test('a failed refresh warns that retained prices are old, including while another fetch runs', () => {
  for (const isFetching of [false, true]) {
    const notice = describe({ isError: true, isFetching });
    assert.equal(notice.label, 'Yenilenemedi');
    assert.match(notice.description, /Son alınan fiyatlar gösteriliyor/);
    assert.equal(notice.warning, true);
    assert.equal(notice.loading, isFetching);
  }
  assert.match(describe({ isError: true, available: 0 }).description, /Fiyatlar alınamadı/);
});

test('paused fetches show the connection state and never imply an active loading request', () => {
  for (const available of [0, 2]) {
    const notice = describe({ available, isPaused: true, isError: true, isFetching: true });
    assert.equal(notice.label, 'Bağlantı bekleniyor');
    assert.match(notice.description, /Bağlantı gelince tekrar denenecek/);
    assert.equal(notice.warning, true);
    assert.equal(notice.loading, false);
  }
});

test('receipt freshness expires at thirty seconds even when prices remain available', () => {
  assert.equal(feed.isFeedStale(undefined, now), false);
  assert.equal(feed.isFeedStale(now, now + 29_999), false);
  assert.equal(feed.isFeedStale(now, now + 30_000), true);
  assert.equal(describe({ now: now + 29_999 }).warning, false);
  const stale = describe({ now: now + 30_000, isFetching: true });
  assert.equal(stale.label, 'Yenileme gecikti');
  assert.equal(stale.warning, true);
  assert.equal(stale.loading, true);
  assert.match(stale.description, /Son alınan fiyatlar gösteriliyor/);
  assert.equal(feed.receivedAge(undefined, now), 'Henüz alınmadı');
  assert.equal(feed.receivedAge(now, now + 30_000), '30 sn önce');
  assert.equal(feed.receivedAge(now, now + 120_000), '2 dk önce');
});

test('a connected feed without valid prices stops indefinite loading after thirty seconds', () => {
  for (const status of ['connecting', 'connected']) {
    const state = { status, receivedAt: [undefined, undefined], total: 2, startedAt: now };
    const waiting = feed.describeTickerFeed({ ...state, now: now + 29_999 });
    assert.equal(waiting.loading, true);
    assert.equal(waiting.warning, false);
    const expired = feed.describeTickerFeed({ ...state, now: now + 30_000 });
    assert.equal(expired.label, 'Veri alınamadı');
    assert.equal(expired.loading, false);
    assert.equal(expired.warning, true);
  }
  const partial = feed.describeTickerFeed({
    status: 'connected', receivedAt: [now, undefined], now, total: 2, startedAt: now - 60_000,
  });
  assert.equal(partial.label, 'Eksik veri');
  const stale = feed.describeTickerFeed({
    status: 'connected', receivedAt: [now - 30_000, now], now, total: 2,
  });
  assert.equal(stale.label, 'Akış gecikti');
  assert.equal(stale.warning, true);
});

const category = load('../src/components/dashboard/market-category.tsx', {
  'react/jsx-runtime': jsxRuntime,
  'lucide-react': { RefreshCw: () => null, AlertCircle: () => null },
  '@/lib/market-feed': feed,
  '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
});
function strip(row, props = {}) {
  return renderToStaticMarkup(React.createElement(category.MarketStrip, {
    row: { key: 'TEST', label: 'Test fiyatı', ...row }, now, streaming: false, loading: false, ...props,
  }));
}

test('market strips render numeric zero without a fabricated positive change', () => {
  const html = strip({ value: 0, change: 0 });
  assert.match(html, />0,0000</);
  assert.match(html, />0\.00%</);
  assert.doesNotMatch(html, /NaN|Infinity|\+0|Veri yok/);
  for (const change of [undefined, null, NaN, Infinity, -Infinity, '0']) {
    const missingChange = strip({ value: 12.5, change });
    assert.match(missingChange, />12,50</);
    assert.doesNotMatch(missingChange, /NaN|Infinity|\+0|%/);
  }
});

test('missing prices suppress orphan percentages and use explicit unavailable/loading text', () => {
  for (const value of [undefined, null, NaN, Infinity, -Infinity, '12.5']) {
    const html = strip({ value, change: 2.5 });
    assert.match(html, /Veri yok/);
    assert.doesNotMatch(html, /NaN|Infinity|\+0|%/);
  }
  assert.match(strip({}, { loading: true }), /Veri bekleniyor/);
});

test('streaming strips mark stale receipts and categories expose named status and refresh controls', () => {
  assert.match(strip({ value: 1, receivedAt: now - 30_000 }, { streaming: true }), /Akış gecikti/);
  assert.match(strip({ value: 1, receivedAt: now - 1000 }, { streaming: true }), /Son alım:/);
  const html = renderToStaticMarkup(React.createElement(category.MarketCategoryPanel, {
    id: 'indices', label: 'Endeksler', description: 'Piyasa fiyatları', now, receivedAt: now,
    rows: [{ key: 'A', label: 'Birinci', value: 0 }, { key: 'B', label: 'İkinci' }],
    notice: describe({ available: 1, total: 2 }), onRefresh() {}, refreshing: true, streaming: false,
  }));
  assert.match(html, /<article[^>]*aria-labelledby="indices-heading"/);
  assert.match(html, /<h2[^>]*id="indices-heading"[^>]*>Endeksler<\/h2>/);
  assert.match(html, /<h3[^>]*>Birinci<\/h3>/);
  assert.match(html, /1\/2 fiyat/);
  assert.match(html, /role="status"/);
  assert.match(html, /aria-label="Endeksler: verileri yenile"/);
  assert.match(html, /disabled=""/);
});

function hookHarness(fetchImplementation) {
  const timers = new Map(), cleared = [], calls = [];
  let nextTimer = 0, options;
  const hook = load('../src/lib/hooks/use-market-snapshot.ts', {
    '@tanstack/react-query': { useQuery(value) { options = value; return { query: 'sentinel' }; } },
    '@/lib/market-feed': feed,
    '@/lib/api/client': {
      fetchGlobalIndices(symbols, request) {
        calls.push({ symbols: Array.from(symbols), signal: request.signal });
        return fetchImplementation(symbols, request.signal, calls.length - 1);
      },
    },
  }, {
    AbortController,
    setTimeout(callback, delay) { const id = ++nextTimer; timers.set(id, { callback, delay }); return id; },
    clearTimeout(id) { cleared.push(id); timers.delete(id); },
  });
  const controller = new AbortController();
  const listeners = new Set();
  const signal = {
    get aborted() { return controller.signal.aborted; },
    addEventListener(type, callback, settings) {
      assert.equal(type, 'abort'); assert.equal(settings.once, true);
      listeners.add(callback); controller.signal.addEventListener(type, callback, settings);
    },
    removeEventListener(type, callback) {
      listeners.delete(callback); controller.signal.removeEventListener(type, callback);
    },
  };
  return { hook, calls, timers, cleared, listeners, signal, controller, get options() { return options; } };
}

function pendingUntilAbort(signal) {
  return new Promise((resolve, reject) => {
    const cancel = () => reject(new DOMException('Request cancelled', 'AbortError'));
    if (signal.aborted) cancel();
    else signal.addEventListener('abort', cancel, { once: true });
  });
}

function assertCleaned(harness) {
  assert.equal(harness.timers.size, 0, 'Timeout must be cleared');
  assert.equal(harness.listeners.size, 0, 'Caller abort listener must be removed');
  assert.equal(harness.cleared.length, 1);
  assert.ok(harness.calls.every(call => call.signal.aborted), 'Sibling requests must be cancelled');
}

test('snapshot requests at most thirty symbols per chunk and normalize partial data', async () => {
  const symbols = Array.from({ length: 65 }, (_, index) => `S${index}`);
  const h = hookHarness(chunk => Promise.resolve([
    { symbol: chunk[0], regularMarketPrice: 0, regularMarketChangePercent: 0 },
    { symbol: chunk[1], regularMarketPrice: null },
    { symbol: 'UNREQUESTED', regularMarketPrice: 100 },
  ]));
  const result = await h.hook.loadMarketSnapshot(symbols, h.signal);
  assert.deepEqual(h.calls.map(call => call.symbols.length), [30, 30, 5]);
  assert.deepEqual(h.calls.flatMap(call => call.symbols), symbols);
  assert.equal(new Set(h.calls.map(call => call.signal)).size, 1);
  assert.deepEqual(plain(result), {
    S0: { value: 0, change: 0 }, S30: { value: 0, change: 0 }, S60: { value: 0, change: 0 },
  });
  assert.equal(h.controller.signal.aborted, false);
  assertCleaned(h);
});

test('empty successful HTTP data returns no stale quotes and an empty symbol group makes no request', async () => {
  for (const symbols of [[], ['A', 'B']]) {
    const h = hookHarness(() => Promise.resolve([]));
    assert.deepEqual(plain(await h.hook.loadMarketSnapshot(symbols, h.signal)), {});
    assert.equal(h.calls.length, symbols.length ? 1 : 0);
    assertCleaned(h);
  }
});

test('one failed or malformed chunk rejects the whole snapshot and cancels pending siblings', async () => {
  for (const malformed of [false, true]) {
    const failure = new Error('HTTP 503');
    const h = hookHarness((chunk, signal, index) => index === 1
      ? (malformed ? Promise.resolve({ quotes: [] }) : Promise.reject(failure))
      : pendingUntilAbort(signal));
    await assert.rejects(h.hook.loadMarketSnapshot(Array.from({ length: 61 }, (_, i) => `S${i}`), h.signal),
      error => malformed ? /Geçersiz piyasa yanıtı/.test(error.message) : error === failure);
    assert.equal(h.calls.length, 3);
    assertCleaned(h);
  }
});

test('the sixty-second timeout aborts a stalled request and removes its timer/listener', async () => {
  const h = hookHarness((chunk, signal) => pendingUntilAbort(signal));
  const pending = h.hook.loadMarketSnapshot(['A'], h.signal);
  const rejected = assert.rejects(pending, error => error.name === 'AbortError');
  assert.equal(h.timers.size, 1);
  const timer = [...h.timers.values()][0];
  assert.equal(timer.delay, 60_000);
  assert.equal(h.calls[0].signal.aborted, false);
  timer.callback();
  await rejected;
  assert.equal(h.controller.signal.aborted, false);
  assertCleaned(h);
});

test('caller cancellation is propagated both before and during a snapshot request', async () => {
  for (const alreadyAborted of [false, true]) {
    const h = hookHarness((chunk, signal) => pendingUntilAbort(signal));
    if (alreadyAborted) h.controller.abort();
    const pending = h.hook.loadMarketSnapshot(['A'], h.signal);
    const rejected = assert.rejects(pending, error => error.name === 'AbortError');
    if (!alreadyAborted) {
      assert.equal(h.listeners.size, 1);
      h.controller.abort();
    }
    await rejected;
    assertCleaned(h);
  }
});

test('query integration polls every ten seconds without retries and links the query abort signal', async () => {
  const h = hookHarness((chunk, signal) => pendingUntilAbort(signal));
  const symbols = ['A', 'B'];
  assert.deepEqual(plain(h.hook.useMarketSnapshot(symbols)), { query: 'sentinel' });
  assert.deepEqual(plain(h.options.queryKey), ['home-market-snapshot', ['A', 'B']]);
  assert.equal(h.options.refetchInterval, 10_000);
  assert.equal(h.options.staleTime, 10_000);
  assert.equal(h.options.retry, false);
  assert.equal(h.options.refetchOnWindowFocus, true);
  const pending = h.options.queryFn({ signal: h.signal });
  const rejected = assert.rejects(pending, error => error.name === 'AbortError');
  assert.deepEqual(h.calls[0].symbols, symbols);
  h.controller.abort();
  await rejected;
  assertCleaned(h);
});

test('the market API forwards the cancellation signal and repeated symbol query parameters', async () => {
  const controller = new AbortController();
  let request;
  const api = load('../src/lib/api/market-api.ts', {
    './core': { API_BASE_URL: '/api', fetchApi(url, options) { request = { url, options }; return Promise.resolve([]); } },
  }, { URLSearchParams });
  await api.fetchGlobalIndices(['^GSPC', 'EURUSD=X'], { signal: controller.signal });
  assert.equal(request.options.signal, controller.signal);
  const url = new URL(request.url, 'https://example.invalid');
  assert.equal(url.pathname, '/api/market/indices');
  assert.deepEqual(url.searchParams.getAll('symbol'), ['^GSPC', 'EURUSD=X']);
});
