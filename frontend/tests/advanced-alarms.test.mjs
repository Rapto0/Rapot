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
const listHelpers = load('../src/lib/server-watchlists.ts');

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
  assert.equal(form.emptyAdvancedDraft('watchlist').scope, 'watchlist');
  const draft = { ...form.emptyAdvancedDraft('watchlist'), scope: 'all_bist', name: 'Evren', bist: 'IGNORED' };
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

function harness({ allowed = true, ruleRows = [], listRows = [], localLists = [], searchParams = '', symbolLoader = async () => ({ symbols: [] }) } = {}) {
  const states = [], requests = [], queries = [];
  const effectDeps = [];
  let cursor = 0, effectCursor = 0, effects = [], dirty = false, tree;
  const runtime = { running: true, last_cycle_at: new Date().toISOString(), last_error: null, evaluation: { total: 3000, checked: 2500, ready: 2100, backlog: 500 }, market: { tracked_symbols: 600, fresh_symbols: 580, state: 'connected' }, delivery: { pending: 4, sent: 10, failed: 0 }, telegram_configured: true };
  const queryData = {
    'advanced-alarms': { rules: ruleRows, usage: { price: 1000, technical: 1000, watchlist: 1000 }, runtime },
    'advanced-alarm-status': runtime, 'advanced-alarm-events': { events: [] }, 'advanced-alarm-watchlists': { watchlists: listRows },
  };
  const hooks = {
    useState(initial) { const index = cursor++; if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial; return [states[index], next => { const value = typeof next === 'function' ? next(states[index]) : next; dirty ||= !Object.is(value, states[index]); states[index] = value; }]; },
    useRef(value) { const index = cursor++; states[index] ??= { current: value }; return states[index]; },
    useMemo(fn) { return fn(); }, useEffect(callback, deps) { const index = effectCursor++; if (!effectDeps[index] || deps.some((value, i) => !Object.is(value, effectDeps[index][i]))) { effectDeps[index] = deps; effects.push(callback); } },
  };
  const api = Object.fromEntries(['fetchAdvancedAlarms', 'fetchAdvancedAlarmStatus', 'fetchAdvancedEvents', 'fetchServerWatchlists', 'removeAdvancedAlarm', 'removeServerWatchlist', 'saveAdvancedAlarm', 'saveServerWatchlist'].map(name => [name, async (...args) => { requests.push({ name, args }); const result = { ...args[0], id: 'saved', revision: 1, category: args[0]?.category ?? 'price' }; if (name === 'saveServerWatchlist') queryData['advanced-alarm-watchlists'] = { watchlists: [...listRows, result] }; return result; }]));
  const componentModule = load('../src/components/alarms/advanced-alarm-center.tsx', {
    react: { ...React, ...hooks }, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
    '@tanstack/react-query': { useQuery(options) { queries.push(options); return { data: queryData[options.queryKey[0]], isError: false, isLoading: false, refetch: async () => ({}) }; } },
    'lucide-react': Object.fromEntries(['Activity', 'Bell', 'List', 'Pencil', 'Plus', 'RefreshCw', 'Trash2'].map(x => [x, 'svg'])),
    '@/components/ui/action-dialog': { ActionDialog: 'dialog' }, '@/components/ui/button': { Button: 'button' }, '@/components/ui/input': { Input: 'input' }, '@/components/ui/page-shell': { PageShell: 'main' }, '@/components/ui/select': { Select: 'select' },
    '@/components/alarms/condition-builder': { ConditionBuilder: 'condition-builder' },
    '@/lib/hooks/use-session': { useSession: () => allowed ? { user: { username: 'admin', is_admin: true }, expiresAt: 1000 } : null },
    '@/lib/api/core': { ApiError: class ApiError extends Error {} },
    '@/lib/api/client': Object.fromEntries(['fetchBistSymbols', 'fetchCryptoSymbols'].map(name => [name, async () => { requests.push({ name, args: [] }); return symbolLoader(name); }])),
    '@/lib/api/advanced-alarms-api': api, '@/lib/advanced-alarm-form': form,
    '@/lib/server-watchlists': listHelpers,
    '@/lib/watchlist-alarms': { loadStoredWatchlists: () => localLists, loadStoredScannerWatchlists: () => [] },
  }, { window: { location: { search: searchParams } } });
  function render() { let rounds = 0; do { assert.ok(++rounds < 10, 'Effects must settle'); cursor = 0; effectCursor = 0; effects = []; dirty = false; tree = componentModule.AdvancedAlarmCenter(); effects.forEach(effect => effect()); } while (dirty); return tree; }
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


const mixedList = { id: 'server/list?one', name: 'Karma liste', revision: 3, symbols: [{ symbol: 'THYAO', market_type: 'BIST' }, { symbol: 'BTCUSDT', market_type: 'Kripto' }] };

test('server list links and drafts keep an encoded identity without copying members or posting an alarm', () => {
  assert.equal(listHelpers.serverWatchlistHref(mixedList.id), '/alarms?serverList=server%2Flist%3Fone&action=new');
  assert.equal(listHelpers.serverWatchlistHref(mixedList.id, 'detail'), '/alarms?serverList=server%2Flist%3Fone');
  assert.equal(listHelpers.serverWatchlistHref(mixedList.id, 'chart'), '/chart?serverList=server%2Flist%3Fone');
  for (const kind of ['price', 'technical']) {
    const draft = form.draftForWatchlist(mixedList, kind);
    const payload = form.writeFromAdvancedDraft({ ...draft, name: 'Koşul' });
    assert.equal(payload.category, 'watchlist');
    assert.equal(payload.scope, 'watchlist');
    assert.equal(payload.watchlist_id, mixedList.id);
    assert.deepEqual(plain(payload.symbols), []);
    assert.equal(payload.condition.left.field, kind === 'price' ? 'price' : 'rsi');
    assert.equal(payload.notify_telegram, false);
  }
});

test('a selected server-list link opens its draft exactly once and never mutates on navigation', () => {
  const view = harness({ listRows: [mixedList], searchParams: '?serverList=server%2Flist%3Fone&action=new' });
  assert.equal(view.requests.length, 0);
  assert.match(view.text(), /Yeni izleme listesi alarmı/);
  const listSelect = view.elements().find(e => e.type === 'select' && e.props.value === mixedList.id);
  assert.ok(listSelect);
  const nameLabel = view.elements().find(e => e.type === 'label' && text(e).startsWith('Alarm adı'));
  allElements(nameLabel).find(e => e.type === 'input').props.onChange({ target: { value: 'Benim taslağım' } });
  view.render(); view.render();
  assert.equal(view.elements().find(e => e.type === 'input' && e.props.value === 'Benim taslağım').props.value, 'Benim taslağım');
  assert.equal(view.requests.length, 0);
  const detail = harness({ listRows: [mixedList], searchParams: '?serverList=server%2Flist%3Fone' });
  assert.match(detail.text(), /Karma liste/);
  assert.ok(detail.elements().some(e => e.type === 'a' && e.props.href === listHelpers.serverWatchlistHref(mixedList.id, 'chart')));
  assert.equal(detail.elements().filter(e => e.type === 'form').length, 0);
});

test('missing server list never falls back to all BIST or creates an alarm', () => {
  const view = harness({ listRows: [mixedList], searchParams: '?serverList=missing&action=new' });
  assert.match(view.text(), /Seçilen sunucu listesi bulunamadı/);
  assert.equal(view.elements().filter(e => e.type === 'form').length, 0);
  assert.equal(view.requests.length, 0);
});

test('manual legacy import preserves mixed members and old data; saving opens only a new alarm draft', async () => {
  const old = { id: 'local-list', name: 'Eski liste', notes: 'Notlar korunur', alarmsEnabled: true, rows: [
    { kind: 'section', id: 'section-1', title: 'Bölüm' },
    { kind: 'symbol', rawSymbol: 'THYAO', marketType: 'BIST' },
    { kind: 'symbol', rawSymbol: 'BTCUSDT', marketType: 'Kripto' },
  ] };
  const before = JSON.stringify(old);
  const view = harness({ localLists: [old], searchParams: '?watchlist=local-list' });
  assert.equal(view.requests.length, 0);
  await view.elements().find(e => e.type === 'form').props.onSubmit({ preventDefault() {} }); view.render();
  assert.deepEqual(view.requests.map(x => x.name), ['saveServerWatchlist']);
  assert.deepEqual(plain(view.requests[0].args[0].symbols), mixedList.symbols);
  assert.equal(JSON.stringify(old), before);
  assert.match(view.text(), /Alarm taslağı hazır/);
  assert.match(view.text(), /Yeni izleme listesi alarmı/);
  assert.ok(view.elements().some(e => e.type === 'select' && e.props.value === 'saved'));
  const telegramLabel = view.elements().find(e => e.type === 'label' && text(e).startsWith('Telegram'));
  assert.equal(allElements(telegramLabel).find(e => e.type === 'input').props.checked, false);
});

test('list detail filters its alarms but supports adding further price and technical conditions', () => {
  const rules = ['first', 'second'].map((id, index) => ({ ...form.writeFromAdvancedDraft({ ...form.draftForWatchlist(mixedList), name: id }), id, revision: 1, state: 'pending', enabled: true, watchlist_id: index ? 'other' : mixedList.id }));
  const view = harness({ listRows: [mixedList], ruleRows: rules, searchParams: '?serverList=server%2Flist%3Fone' });
  assert.match(view.text(), /1 bağlı alarm/);
  assert.ok(view.elements().some(e => e.type === 'h3' && text(e) === 'first'));
  assert.ok(!view.elements().some(e => e.type === 'h3' && text(e) === 'second'));
  view.elements().find(e => e.type === 'button' && text(e) === 'Fiyat koşulu ekle').props.onClick(); view.render();
  assert.equal(view.elements().find(e => e.type === 'condition-builder').props.value.left.field, 'price');
  assert.equal(view.requests.length, 0);
  view.elements().find(e => e.type === 'button' && text(e) === 'Teknik koşul ekle').props.onClick(); view.render();
  assert.equal(view.elements().find(e => e.type === 'condition-builder').props.value.left.field, 'rsi');
  assert.equal(view.requests.length, 0);
});

test('pagination visits all mixed symbols without silent truncation or unbounded provider batches', () => {
  const symbols = [...Array.from({ length: 51 }, (_, i) => ({ symbol: `B${i}`, market_type: 'BIST' })), ...Array.from({ length: 69 }, (_, i) => ({ symbol: `C${i}USDT`, market_type: 'Kripto' }))];
  const pages = [0, 1, 2].map(page => listHelpers.serverWatchlistPage(symbols, page));
  assert.deepEqual(plain(pages.flatMap(page => page.rows)), symbols);
  assert.deepEqual(pages.map(page => page.rows.length), [50, 50, 20]);
  assert.ok(pages.every(page => page.bist.length <= 50 && page.crypto.length <= 50));
  assert.deepEqual(plain(pages[1].bist), ['B50.IS']);
  assert.equal(listHelpers.serverWatchlistPage(symbols, 999).page, 2);
  assert.equal(listHelpers.serverWatchlistPage([], -5).page, 0);
});

function serverPanelHarness({ allowed = true, listRows = [mixedList], quotes = [], failed = false } = {}) {
  const states = [], queries = [], requests = [], streams = [], selections = [];
  let cursor = 0, tree;
  const hooks = { useEffect() {}, useMemo(fn) { return fn(); }, useState(initial) { const index = cursor++; if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial; return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }]; } };
  const panel = load('../src/components/charts/server-watchlist-panel.tsx', {
    react: { ...React, ...hooks }, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
    '@tanstack/react-query': { useQuery(options) { queries.push(options); return { data: options.queryKey[0] === 'advanced-alarm-watchlists' ? { watchlists: listRows } : quotes, isError: options.queryKey[0] === 'server-watchlist-quotes' && failed, isLoading: false, dataUpdatedAt: Date.now(), refetch() {} }; } },
    '@/lib/api/advanced-alarms-api': { fetchServerWatchlists() { throw new Error('Unexpected automatic execution'); } },
    '@/lib/api/client': { fetchGlobalIndices: async (symbols, options) => { requests.push({ symbols, options }); return []; } },
    '@/lib/hooks/use-binance-ticker': { useBinanceTickerFeed(symbols, options) { streams.push({ symbols: plain(symbols), options }); return { prices: {}, receivedAtBySymbol: {}, status: 'connecting', reconnect() {} }; } },
    '@/lib/hooks/use-session': { useSession: () => allowed ? { user: { username: 'admin', is_admin: true }, expiresAt: 1000 } : null },
    '@/lib/server-watchlists': listHelpers, '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
  });
  function render() { cursor = 0; tree = panel.ServerWatchlistPanel({ symbol: 'THYAO', market: 'BIST', onSelect: (...args) => selections.push(args) }); }
  render();
  return { render, queries, requests, streams, selections, elements: () => allElements(tree), text: () => text(tree) };
}

test('chart server panel queries only the visible page and links the selected server identity', async () => {
  const members = Array.from({ length: 61 }, (_, i) => ({ symbol: `B${i}`, market_type: 'BIST' }));
  const list = { ...mixedList, symbols: members };
  const view = serverPanelHarness({ listRows: [list] });
  let query = view.queries.at(-1);
  const signal = new AbortController().signal;
  await query.queryFn({ signal });
  assert.equal(view.requests[0].symbols.length, 50);
  assert.equal(view.requests[0].options.signal, signal);
  view.elements().find(e => e.type === 'button' && text(e) === 'Sonraki').props.onClick(); view.render();
  query = view.queries.at(-1); await query.queryFn({ signal });
  assert.equal(view.requests[1].symbols.length, 11);
  assert.equal(view.requests[1].symbols[0], 'B50.IS');
  assert.ok(view.elements().some(e => e.type === 'a' && e.props.href === listHelpers.serverWatchlistHref(list.id)));
  view.elements().find(e => e.type === 'button' && e.props.title?.startsWith('B50 ·')).props.onClick();
  assert.deepEqual(view.selections, [['B50', 'BIST']]);
});

test('chart server panel hides private lists when logged out and preserves unknown values on refresh failure', () => {
  const anonymous = serverPanelHarness({ allowed: false });
  assert.ok(anonymous.queries.every(query => query.enabled === false));
  assert.ok(anonymous.streams.every(stream => stream.options.paused));
  assert.doesNotMatch(anonymous.text(), /Karma liste|THYAO|BTCUSDT/);
  const view = serverPanelHarness({ failed: true, quotes: [{ symbol: 'THYAO.IS', regularMarketPrice: 10, regularMarketChangePercent: null, message: 'Son veri' }] });
  assert.match(view.text(), /Son kayıt · güncel olmayabilir/);
  assert.match(view.text(), /BTCUSDT/);
  assert.doesNotMatch(view.text(), /BTC\/USD|0%/);
});


test('universe snapshots merge and deduplicate both markets without overwriting existing entries or permitting overflow', () => {
  assert.deepEqual(plain(form.mergeWatchlistSnapshot('thyao.IS', 'BTCUSDT', 'BIST', ['THYAO', 'GARAN'])), { bist: 'THYAO, GARAN', crypto: 'BTCUSDT', count: 3 });
  assert.deepEqual(plain(form.mergeWatchlistSnapshot('THYAO', 'BTCUSDT', 'Kripto', ['BTCUSDT', 'ETHUSDT'])), { bist: 'THYAO', crypto: 'BTCUSDT, ETHUSDT', count: 3 });
  for (const snapshot of [[], [''], [null], ['invalid/asset'], Array.from({ length: 2001 }, (_, i) => `B${i}`)]) assert.throws(() => form.mergeWatchlistSnapshot('THYAO', 'BTCUSDT', 'BIST', snapshot));
  assert.throws(() => form.mergeWatchlistSnapshot('THYAO', 'BTCUSDT', 'BIST', Array.from({ length: 1999 }, (_, i) => `B${i}`)), /2.000/);
});

test('adding a fetched universe is explicit and draft-only; empty or failed responses preserve user text', async () => {
  const local = { id: 'old', name: 'Liste', rows: [{ kind: 'symbol', rawSymbol: 'THYAO', marketType: 'BIST' }, { kind: 'symbol', rawSymbol: 'BTCUSDT', marketType: 'Kripto' }] };
  const view = harness({ localLists: [local], searchParams: '?watchlist=old', symbolLoader: async name => ({ symbols: name === 'fetchBistSymbols' ? ['THYAO', 'GARAN'] : ['BTCUSDT', 'ETHUSDT'] }) });
  assert.equal(view.requests.length, 0);
  await view.elements().find(e => e.type === 'button' && text(e) === 'Tüm BIST kodlarını ekle').props.onClick(); view.render();
  assert.equal(view.elements().find(e => e.type === 'textarea').props.value, 'THYAO, GARAN');
  await view.elements().find(e => e.type === 'button' && text(e) === 'Binance USDT çiftlerini ekle').props.onClick(); view.render();
  assert.ok(view.elements().some(e => e.type === 'input' && e.props.value === 'BTCUSDT, ETHUSDT'));
  assert.deepEqual(view.requests.map(x => x.name), ['fetchBistSymbols', 'fetchCryptoSymbols']);
  assert.match(view.text(), /anlık bir liste kopyası/);
  for (const loader of [async () => ({ symbols: [] }), async () => { throw new Error('private provider message'); }]) {
    const failed = harness({ localLists: [local], searchParams: '?watchlist=old', symbolLoader: loader });
    await failed.elements().find(e => e.type === 'button' && text(e) === 'Tüm BIST kodlarını ekle').props.onClick(); failed.render();
    assert.equal(failed.elements().find(e => e.type === 'textarea').props.value, 'THYAO');
    assert.match(failed.text(), /Mevcut girişler korundu/);
    assert.doesNotMatch(failed.text(), /private provider message/);
    assert.equal(failed.requests.length, 1);
  }
});
