import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

function compile(source, imports = {}, globals = {}) {
  const code = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({ exports: {}, ...globals, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(code, context);
  return context.exports;
}
const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8');
const alarms = compile(source('../src/lib/watchlist-alarms.ts'), { '@/lib/indicators': {} });
const storageSource = source('../src/lib/alarm-rule-storage.ts');
const api = compile(storageSource, { '@/lib/watchlist-alarms': alarms });
const key = alarms.WATCHLIST_ALARMS_STORAGE_KEY;
const plain = (value) => JSON.parse(JSON.stringify(value));
const rule = (id, extra = {}) => ({
  id, watchlistId: 'list-1', watchlistName: 'İzleme', indicator: 'rsi', timeframe: '1d',
  enabled: true, thresholds: { ...alarms.DEFAULT_ALARM_THRESHOLDS },
  createdAt: '2026-09-10T00:00:00.000Z', updatedAt: '2026-09-10T00:00:00.000Z', ...extra,
});
function memory(rules = []) {
  const values = new Map([[key, JSON.stringify(rules)], ['unrelated', 'keep']]);
  const writes = [];
  return { values, writes,
    getItem(name) { return values.get(name) ?? null; },
    setItem(name, value) { writes.push([name, value]); values.set(name, value); },
    rules() { return JSON.parse(values.get(key) ?? '[]'); },
  };
}
function surface(storage) {
  const listeners = new Set();
  return { localStorage: storage, listeners,
    addEventListener(name, callback) { assert.equal(name, 'storage'); listeners.add(callback); },
    removeEventListener(name, callback) { assert.equal(name, 'storage'); listeners.delete(callback); },
    emit(event) { for (const listener of listeners) listener(event); },
  };
}

test('a stale tab adding B cannot resurrect A deleted or disabled by another tab', () => {
  for (const latest of [[], [rule('A', { enabled: false })]]) {
    const storage = memory([rule('A')]);
    const cached = api.readAlarmRuleStorage(storage);
    assert.equal(cached.rules[0].enabled, true);
    storage.values.set(key, JSON.stringify(latest));
    const result = api.updateAlarmRuleStorage({ type: 'add', rule: rule('B') }, storage);
    assert.equal(result.ok, true);
    assert.deepEqual(storage.rules(), [rule('B'), ...latest]);
    assert.deepEqual(plain(result.rules), storage.rules());
    assert.equal(storage.values.get('unrelated'), 'keep');
  }
});

test('explicit enable intent is idempotent; deleted targets and duplicate adds are not recreated/replaced', () => {
  const storage = memory([rule('A', { enabled: false }), rule('B')]);
  api.updateAlarmRuleStorage({ type: 'set-enabled', id: 'A', enabled: false, updatedAt: 'later' }, storage);
  api.updateAlarmRuleStorage({ type: 'set-enabled', id: 'deleted', enabled: true, updatedAt: 'later' }, storage);
  api.updateAlarmRuleStorage({ type: 'add', rule: rule('A') }, storage);
  api.updateAlarmRuleStorage({ type: 'remove', id: 'deleted' }, storage);
  assert.equal(storage.writes.length, 0);
  assert.equal(storage.rules()[0].enabled, false);
  api.updateAlarmRuleStorage({ type: 'set-enabled', id: 'A', enabled: true, updatedAt: 'later' }, storage);
  assert.equal(storage.rules()[0].updatedAt, 'later');
  api.updateAlarmRuleStorage({ type: 'remove', id: 'A' }, storage);
  assert.deepEqual(storage.rules(), [rule('B')]);
});

test('rename/delete watchlist modify only its latest rules and preserve other tab additions', () => {
  const other = rule('other', { watchlistId: 'list-2', enabled: false });
  const storage = memory([rule('new-in-same-list', { enabled: false }), other]);
  api.updateAlarmRuleStorage({ type: 'rename-watchlist', watchlistId: 'list-1', name: 'Yeni', updatedAt: 'later' }, storage);
  assert.deepEqual(storage.rules(), [rule('new-in-same-list', { enabled: false, watchlistName: 'Yeni', updatedAt: 'later' }), other]);
  api.updateAlarmRuleStorage({ type: 'remove-watchlist', watchlistId: 'list-1' }, storage);
  assert.deepEqual(storage.rules(), [other]);
});

test('malformed, non-array, invalid or duplicate saved rows block writes without discarding data', () => {
  for (const raw of ['', '{bad', 'null', '{}', '7', '[null]', JSON.stringify([rule('A'), {}]), JSON.stringify([rule('A'), rule('A')])]) {
    const storage = memory();
    storage.values.set(key, raw);
    assert.equal(api.readAlarmRuleStorage(storage).ok, false);
    assert.equal(api.updateAlarmRuleStorage({ type: 'add', rule: rule('B') }, storage).ok, false);
    assert.equal(storage.values.get(key), raw);
    assert.equal(storage.writes.length, 0);
    assert.equal(storage.values.size, 2);
  }
  const absent = memory(); absent.values.delete(key);
  assert.deepEqual(plain(api.readAlarmRuleStorage(absent)), { ok: true, rules: [] });
  assert.equal(absent.writes.length, 0);
});

test('storage read/write/access errors return failure, preserve saved rows and never expose error details', () => {
  const storage = memory([rule('A')]);
  const original = storage.values.get(key);
  const brokenRead = { ...storage, getItem() { throw new Error('private detail'); } };
  const brokenWrite = { ...storage, setItem() { throw new Error('quota private detail'); } };
  for (const target of [brokenRead, brokenWrite]) {
    assert.deepEqual(plain(api.updateAlarmRuleStorage({ type: 'remove', id: 'A' }, target)), { ok: false });
    assert.equal(storage.values.get(key), original);
  }
  const unavailable = compile(storageSource, { '@/lib/watchlist-alarms': alarms }, {
    window: { get localStorage() { throw new Error('denied'); } },
  });
  assert.equal(unavailable.readAlarmRuleStorage().ok, false);
  assert.equal(unavailable.updateAlarmRuleStorage({ type: 'remove', id: 'A' }).ok, false);
});

test('hydration, delayed cross-tab events and clear only read; listener cleanup prevents later updates', () => {
  const storage = memory([rule('A')]);
  const target = surface(storage);
  const updates = [];
  const dispose = api.subscribeAlarmRuleStorage((result) => updates.push(plain(result)), target);
  assert.equal(updates.length, 1);
  storage.values.set(key, '[]');
  target.emit({ key, storageArea: storage, newValue: JSON.stringify([rule('A')]) });
  assert.deepEqual(updates.at(-1), { ok: true, rules: [] });
  target.emit({ key: 'unrelated', storageArea: storage });
  target.emit({ key, storageArea: memory() });
  assert.equal(updates.length, 2);
  storage.values.delete(key);
  target.emit({ key: null, storageArea: storage });
  assert.equal(updates.length, 3);
  assert.equal(storage.writes.length, 0);
  dispose();
  target.emit({ key, storageArea: storage });
  assert.equal(updates.length, 3);
  assert.equal(target.listeners.size, 0);
});

// Execute the actual chart callback declarations, selected by TypeScript's AST.
// Only unrelated chart rendering/market dependencies are excluded from this harness.
const chart = ts.createSourceFile('advanced-chart.tsx', source('../src/components/charts/advanced-chart.tsx'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
function chartCallbacks(names, globals) {
  const found = new Map();
  function visit(node) {
    if (ts.isVariableStatement(node)) {
      for (const declaration of node.declarationList.declarations) {
        if (ts.isIdentifier(declaration.name) && names.includes(declaration.name.text)) found.set(declaration.name.text, node.getText(chart));
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(chart);
  for (const name of names) assert.ok(found.has(name), `Missing actual chart callback: ${name}`);
  return compile(names.map((name) => found.get(name)).join('\n') + `\nexport { ${names.join(', ')} };`, {}, {
    useCallback: (callback) => callback, ...globals,
  });
}
function chartHarness(storage, extra = {}) {
  const notices = [];
  let displayed = [rule('A')];
  const liveApi = compile(storageSource, { '@/lib/watchlist-alarms': alarms }, { window: { localStorage: storage } });
  const globals = {
    ...liveApi, ...alarms, watchlistAlarmRules: displayed,
    activeWatchlist: { id: 'list-1', name: 'İzleme' },
    alarmIndicatorDraft: 'rsi', alarmTimeframeDraft: '1d', alarmThresholdDraft: alarms.DEFAULT_ALARM_THRESHOLDS,
    setWatchlistAlarmRules(value) { assert.equal(typeof value, 'object'); displayed = value; },
    showWatchlistToast(message) { notices.push(message); },
    ...extra,
  };
  const names = ['commitAlarmRuleChange', 'handleCreateWatchlistAlarmRule', 'handleToggleAlarmRule', 'handleRemoveAlarmRule'];
  return { callbacks: chartCallbacks(names, globals), notices, displayed: () => plain(displayed) };
}

test('actual chart create/toggle/delete handlers respect other tab changes; failures keep UI and avoid success', () => {
  const storage = memory([rule('A')]);
  const chart = chartHarness(storage);
  storage.values.set(key, JSON.stringify([rule('A', { enabled: false })]));
  chart.callbacks.handleToggleAlarmRule('A');
  assert.equal(storage.rules()[0].enabled, false);
  storage.values.set(key, '[]');
  chart.callbacks.handleCreateWatchlistAlarmRule();
  assert.equal(storage.rules().length, 1);
  assert.notEqual(storage.rules()[0].id, 'A');
  chart.callbacks.handleRemoveAlarmRule(storage.rules()[0].id);
  assert.deepEqual(storage.rules(), []);

  const broken = memory([rule('A')]);
  broken.setItem = () => { throw new Error('quota'); };
  const failed = chartHarness(broken);
  failed.callbacks.handleRemoveAlarmRule('A');
  failed.callbacks.handleCreateWatchlistAlarmRule();
  assert.deepEqual(failed.displayed(), [rule('A')]);
  assert.equal(failed.notices.length, 2);
  assert.ok(failed.notices.every((notice) => notice.includes('İşlem uygulanmadı')));
});

test('actual chart alarm effect subscribes read-only and releases the listener', () => {
  let effect;
  function hasSubscribe(node) {
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'subscribeAlarmRuleStorage') return true;
    return ts.forEachChild(node, hasSubscribe);
  }
  function visit(node) {
    if (ts.isExpressionStatement(node) && ts.isCallExpression(node.expression) && ts.isIdentifier(node.expression.expression)
      && node.expression.expression.text === 'useEffect' && hasSubscribe(node)) effect = node.getText(chart);
    ts.forEachChild(node, visit);
  }
  visit(chart);
  assert.ok(effect, 'Chart must wire the real alarm subscription');
  const storage = memory([rule('A')]), target = surface(storage);
  const liveApi = compile(storageSource, { '@/lib/watchlist-alarms': alarms }, { window: target });
  let cleanup, displayed;
  compile(effect, {}, { ...liveApi, useEffect(callback) { cleanup = callback(); },
    setWatchlistAlarmRules(value) { displayed = plain(value); }, setWatchlistNotice() {},
  });
  assert.equal(displayed[0].id, 'A');
  storage.values.set(key, '[]'); target.emit({ key, storageArea: storage });
  assert.deepEqual(displayed, []);
  assert.equal(storage.writes.length, 0);
  cleanup(); assert.equal(target.listeners.size, 0);
});
