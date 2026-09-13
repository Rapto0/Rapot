import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

function loadSource(path, imports = {}, globals = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({ exports: {}, ...globals, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(compiled, context);
  return context.exports;
}

const indicators = loadSource('../src/lib/indicators.ts');
const alarms = loadSource('../src/lib/watchlist-alarms.ts', { '@/lib/indicators': indicators });
const rule = (overrides = {}) => ({
  id: 'rule-1', watchlistId: 'list-1', watchlistName: 'Test list', indicator: 'rsi', timeframe: '1d',
  enabled: true, thresholds: { ...alarms.DEFAULT_ALARM_THRESHOLDS },
  createdAt: '2026-09-10T10:00:00Z', updatedAt: '2026-09-10T10:00:00Z', ...overrides,
});
const symbol = rawSymbol => ({ kind: 'symbol', rawSymbol, marketType: 'Kripto' });
const configuration = (symbols = ['BTCUSDT'], rules = [rule()]) => ({
  rules, watchlists: [{ id: 'list-1', name: 'Test list', alarmsEnabled: true, notes: '', rows: symbols.map(symbol) }],
});
const candles = (count = 40, delta = 0) => Array.from({ length: count }, (_, index) => {
  const close = 100 + index * delta;
  return { time: new Date(Date.UTC(2026, 0, index + 1)).toISOString(), open: close, close,
    high: close + 1, low: close - 1, volume: 100 };
});
const noHit = candles();
const hit = candles(40, -1);
function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const flush = async () => { for (let i = 0; i < 25; i++) await Promise.resolve(); };

function fakeTimers() {
  let nextId = 0;
  const intervals = new Map();
  const timeouts = new Map();
  return { intervals, timeouts,
    setInterval: (callback, delay) => { const id = ++nextId; intervals.set(id, { callback, delay }); return id; },
    clearInterval: id => intervals.delete(id),
    setTimeout: (callback, delay) => { const id = ++nextId; timeouts.set(id, { callback, delay }); return id; },
    clearTimeout: id => timeouts.delete(id),
    tick: () => { for (const { callback } of [...intervals.values()]) callback(); },
    expire: () => { for (const [id, { callback }] of [...timeouts]) { timeouts.delete(id); callback(); } },
  };
}

function monitorFixture(readCandles, onUpdate) {
  const timers = fakeTimers();
  const updates = [];
  const moduleExports = loadSource('../src/lib/local-alarm-monitor.ts', { './watchlist-alarms': alarms }, {
    AbortController, ...timers,
  });
  const monitor = moduleExports.createLocalAlarmMonitor({ readCandles,
    onUpdate: snapshot => { updates.push(snapshot); onUpdate?.(snapshot); },
  });
  return { monitor, timers, updates, moduleExports, latest: () => updates.at(-1) };
}

test('RSI/W%R distinguish valid hit, no hit and measured zero without changing thresholds', () => {
  const dip = alarms.evaluateWatchlistAlarmRule(rule(), hit);
  assert.equal(dip.state, 'hit');
  assert.equal(dip.side, 'dip');
  assert.equal(dip.value, 0);
  const neutral = alarms.evaluateWatchlistAlarmRule(rule(), noHit);
  assert.equal(neutral.state, 'no_hit');
  assert.equal(neutral.value, 50);
  const top = alarms.evaluateWatchlistAlarmRule(rule(), candles(40, 1));
  assert.equal(top.state, 'hit');
  assert.equal(top.side, 'top');
  assert.equal(top.value, 100);
  const wr = rule({ indicator: 'wr' });
  assert.equal(alarms.evaluateWatchlistAlarmRule(wr, noHit).state, 'no_hit');
  const closeAtHigh = candles().map(candle => ({ ...candle, close: candle.high }));
  const wrTop = alarms.evaluateWatchlistAlarmRule(wr, closeAtHigh);
  assert.equal(wrTop.state, 'hit');
  assert.equal(wrTop.side, 'top');
  assert.ok(wrTop.value === 0);
});

test('empty, insufficient and malformed candles cannot be represented as a successful no hit', () => {
  assert.equal(alarms.evaluateWatchlistAlarmRule(rule(), []).state, 'no_data');
  for (const [indicator, count] of [['rsi', 14], ['wr', 13], ['combo', 25], ['hunter', 29]]) {
    assert.equal(alarms.evaluateWatchlistAlarmRule(rule({ indicator }), candles(count)).state, 'unknown');
  }
  for (const invalid of [null, {}, [null], [...noHit, { ...noHit.at(-1), close: NaN }],
    [...noHit, { ...noHit.at(-1), time: 'invalid' }], [...noHit, { ...noHit.at(-1), volume: -1 }],
    [...noHit, { ...noHit.at(-1), high: 50 }]]) {
    const result = alarms.evaluateWatchlistAlarmRule(rule(), invalid);
    assert.equal(result.state, 'unknown');
    assert.equal(result.triggered, false);
    assert.equal(result.value, null);
  }
});

test('latest unavailable indicator never reuses a previous finite reading', () => {
  const controlled = loadSource('../src/lib/watchlist-alarms.ts', { '@/lib/indicators': {
    ...indicators, calculateRSI: () => [{ value: 20 }, { value: NaN }],
    calculateWilliamsR: () => [{ value: -90 }, { value: Infinity }],
  } });
  for (const indicator of ['rsi', 'wr']) {
    assert.equal(controlled.evaluateWatchlistAlarmRule(rule({ indicator }), noHit).state, 'unknown');
  }
});

test('COMBO/HUNTER retain score and signal requirements and reject unavailable components', () => {
  for (const indicator of ['combo', 'hunter']) {
    let latest;
    let received;
    const method = indicator === 'combo' ? 'calculateCombo' : 'calculateHunter';
    const controlled = loadSource('../src/lib/watchlist-alarms.ts', { '@/lib/indicators': {
      ...indicators, [method]: (_candles, options) => { received = options; return [latest]; },
    } });
    const selectedRule = rule({ indicator });
    latest = { buyScore: 2, sellScore: 0, dipScore: 3, topScore: 0, signal: 'AL', details: { rsi: 20 } };
    assert.equal(controlled.evaluateWatchlistAlarmRule(selectedRule, noHit).state, 'hit');
    assert.equal(received[indicator === 'combo' ? 'minBuyScore' : 'requiredDipScore'], indicator === 'combo' ? 2 : 3);
    latest = { ...latest, signal: null };
    assert.equal(controlled.evaluateWatchlistAlarmRule(selectedRule, noHit).state, 'no_hit');
    latest = { ...latest, signal: 'AL', details: { rsi: NaN } };
    assert.equal(controlled.evaluateWatchlistAlarmRule(selectedRule, noHit).state, 'unknown');
  }
});

test('real COMBO preserves RSI zero and produces a four-vote buy alarm', () => {
  const falling = candles(40, -1);
  assert.equal(indicators.calculateRSI(falling).at(-1).value, 0);
  const latest = indicators.calculateCombo(falling, { minBuyScore: 4 }).at(-1);
  assert.equal(latest.details.rsi, 0);
  assert.equal(latest.buyScore, 4);
  assert.equal(latest.sellScore, 0);
  assert.equal(latest.signal, 'AL');
  const selected = rule({ indicator: 'combo', thresholds: {
    ...alarms.DEFAULT_ALARM_THRESHOLDS, comboDipThreshold: 4,
  } });
  const result = alarms.evaluateWatchlistAlarmRule(selected, falling);
  assert.equal(result.state, 'hit');
  assert.equal(result.triggered, true);
  assert.equal(result.side, 'dip');
  assert.equal(result.value, 4);
});

test('real COMBO preserves Williams zero and produces a three-vote sell alarm', () => {
  const rising = candles(40, 1).map(candle => ({ ...candle, close: candle.high }));
  const measuredWr = indicators.calculateWilliamsR(rising).at(-1).value;
  assert.ok(measuredWr === 0);
  const latest = indicators.calculateCombo(rising, { minSellScore: 3 }).at(-1);
  assert.equal(latest.details.wr, measuredWr);
  assert.equal(latest.buyScore, 0);
  assert.equal(latest.sellScore, 3);
  assert.equal(latest.signal, 'SAT');
  const selected = rule({ indicator: 'combo', thresholds: {
    ...alarms.DEFAULT_ALARM_THRESHOLDS, comboTopThreshold: 3,
  } });
  const result = alarms.evaluateWatchlistAlarmRule(selected, rising);
  assert.equal(result.state, 'hit');
  assert.equal(result.triggered, true);
  assert.equal(result.side, 'top');
  assert.equal(result.value, 3);
});

test('real COMBO unavailable warmup values cannot create votes under custom thresholds', () => {
  const series = indicators.calculateCombo(noHit, {
    rsiBuyThreshold: 60, wrBuyThreshold: -40, cciBuyThreshold: 10, minBuyScore: 3,
  });
  assert.equal(series.length, noHit.length);
  const first = series[0];
  assert.equal(first.buyScore, 0);
  assert.equal(first.sellScore, 0);
  assert.equal(first.signal, null);
  for (const name of ['rsi', 'wr', 'cci']) assert.ok(Number.isNaN(first.details[name]));
  // Once measured, the same thresholds may legitimately count the finite flat values.
  const latest = series.at(-1);
  assert.equal(latest.details.cci, 0);
  assert.equal(latest.buyScore, 3);
  assert.equal(latest.signal, 'AL');
});

test('real COMBO finite flat values remain neutral at the 26-bar boundary and later', () => {
  for (const count of [26, 40]) {
    const flat = candles(count);
    const series = indicators.calculateCombo(flat);
    assert.equal(series.length, count);
    const latest = series.at(-1);
    assert.equal(latest.details.macd, 0);
    assert.equal(latest.details.cci, 0);
    assert.equal(latest.details.rsi, 50);
    assert.equal(latest.details.wr, -50);
    assert.equal(latest.buyScore, 0);
    assert.equal(latest.sellScore, 0);
    assert.equal(latest.signal, null);
    const result = alarms.evaluateWatchlistAlarmRule(rule({ indicator: 'combo' }), flat);
    assert.equal(result.state, 'no_hit');
    assert.equal(result.triggered, false);
  }
});

test('real COMBO retains derived NaN so finite-input overflow is an unknown alarm', () => {
  const overflow = candles().map(candle => ({
    ...candle, open: 1e308, close: 1e308, high: 1.1e308, low: 9e307,
  }));
  assert.ok(overflow.every(candle =>
    [candle.open, candle.high, candle.low, candle.close, candle.volume].every(Number.isFinite)));
  assert.ok(Number.isNaN(indicators.calculateMACD(overflow).at(-1).macd));
  assert.ok(Number.isNaN(indicators.calculateCCI(overflow).at(-1).value));
  const latest = indicators.calculateCombo(overflow).at(-1);
  assert.ok(Number.isNaN(latest.details.macd));
  assert.ok(Number.isNaN(latest.details.cci));
  assert.equal(latest.buyScore, 0);
  assert.equal(latest.sellScore, 0);
  assert.equal(latest.signal, null);
  const result = alarms.evaluateWatchlistAlarmRule(rule({ indicator: 'combo' }), overflow);
  assert.equal(result.state, 'unknown');
  assert.equal(result.triggered, false);
  assert.equal(result.value, null);
});

test('real COMBO never awards a buy vote to negative Infinity at 26 bars', () => {
  const overflow = candles(26).map(candle => ({
    ...candle, open: 1e307, close: 1e307, high: 1.1e307, low: 9e306,
  }));
  assert.ok(overflow.every(candle =>
    [candle.open, candle.high, candle.low, candle.close, candle.volume].every(Number.isFinite)));
  assert.equal(indicators.calculateMACD(overflow).at(-1).macd, -Infinity);
  const series = indicators.calculateCombo(overflow, { minBuyScore: 1 });
  assert.equal(series.length, 26);
  const latest = series.at(-1);
  assert.equal(latest.details.macd, -Infinity);
  assert.equal(latest.buyScore, 0);
  assert.equal(latest.sellScore, 0);
  assert.equal(latest.signal, null);
  const selected = rule({ indicator: 'combo', thresholds: {
    ...alarms.DEFAULT_ALARM_THRESHOLDS, comboDipThreshold: 1,
  } });
  const result = alarms.evaluateWatchlistAlarmRule(selected, overflow);
  assert.equal(result.state, 'unknown');
  assert.equal(result.triggered, false);
});

test('manual and 60-second triggers share one active pass with at most four reads', async () => {
  const requests = [];
  const fixture = monitorFixture((row, _rule, signal) => {
    const request = { ...deferred(), row, signal };
    requests.push(request);
    return request.promise;
  });
  const { monitor, timers, latest } = fixture;
  try {
    const pass = monitor.replace(configuration(['A', 'B', 'C', 'D', 'E', 'E']));
    await flush();
    assert.equal(requests.length, 4);
    assert.equal([...timers.intervals.values()][0].delay, 60_000);
    assert.strictEqual(monitor.run(), pass);
    timers.tick();
    await flush();
    assert.equal(requests.length, 4);
    requests[0].resolve(noHit);
    await flush();
    assert.equal(requests.length, 5);
    requests.slice(1).forEach(request => request.resolve(noHit));
    await pass;
    assert.equal(latest().isChecking, false);
    assert.equal(latest().runtimeByRuleId['rule-1'].state, 'no_hit');
    assert.equal(latest().runtimeByRuleId['rule-1'].checkedSymbols, 5);
    assert.equal(timers.timeouts.size, 0);
    assert.ok(latest().lastCheckedAt);
  } finally { monitor.dispose(); }
});

test('rule edits, removal, disabling and watchlist changes abort and reject late results', async t => {
  const cases = {
    edit: () => configuration(['BTCUSDT'], [rule({ timeframe: '4h' })]),
    delete: () => configuration(['BTCUSDT'], []),
    disable: () => configuration(['BTCUSDT'], [rule({ enabled: false })]),
    symbols: () => configuration(['ETHUSDT']),
    listDisabled: () => ({ ...configuration(), watchlists: [{ ...configuration().watchlists[0], alarmsEnabled: false }] }),
    listDeleted: () => ({ ...configuration(), watchlists: [] }),
  };
  for (const [name, replacement] of Object.entries(cases)) await t.test(name, async () => {
    const requests = [];
    const { monitor, updates, latest } = monitorFixture((row, selectedRule, signal) => {
      const request = { ...deferred(), row, selectedRule, signal };
      requests.push(request);
      return request.promise;
    });
    try {
      const oldPass = monitor.replace(configuration());
      await flush();
      const next = replacement();
      const newPass = monitor.replace(next);
      await flush();
      assert.equal(requests[0].signal.aborted, true);
      requests.slice(1).forEach(request => request.resolve(noHit));
      await newPass;
      const published = updates.length;
      requests[0].resolve(hit);
      await oldPass;
      await flush();
      assert.equal(updates.length, published, 'Old result cannot overwrite the new configuration');
      assert.equal(latest().key, JSON.stringify(next));
      assert.equal(Object.values(latest().runtimeByRuleId).flatMap(item => item.triggerHits).length, 0);
      if (name === 'delete') assert.equal(Object.keys(latest().runtimeByRuleId).length, 0);
      if (name === 'disable' || name === 'listDisabled') assert.equal(latest().runtimeByRuleId['rule-1'].state, 'disabled');
      if (name === 'listDeleted') assert.equal(latest().runtimeByRuleId['rule-1'].state, 'unknown');
      if (name === 'edit') assert.equal(requests[1].selectedRule.timeframe, '4h');
      if (name === 'symbols') assert.equal(requests[1].row.rawSymbol, 'ETHUSDT');
    } finally { monitor.dispose(); }
  });
});

test('unmount/dispose cancels reads and all timers; late rejection cannot publish or restart', async () => {
  const request = deferred();
  let signal;
  let reads = 0;
  const { monitor, timers, updates } = monitorFixture((_row, _rule, suppliedSignal) => {
    reads++; signal = suppliedSignal; return request.promise;
  });
  const pass = monitor.replace(configuration());
  await flush();
  const count = updates.length;
  monitor.dispose();
  assert.equal(signal.aborted, true);
  assert.equal(timers.intervals.size, 0);
  assert.equal(timers.timeouts.size, 0);
  request.reject(new Error('Late secret-bearing adapter error must not escape'));
  await pass;
  await monitor.run();
  await monitor.replace(configuration(['ETHUSDT']));
  timers.tick();
  await flush();
  assert.equal(updates.length, count);
  assert.equal(reads, 1);
});

test('20-second read timeout settles even an adapter ignoring abort and allows another pass', async () => {
  const requests = [];
  const { monitor, timers, latest, updates } = monitorFixture((_row, _rule, signal) => {
    const request = { ...deferred(), signal }; requests.push(request); return request.promise;
  });
  try {
    const first = monitor.replace(configuration());
    await flush();
    assert.equal([...timers.timeouts.values()][0].delay, 20_000);
    timers.expire();
    await first;
    assert.equal(requests[0].signal.aborted, true);
    assert.equal(latest().runtimeByRuleId['rule-1'].state, 'error');
    assert.match(latest().runtimeByRuleId['rule-1'].errors[0], /zaman aşımı/);
    const second = monitor.run();
    await flush();
    requests[1].resolve(noHit);
    await second;
    const count = updates.length;
    requests[0].resolve(hit);
    await flush();
    assert.equal(updates.length, count);
    assert.equal(latest().runtimeByRuleId['rule-1'].state, 'no_hit');
  } finally { monitor.dispose(); }
});

test('unavailable and failed reads remain distinct, partial passes keep only measured hits', async () => {
  for (const [rows, expected, checked, hits] of [
    [['EMPTY'], 'no_data', 0, 0], [['ERROR'], 'error', 0, 0], [['SHORT'], 'unknown', 0, 0],
    [['OK'], 'no_hit', 1, 0], [['HIT'], 'hit', 1, 1],
    [['HIT', 'EMPTY', 'ERROR', 'SHORT'], 'partial', 1, 1],
  ]) {
    const { monitor, latest } = monitorFixture(async row => {
      if (row.rawSymbol === 'ERROR') throw new Error('Private request URL');
      return { EMPTY: [], SHORT: candles(3), OK: noHit, HIT: hit }[row.rawSymbol];
    });
    try {
      await monitor.replace(configuration(rows));
      const runtime = latest().runtimeByRuleId['rule-1'];
      assert.equal(runtime.state, expected);
      assert.equal(runtime.checkedSymbols, checked);
      assert.equal(runtime.triggerHits.length, hits);
      assert.doesNotMatch(JSON.stringify(latest()), /Private request URL/);
    } finally { monitor.dispose(); }
  }
});

test('disabled or empty lists do not issue reads or claim a measured result', async () => {
  for (const next of [configuration([], [rule()]), configuration(['BTCUSDT'], [rule({ enabled: false })]),
    { ...configuration(), watchlists: [] }]) {
    const { monitor, latest } = monitorFixture(() => assert.fail('No read authorized by this configuration'));
    try {
      await monitor.replace(next);
      assert.notEqual(latest().runtimeByRuleId['rule-1'].state, 'no_hit');
      assert.equal(latest().runtimeByRuleId['rule-1'].checkedAt, null);
    } finally { monitor.dispose(); }
  }
});

// A deterministic hook harness runs effect setup/cleanup and renders without a browser or DOM.
function hookHarness() {
  const slots = [];
  let position = 0;
  let pending = [];
  let updates = 0;
  const memo = (value, deps) => {
    const index = position++;
    if (!slots[index] || deps.some((dep, i) => !Object.is(dep, slots[index].deps[i]))) slots[index] = { deps, value: value() };
    return slots[index].value;
  };
  const hooks = {
    useState(initial) {
      const index = position++;
      if (!slots[index]) slots[index] = { value: initial };
      return [slots[index].value, next => { updates++; slots[index].value = next; }];
    },
    useRef: initial => memo(() => ({ current: initial }), []),
    useMemo: memo,
    useCallback: (callback, deps) => memo(() => callback, deps),
    useEffect(effect, deps) {
      const index = position++;
      if (!slots[index] || deps.some((dep, i) => !Object.is(dep, slots[index].deps[i]))) {
        const oldCleanup = slots[index]?.cleanup;
        slots[index] = { deps };
        pending.push(() => { oldCleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  return { hooks,
    render: callback => { position = 0; return callback(); },
    commit: () => { const effects = pending; pending = []; effects.forEach(effect => effect()); },
    unmount: () => slots.forEach(slot => slot.cleanup?.()),
    updateCount: () => updates,
  };
}

test('hook forwards AbortSignal and hides old configuration results before effects, then cleans up on unmount', async () => {
  const harness = hookHarness();
  const requests = [];
  const fixture = monitorFixture(() => assert.fail('Hook must supply its own reader'));
  const hook = loadSource('../src/lib/hooks/use-local-alarms.ts', {
    react: harness.hooks, '@/lib/local-alarm-monitor': fixture.moduleExports,
    '@/lib/api/client': { fetchCandles: (...args) => {
      const request = { ...deferred(), args }; requests.push(request); return request.promise;
    } },
  });
  let current = configuration();
  const render = () => harness.render(() => hook.useLocalAlarms(current.rules, current.watchlists, true));
  render();
  harness.commit();
  await flush();
  assert.equal(requests.length, 1);
  assert.deepEqual(requests[0].args.slice(0, 4), ['BTCUSDT', 'Kripto', '1d', 320]);
  assert.equal(requests[0].args[4].signal.aborted, false);
  requests[0].resolve({ candles: hit });
  await flush();
  assert.equal(render().runtimeByRuleId['rule-1'].state, 'hit');
  current = configuration(['ETHUSDT']);
  const betweenRenderAndEffect = render();
  assert.equal(Object.keys(betweenRenderAndEffect.runtimeByRuleId).length, 0);
  assert.equal(betweenRenderAndEffect.isChecking, true);
  harness.commit();
  await flush();
  const count = harness.updateCount();
  harness.unmount();
  assert.equal(requests[1].args[4].signal.aborted, true);
  assert.equal(fixture.timers.intervals.size, 0);
  assert.equal(fixture.timers.timeouts.size, 0);
  requests[1].resolve({ candles: hit });
  await flush();
  assert.equal(harness.updateCount(), count);
});

function renderPage(runtime, isChecking = false) {
  let stateIndex = 0;
  const states = [configuration().watchlists, [rule()], true, null];
  const page = loadSource('../src/app/alarms/page.tsx', {
    react: { ...React, useState: () => [states[stateIndex++], () => {}] },
    'react/jsx-runtime': jsxRuntime, 'lucide-react': icons,
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    '@/lib/watchlist-alarms': alarms,
    '@/lib/alarm-rule-storage': {
      readAlarmRuleStorage: () => assert.fail('No storage reads during render'),
      updateAlarmRuleStorage: () => assert.fail('No storage writes during render'),
    },
    '@/lib/hooks/use-local-alarms': { useLocalAlarms: () => ({ isChecking,
      runtimeByRuleId: runtime ? { 'rule-1': runtime } : {}, lastCheckedAt: null, run() {} }) },
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

test('page labels unknown/no data/error/partial separately and explains this-browser page-open-only polling', () => {
  for (const [state, label] of [['unknown', 'Sonuç bilinmiyor'], ['no_data', 'Veri yok'],
    ['error', 'Veri alınamadı'], ['partial', 'Kısmi kontrol'], ['disabled', 'Kontrol kapalı']]) {
    const html = renderPage({ state, checkedAt: null, checkedSymbols: 0, triggerHits: [], errors: [] });
    assert.ok(html.includes(label));
    assert.doesNotMatch(html, /Tetik yok\./);
    assert.match(html, /yalnız bu tarayıcıda/);
    assert.match(html, /60 saniyede/);
    assert.match(html, /Sayfa kapanınca kontroller durur/);
    assert.match(html, /Telegram bildirimi veya 7\/24 arka plan hizmeti değildir/);
  }
  const noHitHtml = renderPage({ state: 'no_hit', checkedAt: '2026-09-10T10:00:00Z', checkedSymbols: 1, triggerHits: [], errors: [] });
  assert.match(noHitHtml, /Tetik yok\./);
  assert.match(renderPage(null, true), /<button[^>]*disabled=""/);
  assert.match(renderPage(null), /Henüz kontrol edilmedi/);
});

test('page hydration/storage events only read; user toggle/delete submit intents and surface save failure', () => {
  const states = [configuration().watchlists, [rule()], true, null];
  let stateIndex = 0;
  const effects = [];
  const listeners = new Map();
  const changes = [];
  let reads = 0;
  let result = { ok: true, rules: [rule({ enabled: false }), rule({ id: 'peer-rule' })] };
  const makeNode = (type, props) => ({ type, props });
  const page = loadSource('../src/app/alarms/page.tsx', {
    react: {
      useState: () => {
        const index = stateIndex++;
        return [states[index], value => { states[index] = value; }];
      },
      useMemo: factory => factory(), useCallback: callback => callback,
      useEffect: callback => effects.push(callback),
    },
    'react/jsx-runtime': { jsx: makeNode, jsxs: makeNode }, 'lucide-react': icons,
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    '@/lib/watchlist-alarms': { ...alarms, loadStoredWatchlists: () => configuration().watchlists },
    '@/lib/alarm-rule-storage': {
      readAlarmRuleStorage: () => { reads++; return { ok: true, rules: [rule()] }; },
      updateAlarmRuleStorage: change => { changes.push(change); return result; },
    },
    '@/lib/hooks/use-local-alarms': { useLocalAlarms: () => ({ isChecking: false,
      runtimeByRuleId: {}, lastCheckedAt: null, run() {} }) },
  }, { window: {
    addEventListener: (name, callback) => listeners.set(name, callback),
    removeEventListener: name => listeners.delete(name),
  } });
  const tree = page.default();
  const nodes = [];
  function walk(node) {
    if (Array.isArray(node)) return node.forEach(walk);
    if (!node || typeof node !== 'object') return;
    nodes.push(node);
    walk(node.props?.children);
  }
  walk(tree);
  const cleanup = effects.map(effect => effect());
  assert.equal(reads, 1);
  assert.equal(changes.length, 0, 'Mount must not write a complete old array');
  listeners.get('storage')({ key: alarms.WATCHLIST_ALARMS_STORAGE_KEY });
  listeners.get('storage')({ key: null });
  assert.equal(reads, 3);
  assert.equal(changes.length, 0, 'Storage events must not echo a stale array');
  nodes.find(node => node.type === 'button' && node.props.children === 'Acik').props.onClick();
  assert.equal(changes[0].type, 'set-enabled');
  assert.equal(changes[0].id, 'rule-1');
  assert.equal(changes[0].enabled, false);
  assert.strictEqual(states[1], result.rules, 'Display the fresh merged storage result');
  nodes.find(node => node.type === 'button' && node.props.title === 'Kurali sil').props.onClick();
  assert.equal(changes[1].type, 'remove');
  assert.equal(changes[1].id, 'rule-1');
  const previous = states[1];
  result = { ok: false };
  nodes.find(node => node.type === 'button' && node.props.title === 'Kurali sil').props.onClick();
  assert.strictEqual(states[1], previous, 'Failed persistence must not pretend the rule was deleted');
  assert.match(states[3], /kaydedilemedi/);
  cleanup.forEach(callback => callback?.());
  assert.equal(listeners.size, 0);
});
