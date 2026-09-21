import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const compiled = ts.transpileModule(
  readFileSync(new URL('../src/lib/hooks/use-binance-ticker.ts', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;
const plain = value => JSON.parse(JSON.stringify(value));
const quote = (s = 'BTCUSDT', c = '123.5') => ({ s, c, p: '0', P: '0', E: 1 });

function harness({ symbols = ['BTCUSDT'], options, online = true, failures = 0, compatibility = false } = {}) {
  let now = 1_000_000;
  let timerId = 0;
  let position = 0;
  let updates = 0;
  let props = { symbols, options };
  let effects = [];
  const slots = [];
  const timers = new Map();
  const sockets = [];
  const attempts = [];
  const listeners = new Map();
  const different = (a, b) => !a || a.length !== b.length || b.some((value, i) => !Object.is(value, a[i]));
  const memo = (factory, deps) => {
    const index = position++;
    if (!slots[index] || different(slots[index].deps, deps)) slots[index] = { value: factory(), deps };
    return slots[index].value;
  };
  const hooks = {
    useState(initial) {
      const index = position++;
      if (!slots[index]) slots[index] = { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, value => {
        updates++;
        slots[index].value = typeof value === 'function' ? value(slots[index].value) : value;
      }];
    },
    useMemo: memo,
    useCallback: (callback, deps) => memo(() => callback, deps),
    useRef: initial => memo(() => ({ current: initial }), []),
    useEffect(effect, deps) {
      const index = position++;
      if (!slots[index] || different(slots[index].deps, deps)) {
        const previous = slots[index];
        slots[index] = { deps, effect, cleanup: previous?.cleanup };
        effects.push(() => {
          previous?.cleanup?.();
          slots[index].cleanup = effect();
        });
      }
    },
  };
  class Clock extends Date { static now() { return now; } }
  class Socket {
    static CONNECTING = 0;
    static OPEN = 1;
    constructor(url) {
      attempts.push({ url, at: now });
      if (failures-- > 0) throw new Error('Synthetic socket constructor failure');
      this.url = url;
      this.readyState = 0;
      this.closeCount = 0;
      sockets.push(this);
    }
    open() { this.readyState = 1; this.onopen?.({}); }
    message(value) { this.onmessage?.({ data: typeof value === 'string' ? value : JSON.stringify(value) }); }
    error() { this.onerror?.({}); }
    close(code = 1000) { this.readyState = 3; this.closeCount++; this.onclose?.({ code }); }
  }
  const window = {
    navigator: { onLine: online },
    setTimeout(callback, delay) {
      const id = ++timerId;
      timers.set(id, { callback, at: now + delay, delay });
      return id;
    },
    clearTimeout: id => timers.delete(id),
    addEventListener(name, callback) {
      if (!listeners.has(name)) listeners.set(name, new Set());
      listeners.get(name).add(callback);
    },
    removeEventListener: (name, callback) => listeners.get(name)?.delete(callback),
  };
  const context = vm.createContext({
    exports: {}, window, WebSocket: Socket, Date: Clock,
    fetch: () => assert.fail('Ticker tests must never use the network'),
    require(name) { assert.equal(name, 'react', 'Only fake React may be imported'); return hooks; },
  });
  vm.runInContext(compiled, context);
  const hook = context.exports[compatibility ? 'useBinanceTicker' : 'useBinanceTickerFeed'];
  const render = (nextProps = props, commit = true) => {
    props = nextProps;
    position = 0;
    const result = hook(props.symbols, props.options);
    if (!commit || !effects.length) return result;
    const scheduled = effects;
    effects = [];
    scheduled.forEach(effect => effect());
    return render(props, false);
  };
  const h = {
    render, read: () => render(), sockets, attempts, timers, listeners,
    latest: () => sockets.at(-1),
    get now() { return now; },
    get updates() { return updates; },
    advance(ms) {
      const target = now + ms;
      let guard = 0;
      for (;;) {
        const next = [...timers].sort((a, b) => a[1].at - b[1].at)[0];
        if (!next || next[1].at > target) break;
        assert.ok(guard++ < 1000, 'Timer activity must be bounded');
        now = next[1].at;
        timers.delete(next[0]);
        next[1].callback();
      }
      now = target;
    },
    connectivity(available) {
      window.navigator.onLine = available;
      for (const callback of listeners.get(available ? 'online' : 'offline') ?? []) callback();
    },
    unmount() { slots.forEach(slot => slot.cleanup?.()); },
    replayEffects() {
      slots.forEach(slot => { if (slot.effect) { slot.cleanup?.(); slot.cleanup = slot.effect(); } });
    },
  };
  h.render();
  return h;
}

test('normalizes, deduplicates and sorts subscriptions without reconnecting on array identity changes', () => {
  const h = harness({ symbols: ['ethusdt', ' BTCUSDT ', 'ETHUSDT', '', 'bad/symbol'] });
  assert.equal(h.read().status, 'connecting');
  assert.equal(h.latest().url, 'wss://stream.binance.com:9443/stream?streams=btcusdt@ticker/ethusdt@ticker');
  h.latest().open();
  assert.equal(h.read().status, 'connected');
  h.render({ symbols: ['BTCUSDT', 'ethusdt'] });
  assert.equal(h.sockets.length, 1);
  assert.equal(h.latest().closeCount, 0);
  assert.equal(h.timers.size, 0, 'Opening watchdog is cleared after open');
});

test('single and combined packets keep price/change/priceChange and record browser receipt time before flush', () => {
  const h = harness({ symbols: ['BTCUSDT', 'ETHUSDT'] });
  h.latest().open();
  h.latest().message(quote());
  h.advance(80);
  h.latest().message({ stream: 'ethusdt@ticker', data: { ...quote('ETHUSDT', '2000'), P: '-2.5', p: '-50' } });
  assert.deepEqual(plain(h.read().prices), {});
  assert.equal(h.timers.size, 1);
  h.advance(170);
  assert.deepEqual(plain(h.read().prices), {
    BTCUSDT: { price: 123.5, change: 0, priceChange: 0 },
    ETHUSDT: { price: 2000, change: -2.5, priceChange: -50 },
  });
  assert.deepEqual(plain(h.read().receivedAtBySymbol), { BTCUSDT: 1_000_000, ETHUSDT: 1_000_080 });
});

test('identical prices refresh receipt timestamps and bursts retain the latest valid receipt', () => {
  const h = harness();
  h.latest().open();
  h.latest().message(quote());
  h.advance(250);
  const initial = plain(h.read());
  h.latest().message(quote());
  h.advance(50);
  h.latest().message(quote());
  h.advance(200);
  assert.deepEqual(plain(h.read().prices), initial.prices);
  assert.equal(h.read().receivedAtBySymbol.BTCUSDT, 1_000_300);
});

test('malformed, unrequested and nonfinite packets cannot replace a valid price or receipt timestamp', () => {
  const h = harness();
  h.latest().open();
  h.latest().message(quote());
  h.advance(250);
  const before = plain(h.read());
  const malformed = ['{', 'null', '[]', 'true', '4', '{}', '{"data":null}', '{"data":[]}',
    quote('ETHUSDT'), { ...quote(), s: 1 }, { ...quote(), s: ' BTCUSDT ' }];
  for (const value of malformed) h.latest().message(value);
  for (const field of ['c', 'p', 'P']) {
    for (const value of ['', ' ', 'NaN', 'Infinity', '-Infinity', '1garbage', '0x10', null,
      undefined, [], {}, true, false, NaN, Infinity, -Infinity]) {
      h.latest().message({ ...quote(), [field]: value });
    }
  }
  h.latest().onmessage({ data: { ...quote(), c: 500 } });
  for (const c of ['0', '-1', 0, -1]) h.latest().message({ ...quote(), c });
  assert.equal(h.timers.size, 0, 'Rejected messages must not even schedule a flush');
  h.advance(5000);
  assert.deepEqual(plain(h.read()), before);
});

test('finite decimal/exponent strings and numeric zero changes are valid', () => {
  const h = harness();
  h.latest().open();
  h.latest().message({ ...quote('btcusdt', '1.25e2'), P: 0, p: '-.5' });
  h.advance(250);
  assert.deepEqual(plain(h.read().prices.BTCUSDT), { price: 125, change: 0, priceChange: -0.5 });
});

test('normal remote closes retry; socket error plus queued close owns only one retry', () => {
  for (const code of [1000, 1001, 1006]) {
    const h = harness();
    h.latest().open();
    h.latest().close(code);
    assert.equal(h.read().status, 'reconnecting');
    assert.equal(h.timers.size, 1);
    h.advance(1000);
    assert.equal(h.sockets.length, 2);
    const current = h.latest();
    current.open();
    const oldClose = current.onclose;
    current.error();
    oldClose({ code });
    assert.equal(h.timers.size, 1);
    assert.equal(current.closeCount, 1);
    h.advance(1000);
    assert.equal(h.sockets.length, 3);
    h.unmount();
  }
});

test('constructor exceptions retry with bounded 1/2/4/8/10 second backoff, reset after open', () => {
  const h = harness({ failures: 6 });
  assert.equal(h.read().status, 'reconnecting');
  for (const delay of [1000, 2000, 4000, 8000, 10000, 10000]) {
    const attempts = h.attempts.length;
    assert.equal(h.timers.size, 1);
    h.advance(delay - 1);
    assert.equal(h.attempts.length, attempts);
    h.advance(1);
    assert.equal(h.attempts.length, attempts + 1);
  }
  h.latest().open();
  h.latest().close();
  assert.equal([...h.timers.values()][0].delay, 1000);
});

test('opening watchdog retires a silent connecting socket after 20 seconds and cannot retire its successor', () => {
  const h = harness();
  const oldSocket = h.latest();
  const watchdog = [...h.timers.values()][0].callback;
  h.advance(19999);
  assert.equal(oldSocket.closeCount, 0);
  h.advance(1);
  assert.equal(oldSocket.closeCount, 1);
  assert.equal(h.read().status, 'reconnecting');
  h.advance(1000);
  h.latest().open();
  watchdog();
  assert.equal(h.read().status, 'connected');
  assert.equal(h.latest().closeCount, 0);
  assert.equal(h.timers.size, 0);
});

test('an opening watchdog already queued before open cannot close the now-connected socket', () => {
  const h = harness();
  const watchdog = [...h.timers.values()][0].callback;
  h.latest().open();
  watchdog();
  assert.equal(h.read().status, 'connected');
  assert.equal(h.latest().closeCount, 0);
  assert.equal(h.timers.size, 0);
});

test('manual reconnect closes the current socket and discards its pending flush and every late event', () => {
  const h = harness();
  const old = h.latest();
  old.open();
  old.message(quote());
  const lateFlush = [...h.timers.values()][0].callback;
  const lateEvents = [old.onopen, old.onmessage, old.onerror, old.onclose];
  const reconnect = h.read().reconnect;
  reconnect();
  assert.equal(h.read().reconnect, reconnect, 'Public reconnect callback stays stable');
  assert.equal(old.closeCount, 1);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.read().status, 'reconnecting');
  const writes = h.updates;
  lateEvents.forEach(callback => callback({ data: JSON.stringify(quote()), code: 1000 }));
  lateFlush();
  assert.equal(h.updates, writes);
  h.latest().open();
  h.advance(1000);
  assert.deepEqual(plain(h.read().prices), {});
  assert.equal(h.sockets.length, 2);
});

test('manual reconnect cancels pending retry, including a saved callback already queued by the browser', () => {
  const h = harness();
  h.latest().close();
  const lateRetry = [...h.timers.values()][0].callback;
  h.read().reconnect();
  h.latest().open();
  lateRetry();
  h.advance(30000);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.timers.size, 0);
  assert.equal(h.read().status, 'connected');
});

test('symbol changes hide removed prices immediately and ignore the previous socket and pending flush', () => {
  const h = harness();
  h.latest().open();
  h.latest().message(quote());
  h.advance(250);
  const old = h.latest();
  old.message(quote('BTCUSDT', '400'));
  const lateMessage = old.onmessage;
  const lateFlush = [...h.timers.values()][0].callback;
  const firstRender = h.render({ symbols: ['ETHUSDT'] }, false);
  assert.deepEqual(plain(firstRender.prices), {});
  assert.deepEqual(plain(firstRender.receivedAtBySymbol), {});
  assert.equal(firstRender.status, 'connecting');
  h.read();
  assert.equal(old.closeCount, 1);
  lateMessage({ data: JSON.stringify(quote()) });
  lateFlush();
  h.latest().open();
  h.latest().message(quote('BTCUSDT'));
  h.latest().message(quote('ETHUSDT', '600'));
  h.advance(250);
  assert.deepEqual(Object.keys(h.read().prices), ['ETHUSDT']);
  assert.deepEqual(Object.keys(h.read().receivedAtBySymbol), ['ETHUSDT']);
  assert.equal(h.read().prices.ETHUSDT.price, 600);
});

test('paused compatibility hook retains the exact quote shape, honors 320ms batching and cancels stale events', () => {
  const h = harness({ compatibility: true, options: { flushIntervalMs: 320 } });
  const old = h.latest();
  old.open();
  old.message(quote());
  h.advance(319);
  assert.deepEqual(plain(h.read()), {});
  h.advance(1);
  assert.deepEqual(plain(h.read()), { BTCUSDT: { price: 123.5, change: 0, priceChange: 0 } });
  old.message(quote('BTCUSDT', '800'));
  const lateFlush = [...h.timers.values()][0].callback;
  const lateEvents = [old.onmessage, old.onclose];
  h.render({ symbols: ['BTCUSDT'], options: { paused: true, flushIntervalMs: 320 } });
  const writes = h.updates;
  lateEvents.forEach(callback => callback({ data: JSON.stringify(quote()), code: 1000 }));
  lateFlush();
  h.advance(60000);
  assert.equal(h.updates, writes);
  assert.equal(h.timers.size, 0);
  assert.equal(h.sockets.length, 1);
  assert.equal(old.closeCount, 1);
  h.render({ symbols: ['BTCUSDT'], options: { paused: false, flushIntervalMs: 320 } });
  assert.equal(h.sockets.length, 2);
});

test('paused and empty subscriptions never open sockets; reconnect is inert until enabled', () => {
  const h = harness({ options: { paused: true } });
  assert.equal(h.read().status, 'paused');
  h.read().reconnect();
  assert.equal(h.attempts.length, 0);
  h.render({ symbols: [], options: {} });
  assert.equal(h.read().status, 'offline');
  h.read().reconnect();
  h.advance(60000);
  assert.equal(h.attempts.length, 0);
  assert.deepEqual(plain(h.read().prices), {});
});

test('offline state suppresses retries, closes sockets and resumes once on a browser online event', () => {
  const h = harness({ online: false });
  assert.equal(h.read().status, 'offline');
  assert.equal(h.attempts.length, 0);
  h.read().reconnect();
  assert.equal(h.timers.size, 0);
  h.connectivity(true);
  h.connectivity(true);
  assert.equal(h.sockets.length, 1);
  h.latest().open();
  const old = h.latest();
  old.message(quote());
  h.connectivity(false);
  assert.equal(old.closeCount, 1);
  assert.equal(h.read().status, 'offline');
  assert.equal(h.timers.size, 0);
  h.advance(60000);
  assert.equal(h.sockets.length, 1);
  h.connectivity(true);
  assert.equal(h.sockets.length, 2);
});

test('unmount removes listeners and cancels timers; saved socket, timer and reconnect callbacks stay inert', () => {
  for (const state of ['opening', 'pending', 'retrying']) {
    const h = harness();
    const old = h.latest();
    const callbacks = [old.onopen, old.onmessage, old.onerror, old.onclose];
    if (state === 'pending') { old.open(); old.message(quote()); }
    if (state === 'retrying') old.close();
    const scheduled = [...h.timers.values()].map(timer => timer.callback);
    const reconnect = h.read().reconnect;
    h.unmount();
    const writes = h.updates;
    assert.equal(h.timers.size, 0);
    assert.ok([...h.listeners.values()].every(set => set.size === 0));
    callbacks.forEach(callback => callback({ data: JSON.stringify(quote()), code: 1000 }));
    scheduled.forEach(callback => callback());
    reconnect();
    h.advance(60000);
    assert.equal(h.updates, writes);
    assert.equal(h.attempts.length, 1);
  }
});

test('Strict Mode effect cleanup/setup keeps one active socket and rejects callbacks from the first setup', () => {
  const h = harness();
  const old = h.latest();
  const lateOpen = old.onopen;
  const lateClose = old.onclose;
  h.replayEffects();
  assert.equal(old.closeCount, 1);
  assert.equal(h.sockets.length, 2);
  assert.equal(h.timers.size, 1);
  h.latest().open();
  lateOpen({});
  lateClose({ code: 1006 });
  assert.equal(h.read().status, 'connected');
  assert.equal(h.timers.size, 0);
});

test('invalid flush intervals remain bounded; the lower bound is 100ms', () => {
  for (const [flushIntervalMs, expected] of [[-20, 100], [NaN, 250], [Infinity, 250]]) {
    const h = harness({ options: { flushIntervalMs } });
    h.latest().open();
    h.latest().message(quote());
    assert.equal([...h.timers.values()][0].delay, expected);
    h.advance(expected);
    assert.equal(h.read().prices.BTCUSDT.price, 123.5);
    h.unmount();
  }
});
