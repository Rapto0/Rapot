import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
import { create } from 'zustand';
import { QueryClient, QueryObserver } from '@tanstack/react-query';
import ts from 'typescript';

const sourceRoot = fileURLToPath(new URL('../src/lib/realtime/', import.meta.url));
const sample = {
  id: 1, symbol: 'BTCUSDT', marketType: 'Kripto', strategy: 'COMBO',
  signalType: 'AL', timeframe: '1D', score: '+4/-0', price: 100,
  createdAt: '2026-09-10T10:00:00Z', specialTag: 'BELES',
};

function harness(realQueryClient) {
  let now = 0;
  let nextTimer = 0;
  const timers = new Map();
  const sockets = [];
  const attempts = [];
  const failures = new Map();
  const effects = [];
  const invalidations = [];
  const queryClient = { invalidateQueries: ({ queryKey }, options) => {
    assert.equal(options.cancelRefetch, false, 'Bursts must allow slow REST requests to finish');
    invalidations.push([...queryKey]);
  } };
  class MockSocket {
    static OPEN = 1;
    static CONNECTING = 0;
    constructor(url) {
      attempts.push(url);
      if (failures.get(url)) {
        failures.set(url, failures.get(url) - 1);
        throw new Error('Constructor unavailable');
      }
      this.url = url;
      this.readyState = 0;
      this.closeCount = 0;
      sockets.push(this);
    }
    open() { this.readyState = 1; this.onopen?.({}); }
    message(data) { this.onmessage?.({ data: typeof data === 'string' ? data : JSON.stringify(data) }); }
    close() { this.readyState = 3; this.closeCount++; this.onclose?.({}); }
    error() { this.onerror?.({}); }
  }
  const modules = new Map();
  const context = vm.createContext({
    console, URL, Map, Set, Date, WebSocket: MockSocket,
    window: { location: { origin: 'https://rapot.test' } },
    process: { env: { NEXT_PUBLIC_API_URL: '/api' } },
    setTimeout: (callback, delay) => { const id = ++nextTimer; timers.set(id, { callback, at: now + delay }); return id; },
    clearTimeout: (id) => timers.delete(id),
  });
  function load(filename) {
    if (modules.has(filename)) return modules.get(filename).exports;
    const compiled = ts.transpileModule(readFileSync(filename, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText;
    const loadedModule = { exports: {} };
    modules.set(filename, loadedModule);
    const run = vm.runInContext(`(function(require,module,exports) { ${compiled}\n })`, context);
    run((specifier) => {
      if (specifier === 'zustand') return { create };
      if (specifier === '@tanstack/react-query') return { useQueryClient: () => realQueryClient ?? queryClient };
      if (specifier === 'react') return {
        useRef: (value) => ({ current: value }), useCallback: (callback) => callback,
        useEffect: (effect) => effects.push(effect),
      };
      assert.ok(specifier.startsWith('.'), `Unexpected import ${specifier}`);
      return load(path.resolve(path.dirname(filename), `${specifier}.ts`));
    }, loadedModule, loadedModule.exports);
    return loadedModule.exports;
  }
  const store = load(path.join(sourceRoot, 'store.ts')).useRealtimeStore;
  const connectionModule = load(path.join(sourceRoot, 'connection.ts'));
  let refreshes = 0;
  const connection = connectionModule.createRealtimeConnection({
    baseUrl: () => 'wss://rapot.test/api/realtime/ws',
    getStore: store.getState,
    refreshSignals: () => refreshes++,
  });
  return {
    connection, store, sockets, attempts, failures, timers, effects, invalidations,
    get refreshes() { return refreshes; },
    load: (name) => load(path.join(sourceRoot, name)),
    latest(suffix) { return sockets.filter((socket) => socket.url.endsWith(suffix)).at(-1); },
    advance(ms) {
      const target = now + ms;
      let guard = 0;
      for (;;) {
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > target) break;
        assert.ok(guard++ < 1000, 'Timers must remain bounded');
        now = next[1].at;
        timers.delete(next[0]);
        next[1].callback();
      }
      now = target;
    },
  };
}

test('signal feed connects without a ticker, and ticker failures never close it', () => {
  const h = harness();
  h.failures.set('wss://rapot.test/api/realtime/ws/ticker', 2);
  h.connection.connect();
  const signals = h.latest('/signals');
  signals.open();
  assert.equal(h.refreshes, 1);
  h.advance(1000);
  assert.equal(signals.closeCount, 0);
  h.advance(2000);
  h.latest('/ticker').open();
  h.latest('/ticker').error();
  signals.message({ type: 'signal', data: sample });
  assert.equal(h.store.getState().realtimeSignals.length, 1);
  assert.equal(h.store.getState().signalConnectionState, 'connected');
  h.connection.dispose();
  assert.equal(h.timers.size, 0);
});

test('signal constructor errors and later disconnects retry independently and refresh REST on open', () => {
  const h = harness();
  h.failures.set('wss://rapot.test/api/realtime/ws/signals', 1);
  h.connection.connect();
  h.advance(1000);
  h.latest('/signals').open();
  assert.equal(h.refreshes, 1);
  h.latest('/signals').message({ type: 'signal', data: sample });
  h.latest('/signals').close();
  h.advance(1000);
  h.latest('/signals').open();
  assert.equal(h.refreshes, 2);
  assert.equal(h.store.getState().realtimeSignals.length, 0, 'Reconnect replaces old transient data from REST');
  h.connection.dispose();
});

test('intentional disconnect cancels every retry and ignores callbacks from retired sockets', () => {
  const h = harness();
  h.connection.connect();
  const old = h.latest('/signals');
  const lateOpen = old.onopen;
  const lateClose = old.onclose;
  const lateMessage = old.onmessage;
  h.latest('/ticker').error();
  h.connection.disconnect();
  const count = h.attempts.length;
  lateOpen({});
  lateClose({});
  lateMessage({ data: JSON.stringify({ type: 'signal', data: sample }) });
  h.advance(120_000);
  assert.equal(h.attempts.length, count);
  assert.equal(h.refreshes, 0);
  assert.equal(h.store.getState().realtimeSignals.length, 0);
  h.connection.connect();
  h.latest('/signals').open();
  lateClose({});
  assert.equal(h.store.getState().signalConnectionState, 'connected');
  h.connection.dispose();
  h.connection.connect();
  assert.equal(h.attempts.length, count + 2);
});

test('one minute of continuous events keeps REST refreshes bounded without starving, and resync clears stale signals', () => {
  const h = harness();
  h.connection.connect();
  const signals = h.latest('/signals');
  signals.open();
  for (let index = 0; index < 600; index++) {
    signals.message({ type: 'signal', data: { ...sample, specialTag: index ? 'COK_UCUZ' : 'BELES' } });
    h.advance(100);
  }
  assert.equal(h.refreshes, 3, 'Two refreshes per minute plus the connection refresh');
  assert.equal(h.store.getState().realtimeSignals.length, 1);
  assert.equal(h.store.getState().realtimeSignals[0].specialTag, 'COK_UCUZ');
  signals.message({ type: 'resync', reason: 'signal_feed_reset' });
  assert.equal(h.store.getState().realtimeSignals.length, 0);
  assert.equal(h.refreshes, 4);
  signals.message({ type: 'signal', data: { id: 3 } });
  signals.message('broken JSON');
  assert.equal(h.store.getState().realtimeSignals.length, 0);
  h.connection.dispose();
});

test('realtime store remains bounded and latest REST enrichment wins an ID collision', () => {
  const h = harness();
  for (let id = 1; id <= 70; id++) h.store.getState().addSignal({ ...sample, id });
  assert.equal(h.store.getState().realtimeSignals.length, 50);
  const { mergeSignals } = h.load('signals.ts');
  const rest = { ...sample, specialTag: 'COK_UCUZ', score: '+5/-0' };
  const merged = mergeSignals([rest], [sample, { ...sample, id: 2 }]);
  assert.equal(merged.length, 2);
  assert.equal(merged.find((signal) => signal.id === 1).specialTag, 'COK_UCUZ');
  assert.equal(merged.find((signal) => signal.id === 1).score, '+5/-0');
});

test('kline and trade subscriptions use dedicated endpoints, share duplicates, and release retries', () => {
  const h = harness();
  const stopFirst = h.connection.subscribe('kline', 'btcusdt', '4h');
  const stopSecond = h.connection.subscribe('kline', 'BTCUSDT', '4h');
  assert.equal(h.sockets.length, 1);
  const kline = h.latest('/kline/BTCUSDT?interval=4h');
  assert.ok(kline);
  kline.open();
  kline.message({ type: 'kline', data: { symbol: 'BTCUSDT', interval: '4h', close: 100 } });
  assert.equal(h.store.getState().klineData.get('BTCUSDT_4h').close, 100);
  stopFirst();
  assert.equal(kline.closeCount, 0);
  kline.error();
  stopSecond();
  stopSecond();
  h.advance(120_000);
  assert.equal(h.sockets.length, 1);
  const stopTrade = h.connection.subscribe('trade', 'ethusdt');
  const trades = h.latest('/trades/ETHUSDT');
  trades.open();
  trades.message({ type: 'trade', data: { symbol: 'ETHUSDT', tradeId: 1 } });
  assert.equal(h.store.getState().recentTrades[0].symbol, 'ETHUSDT');
  stopTrade();
  assert.equal(trades.closeCount, 1);
  assert.ok(!h.sockets.some((socket) => socket.url.endsWith('/ticker')));
  h.connection.dispose();
  assert.equal(h.timers.size, 0);
});

test('hook effect replay disposes old ownership and invalidates all signal query variants', () => {
  const h = harness();
  const { useRealtimeConnection } = h.load('use-realtime-connection.ts');
  useRealtimeConnection();
  const firstCleanups = h.effects.map((effect) => effect());
  const oldSignal = h.latest('/signals');
  const oldMessage = oldSignal.onmessage;
  firstCleanups.forEach((cleanup) => cleanup?.());
  const secondCleanups = h.effects.map((effect) => effect());
  assert.equal(h.sockets.filter((socket) => socket.readyState !== 3).length, 2);
  const newSignal = h.latest('/signals');
  newSignal.open();
  assert.deepEqual(h.invalidations, [
    ['signals'], ['signal-analysis'], ['analyses'], ['scanner-v2', 'signals'],
  ]);
  oldMessage({ data: JSON.stringify({ type: 'signal', data: sample }) });
  assert.equal(h.store.getState().realtimeSignals.length, 0);
  newSignal.message({ type: 'signal', data: sample });
  h.advance(30_000);
  assert.equal(h.invalidations.length, 8);
  newSignal.message({ type: 'signal', data: { ...sample, id: 2 } });
  secondCleanups.forEach((cleanup) => cleanup?.());
  h.advance(120_000);
  assert.equal(h.invalidations.length, 8);
  assert.equal(h.timers.size, 0);
});

test('opening signal socket preserves an active initial REST request instead of starting another', async () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  let requests = 0;
  let resolveRequest;
  const observer = new QueryObserver(queryClient, {
    queryKey: ['signals', 'special-notifications', 100],
    queryFn: () => { requests++; return new Promise((resolve) => { resolveRequest = resolve; }); },
  });
  const unsubscribe = observer.subscribe(() => {});
  const h = harness(queryClient);
  h.load('use-realtime-connection.ts').useRealtimeConnection();
  const cleanups = h.effects.map((effect) => effect());
  h.latest('/signals').open();
  assert.equal(requests, 1);
  resolveRequest([sample]);
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(queryClient.getQueryData(['signals', 'special-notifications', 100])[0].id, 1);
  assert.equal(requests, 1);
  cleanups.forEach((cleanup) => cleanup?.());
  unsubscribe();
  queryClient.clear();
});
