import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

function load(path, imports = {}, globals = {}) {
  const context = vm.createContext({ exports: {}, structuredClone, URLSearchParams, Error, ...globals,
    require(name) { assert.ok(Object.hasOwn(imports, name), `Unexpected import ${name}`); return imports[name]; } });
  vm.runInContext(ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText, context);
  return context.exports;
}
const plain = value => JSON.parse(JSON.stringify(value));
const form = load('../src/lib/advanced-alarm-form.ts');

test('advanced transport retains auth core, cancellation, revisions and escaped identifiers', async () => {
  const calls = [];
  const api = load('../src/lib/api/advanced-alarms-api.ts', { './core': {
    API_BASE_URL: '/api', fetchApi: async (...args) => { calls.push(args); return {}; },
  } });
  const signal = new AbortController().signal;
  await api.fetchAdvancedAlarms(signal);
  await api.fetchAdvancedAlarmStatus(signal);
  await api.fetchAdvancedEvents(undefined, signal);
  await api.fetchAdvancedEvents(101, signal);
  await api.saveAdvancedAlarm({ revision: 3 }, 'a/b');
  await api.removeAdvancedAlarm('a/b');
  await api.saveServerWatchlist({ name: 'test', symbols: [] }, 'x?y');
  assert.deepEqual(calls.map(x => x[0]), ['/api/advanced-alarms', '/api/advanced-alarms/status', '/api/advanced-alarms/events?limit=100', '/api/advanced-alarms/events?limit=100&after_id=101', '/api/advanced-alarms/a%2Fb', '/api/advanced-alarms/a%2Fb', '/api/advanced-alarms/watchlists/x%3Fy']);
  assert.equal(calls[0][1].signal, signal);
  assert.equal(calls[2][1].signal, signal);
  assert.equal(calls[4][1].method, 'PUT');
  assert.equal(JSON.parse(calls[4][1].body).revision, 3);
});

test('minute alarms preserve compound multi-timeframe conditions and default Telegram off', () => {
  const draft = { ...form.emptyAdvancedDraft('technical'), name: ' Çoklu koşul ', bist: 'thyao.IS THYAO,ASELS', timeframe: '1m',
    condition: { op: 'and', children: [form.defaultLeaf(), { op: 'gt', left: { field: 'ema', period: 20, timeframe: '1d' }, right: { field: 'ema', period: 50, timeframe: '1d' } }] } };
  const payload = form.writeFromAdvancedDraft(draft);
  assert.equal(payload.name, 'Çoklu koşul');
  assert.equal(payload.timeframe, '1m');
  assert.equal(payload.notify_telegram, false);
  assert.deepEqual(plain(payload.symbols), [{ symbol: 'THYAO', market_type: 'BIST' }, { symbol: 'ASELS', market_type: 'BIST' }]);
  assert.equal(payload.condition.children[1].left.timeframe, '1d');
  draft.condition.children[1].left.period = 100;
  assert.equal(payload.condition.children[1].left.period, 20);
  assert.equal(Object.hasOwn(payload, 'expires_at'), false);
});

test('invalid thresholds, recursive groups and empty watchlists cannot be submitted', () => {
  const draft = { ...form.emptyAdvancedDraft(), name: 'x', bist: 'THYAO' };
  assert.throws(() => form.writeFromAdvancedDraft({ ...draft, condition: { ...draft.condition, right: NaN } }), /sayı/);
  assert.throws(() => form.writeFromAdvancedDraft({ ...draft, cooldown_seconds: 0 }), /bekleme/);
  assert.throws(() => form.writeFromAdvancedDraft({ ...draft, scope: 'watchlist' }), /liste/);
  const cyclic = { op: 'and', children: [] }; cyclic.children.push(cyclic);
  assert.throws(() => form.validateTree(cyclic), /4 seviye/);
  assert.throws(() => form.validateTree({ op: 'or', children: Array.from({ length: 33 }, () => form.defaultLeaf()) }), /32/);
  assert.throws(() => form.parseAlarmSymbols('', 'ETHBTC'), /USDT/);
});

test('all BIST and saved watchlists use server scopes without hidden frozen membership', () => {
  const draft = { ...form.emptyAdvancedDraft('watchlist'), name: 'Evren', bist: 'IGNORED' };
  const all = form.writeFromAdvancedDraft(draft);
  assert.equal(all.scope, 'all_bist');
  assert.deepEqual(plain(all.symbols), []);
  const list = form.writeFromAdvancedDraft({ ...draft, scope: 'watchlist', watchlist_id: 'server-list' }, 4);
  assert.equal(list.watchlist_id, 'server-list');
  assert.equal(list.revision, 4);
});

test('large watchlist parsing never silently truncates or changes symbol identity', () => {
  const symbols = Array.from({ length: 2000 }, (_, i) => `SYM${i}`);
  assert.equal(form.parseAlarmSymbols(symbols.join(','), '').length, 2000);
  assert.throws(() => form.parseAlarmSymbols([...symbols, 'OVER'].join(','), ''), /2.000/);
});

const allElements = node => React.isValidElement(node) ? [node, ...React.Children.toArray(node.props.children).flatMap(allElements)] : [];
const text = node => Array.isArray(node) ? node.map(text).join('') : React.isValidElement(node) ? text(node.props.children) : typeof node === 'string' || typeof node === 'number' ? String(node) : '';

function harness({ allowed = true, ruleRows = [] } = {}) {
  const states = [], requests = [], queries = [];
  let cursor = 0, tree;
  const runtime = { running: true, last_cycle_at: new Date().toISOString(), last_error: null, evaluation: { total: 3000, checked: 2500, ready: 2100, backlog: 500 }, market: { tracked_symbols: 600, fresh_symbols: 580, state: 'connected' }, delivery: { pending: 4, sent: 10, failed: 0 }, telegram_configured: true };
  const queryData = {
    'advanced-alarms': { rules: ruleRows, usage: { price: 1000, technical: 1000, watchlist: 1000 }, runtime },
    'advanced-alarm-status': runtime, 'advanced-alarm-events': { events: [] }, 'advanced-alarm-watchlists': { watchlists: [] },
  };
  const hooks = {
    useState(initial) { const index = cursor++; if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial; return [states[index], next => { states[index] = typeof next === 'function' ? next(states[index]) : next; }]; },
    useRef(value) { const index = cursor++; states[index] ??= { current: value }; return states[index]; },
    useMemo(fn) { return fn(); }, useEffect() {},
  };
  const api = Object.fromEntries(['fetchAdvancedAlarms', 'fetchAdvancedAlarmStatus', 'fetchAdvancedEvents', 'fetchServerWatchlists', 'removeAdvancedAlarm', 'removeServerWatchlist', 'saveAdvancedAlarm', 'saveServerWatchlist'].map(name => [name, async (...args) => { requests.push({ name, args }); return { ...args[0], id: 'saved', category: args[0]?.category ?? 'price' }; }]));
  const componentModule = load('../src/components/alarms/advanced-alarm-center.tsx', {
    react: { ...React, ...hooks }, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
    '@tanstack/react-query': { useQuery(options) { queries.push(options); return { data: queryData[options.queryKey[0]], isError: false, isLoading: false, refetch: async () => ({}) }; } },
    'lucide-react': Object.fromEntries(['Activity', 'Bell', 'List', 'Pencil', 'Plus', 'RefreshCw', 'Trash2'].map(x => [x, 'svg'])),
    '@/components/ui/action-dialog': { ActionDialog: 'dialog' }, '@/components/ui/button': { Button: 'button' }, '@/components/ui/input': { Input: 'input' }, '@/components/ui/page-shell': { PageShell: 'main' }, '@/components/ui/select': { Select: 'select' },
    '@/components/alarms/condition-builder': { ConditionBuilder: 'condition-builder' },
    '@/lib/hooks/use-session': { useSession: () => allowed ? { user: { username: 'admin', is_admin: true }, expiresAt: 1000 } : null },
    '@/lib/api/core': { ApiError: class ApiError extends Error {} },
    '@/lib/api/advanced-alarms-api': api, '@/lib/advanced-alarm-form': form,
    '@/lib/watchlist-alarms': { loadStoredWatchlists: () => [] },
  });
  function render() { cursor = 0; tree = componentModule.AdvancedAlarmCenter(); return tree; }
  render();
  return { render, requests, queries, elements: () => allElements(tree), text: () => text(tree) };
}

test('logged-out alarm center does not request private feeds or create rules', () => {
  const view = harness({ allowed: false });
  assert.ok(view.queries.every(q => q.enabled === false));
  assert.equal(view.requests.length, 0);
  assert.match(view.text(), /giriş yap/);
});

test('UI reports measured backlog and quote coverage instead of claiming all data is ready', () => {
  const view = harness();
  assert.match(view.text(), /2.100 hazır \/ 2.500 kontrol/);
  assert.match(view.text(), /Toplam 3.000 eşleşme/);
  assert.match(view.text(), /Bekleyen kontrol: 500/);
  assert.match(view.text(), /580 güncel \/ 600/);
  const streamQueries = view.queries.filter(q => ['advanced-alarm-status', 'advanced-alarm-events'].includes(q.queryKey[0]));
  assert.ok(streamQueries.every(q => q.refetchInterval === 1000));
  assert.equal(view.requests.length, 0);
});

test('saving is explicit and never silently enables Telegram', async () => {
  const view = harness();
  view.elements().find(e => e.type === 'button' && text(e).includes('Yeni alarm')).props.onClick(); view.render();
  const labelInput = label => allElements(view.elements().find(e => e.type === 'label' && text(e).startsWith(label))).find(e => e.type === 'input');
  labelInput('Alarm adı').props.onChange({ target: { value: 'Fiyat geçişi' } }); view.render();
  labelInput('BIST hisseleri').props.onChange({ target: { value: 'THYAO' } }); view.render();
  assert.equal(view.requests.length, 0);
  await view.elements().find(e => e.type === 'form').props.onSubmit({ preventDefault() {} }); view.render();
  assert.equal(view.requests[0].name, 'saveAdvancedAlarm');
  assert.equal(view.requests[0].args[0].notify_telegram, false);
  assert.equal(view.requests[0].args[0].symbols[0].symbol, 'THYAO');
  assert.match(view.text(), /sunucuya kaydedildi/);
});
