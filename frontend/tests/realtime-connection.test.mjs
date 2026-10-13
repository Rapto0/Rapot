import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import vm from 'node:vm';
import { create } from 'zustand';
import ts from 'typescript';

const sourceRoot = fileURLToPath(new URL('../src/lib/realtime/', import.meta.url));
const sample = { symbol: 'BTCUSDT', price: 100, priceChange: null, priceChangePercent: null };

function harness(realQueryClient, { token, guest = false } = {}) {
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
      this.sent = [];
      sockets.push(this);
    }
    open(authenticate = true) { this.readyState = 1; this.onopen?.({}); if (authenticate && this.sent.length) this.message({ type: 'authenticated' }); }
    send(raw) { this.sent.push(JSON.parse(raw)); }
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
      if (specifier === '../auth/session') return {
        getSession: () => guest ? null : { user: { username: 'admin', is_admin: true, disabled: false }, expiresAt: 123 },
        getAccessToken: () => guest ? null : 'session-token',
      };
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
    ...(token !== undefined ? { getToken: () => token } : {}),
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


test('only the price stream connects; retired signal messages create no state or requests', () => {
  const h = harness(); h.connection.connect();
  assert.deepEqual(h.attempts, ['wss://rapot.test/api/realtime/ws/ticker']);
  const socket = h.latest('/ticker'); socket.open();
  socket.message({ type: 'signal', data: { id: 7, symbol: 'SECRET' } });
  socket.message({ type: 'resync', reason: 'signal_feed_reset' });
  assert.equal(h.refreshes, 0); assert.deepEqual(h.invalidations, []);
  assert.equal(h.store.getState().tickers.size, 0);
  assert.ok(!Object.hasOwn(h.store.getState(), 'realtimeSignals'));
  h.connection.dispose(); assert.equal(h.timers.size, 0);
});

test('private ticker authenticates in first frame and ignores prices before acknowledgement', () => {
  const h = harness(undefined, { token: 'private-token' }); h.connection.connect();
  const socket = h.latest('/ticker'); socket.open(false);
  assert.deepEqual(socket.sent, [{ type: 'auth', token: 'private-token' }]);
  assert.doesNotMatch(socket.url, /private-token|token=/);
  assert.equal(h.store.getState().connectionState, 'connecting');
  socket.message({ type: 'ticker', data: sample }); assert.equal(h.store.getState().tickers.size, 0);
  socket.message({ type: 'authenticated' }); socket.message({ type: 'ticker', data: sample });
  assert.equal(h.store.getState().tickers.get('BTCUSDT').price, 100);
  assert.equal(h.store.getState().connectionState, 'connected'); h.connection.dispose();
});

test('auth rejection retires all price/kline sockets, clears data and never retries', () => {
  for (const code of [4401, 4403]) {
    const h = harness(undefined, { token: 'private-token' }); h.connection.connect();
    const socket = h.latest('/ticker'); socket.open(); socket.message({ type: 'ticker', data: sample });
    h.connection.subscribe('kline', 'BTCUSDT'); const count = h.sockets.length;
    socket.onclose({ code }); h.advance(120_000); h.connection.connect(); h.connection.subscribe('trade', 'ETHUSDT');
    assert.equal(h.sockets.length, count); assert.equal(h.store.getState().tickers.size, 0);
    assert.equal(h.store.getState().connectionState, 'disconnected');
    assert.ok(h.sockets.every(socket => socket.closeCount === 1)); assert.equal(h.timers.size, 0);
  }
});

test('absent auth prevents construction and acknowledgement has a bounded timeout', () => {
  const guest = harness(undefined, { token: null }); guest.connection.connect(); guest.connection.subscribe('kline', 'BTCUSDT');
  assert.equal(guest.sockets.length, 0);
  const h = harness(undefined, { token: 'private-token' }); h.connection.connect(); h.latest('/ticker').open(false);
  h.advance(5000); assert.ok(h.sockets.every(socket => socket.closeCount === 1)); assert.equal(h.timers.size, 0);
});

test('ticker constructor errors and disconnects retry without polling retired REST data', () => {
  const h = harness(); h.failures.set('wss://rapot.test/api/realtime/ws/ticker', 1);
  h.connection.connect(); h.advance(1000); h.latest('/ticker').open(); h.latest('/ticker').close();
  h.advance(1000); h.latest('/ticker').open(); assert.equal(h.refreshes, 0);
  assert.equal(h.store.getState().connectionState, 'connected'); h.connection.dispose();
});

test('intentional disconnect cancels retries and callbacks from retired sockets cannot update data', () => {
  const h = harness(); h.connection.connect(); const old = h.latest('/ticker');
  const lateOpen = old.onopen, lateClose = old.onclose, lateMessage = old.onmessage;
  old.error(); h.connection.disconnect(); const count = h.attempts.length;
  lateOpen({}); lateClose({}); lateMessage({ data: JSON.stringify({ type: 'ticker', data: sample }) });
  h.advance(120_000); assert.equal(h.attempts.length, count); assert.equal(h.store.getState().tickers.size, 0);
  h.connection.connect(); h.latest('/ticker').open(); lateClose({});
  assert.equal(h.store.getState().connectionState, 'connected'); h.connection.dispose(); h.connection.connect();
  assert.equal(h.attempts.length, count + 1);
});

test('hook effect replay retires old socket ownership and clears private market data', () => {
  const h = harness(); h.load('use-realtime-connection.ts').useRealtimeConnection();
  const first = h.effects.map(effect => effect()); const old = h.latest('/ticker'); const late = old.onmessage;
  first.forEach(cleanup => cleanup?.()); const second = h.effects.map(effect => effect());
  assert.equal(h.sockets.filter(socket => socket.readyState !== 3).length, 1);
  const current = h.latest('/ticker'); current.open();
  late({ data: JSON.stringify({ type: 'ticker', data: sample }) }); assert.equal(h.store.getState().tickers.size, 0);
  current.message({ type: 'ticker', data: sample }); assert.equal(h.store.getState().tickers.size, 1);
  assert.deepEqual(h.invalidations, []); second.forEach(cleanup => cleanup?.()); h.advance(120_000);
  assert.equal(h.store.getState().tickers.size, 0); assert.equal(h.timers.size, 0);
});
test('server crypto tickers retain valid prices and nullable daily changes across init and updates', () => {
  const h = harness();
  h.connection.connect();
  const socket = h.latest('/ticker');
  socket.open();
  socket.message({ type: 'init', crypto: { BTCUSDT: { symbol: 'BTCUSDT', price: 100, priceChange: null, priceChangePercent: null } } });
  assert.equal(h.store.getState().tickers.get('BTCUSDT').price, 100);
  assert.equal(h.store.getState().tickers.get('BTCUSDT').priceChangePercent, null);
  socket.message({ type: 'ticker', data: { symbol: 'BTCUSDT', price: 105, priceChange: 0, priceChangePercent: 0 } });
  assert.equal(h.store.getState().tickers.get('BTCUSDT').priceChangePercent, 0);
  socket.message({ type: 'ticker', data: { symbol: 'BTCUSDT', price: 106, priceChangePercent: '0' } });
  assert.equal(h.store.getState().tickers.get('BTCUSDT').price, 106);
  assert.equal(h.store.getState().tickers.get('BTCUSDT').priceChangePercent, null);
  assert.equal(h.store.getState().tickers.get('BTCUSDT').priceChange, null);
  socket.message({ type: 'ticker', data: { symbol: 'BTCUSDT', price: null, priceChange: 2, priceChangePercent: 2 } });
  assert.equal(h.store.getState().tickers.get('BTCUSDT').price, 106);
  h.connection.dispose();
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
