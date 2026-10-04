import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

const source = path => readFileSync(new URL(path, import.meta.url), 'utf8');
function load(path, imports = {}, globals = {}) {
  const context = vm.createContext({ exports: {}, URLSearchParams, Error, ...globals, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(ts.transpileModule(source(path), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText, context);
  return context.exports;
}
const form = load('../src/lib/server-alarm-form.ts');
const plain = value => JSON.parse(JSON.stringify(value));
const now = Date.parse('2026-10-02T12:00:00Z');
const rule = (overrides = {}) => ({
  id: 'one', name: 'BTC dip', symbols: [{ symbol: 'BTCUSDT', market_type: 'Kripto' }],
  indicator: 'rsi', timeframe: '1h', side: 'dip', threshold: 30, mode: 'on_enter',
  enabled: true, notify_telegram: false, state: 'active', created_at: new Date(now).toISOString(),
  updated_at: new Date(now).toISOString(), last_checked_at: new Date(now).toISOString(),
  last_triggered_at: null, last_error: null, ...overrides,
});

test('server alarm API uses authenticated core transport and escaped rule identifiers', async () => {
  const calls = [];
  const api = load('../src/lib/api/alarms-api.ts', { './core': {
    API_BASE_URL: '/api', fetchApi: async (...args) => { calls.push(args); return {}; },
  } });
  const signal = new AbortController().signal;
  await api.fetchServerAlarms(signal);
  await api.fetchServerAlarmEvents(signal);
  const payload = form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'test', cryptoSymbols: 'BTCUSDT' });
  await api.createServerAlarm(payload);
  await api.updateServerAlarm('a/b?', payload);
  await api.deleteServerAlarm('a/b?');
  assert.deepEqual(calls.map(call => call[0]), ['/api/alarms', '/api/alarms/events?limit=100', '/api/alarms', '/api/alarms/a%2Fb%3F', '/api/alarms/a%2Fb%3F']);
  assert.equal(calls[0][1].signal, signal);
  assert.equal(calls[1][1].signal, signal);
  assert.equal(calls[2][1].method, 'POST');
  assert.equal(calls[3][1].method, 'PUT');
  assert.equal(calls[4][1].method, 'DELETE');
  assert.deepEqual(JSON.parse(calls[2][1].body), plain(payload));
});

test('draft validates and deduplicates mixed markets while preserving server scope', () => {
  const payload = form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: ' İzleme ', bistSymbols: 'thyao.IS, THYAO asels', cryptoSymbols: 'btcusdt; BTCUSDT' });
  assert.deepEqual(plain(payload.symbols), [{ symbol: 'THYAO', market_type: 'BIST' }, { symbol: 'ASELS', market_type: 'BIST' }, { symbol: 'BTCUSDT', market_type: 'Kripto' }]);
  assert.equal(payload.name, 'İzleme');
  assert.equal(payload.notify_telegram, false);
  for (const timeframe of ['1h', '4h']) {
    assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', bistSymbols: 'THYAO', timeframe }), /BIST alarmlarında yalnız 1 gün/);
    assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', bistSymbols: 'THYAO', cryptoSymbols: 'BTCUSDT', timeframe }), /BIST alarmlarında yalnız 1 gün/);
  }
  for (const timeframe of ['1h', '4h', '1d']) {
    assert.equal(form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', cryptoSymbols: 'BTCUSDT', timeframe }).timeframe, timeframe);
  }
  assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', cryptoSymbols: 'ETHBTC' }), /USDT/);
  assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', bistSymbols: 'THYAO, ASELS' }, 1), /en fazla 1/);
  assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', cryptoSymbols: 'BTC/USDT' }), /biçiminde/);
});

test('score bounds and empty numeric thresholds cannot produce misleading alarms', () => {
  for (const [indicator, threshold] of [['rsi', ''], ['rsi', '-1'], ['wr', '1'], ['combo', '4.1'], ['combo', '0'], ['hunter', '16'], ['hunter', 'NaN']]) {
    assert.throws(() => form.alarmWriteFromDraft({ ...form.emptyAlarmDraft(), name: 'x', cryptoSymbols: 'BTCUSDT', indicator, threshold }), /eşiği/);
  }
  assert.match(form.alarmCondition('rsi', 'dip', 30), /≤ 30/);
  assert.match(form.alarmCondition('wr', 'top', -20), /≥ -20/);
  assert.match(form.alarmCondition('hunter', 'dip', 7), /≥ 7 \/ 15/);
});

test('chart and watchlist prefill are drafts only, without enabling Telegram or truncating lists', () => {
  assert.equal(form.alarmPrefill('?symbol=BTCUSDT&market=Kripto').cryptoSymbols, 'BTCUSDT');
  assert.equal(form.alarmPrefill('?symbol=%3Cscript%3E&market=Kripto').cryptoSymbols, '');
  const rows = Array.from({ length: 21 }, (_, index) => ({ kind: 'symbol', rawSymbol: `SYM${index}`, marketType: 'BIST' }));
  const draft = form.alarmPrefill('?watchlist=list', [{ id: 'list', name: 'Liste', rows }]);
  assert.equal(draft.notify_telegram, false);
  assert.equal(draft.bistSymbols.split(', ').length, 21);
  assert.throws(() => form.alarmWriteFromDraft(draft), /en fazla 20/);
  rows[0].rawSymbol = 'CHANGED';
  assert.match(draft.bistSymbols, /^SYM0,/);
});

function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}
function text(element) {
  if (Array.isArray(element)) return element.map(text).join('');
  if (React.isValidElement(element)) return text(element.props.children);
  return typeof element === 'string' || typeof element === 'number' ? String(element) : '';
}
class ApiError extends Error { constructor(message, status) { super(message); this.status = status; } }

function harness({ session = { user: { username: 'admin', is_admin: true }, expiresAt: now + 60_000 }, search = '', ruleOverrides = {}, eventOverrides = {}, implementations = {} } = {}) {
  const slots = [], requests = [], configs = [];
  let cursor = 0, effects = [], dirty = false, tree;
  const queries = {
    rules: { data: { rules: [rule()], runtime: { running: true, last_cycle_at: new Date(now).toISOString(), telegram_configured: true, poll_interval_seconds: 60 }, limits: { max_rules: 50, max_symbols_per_rule: 20, max_subscriptions: 100 } }, isLoading: false, isError: false, isFetching: false, ...ruleOverrides },
    events: { data: { events: [] }, isLoading: false, isError: false, isFetching: false, ...eventOverrides },
  };
  for (const query of Object.values(queries)) query.refetch = async () => ({ data: query.data });
  const different = (a, b) => !a || b.some((value, index) => !Object.is(value, a[index]));
  const hooks = {
    useState(initial) {
      const index = cursor++;
      slots[index] ??= { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, next => {
        slots[index].value = typeof next === 'function' ? next(slots[index].value) : next;
        dirty = true;
      }];
    },
    useRef(value) { const index = cursor++; return slots[index] ??= { current: value }; },
    useEffect(effect, deps) {
      const index = cursor++;
      if (!slots[index] || different(slots[index].deps, deps)) {
        const previous = slots[index];
        slots[index] = { deps };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  const Dialog = () => null;
  const api = {};
  for (const name of ['fetchServerAlarms', 'fetchServerAlarmEvents', 'createServerAlarm', 'updateServerAlarm', 'deleteServerAlarm']) {
    api[name] = async (...args) => {
      requests.push([name, ...args]);
      if (implementations[name]) return implementations[name](...args);
      return name === 'createServerAlarm' ? rule({ ...args[0], id: 'new' }) : name === 'updateServerAlarm' ? rule({ ...args[1], id: args[0] }) : { deleted: true };
    };
  }
  class Clock extends Date { static now() { return now; } }
  const Page = load('../src/app/alarms/legacy/page.tsx', {
    react: hooks, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' },
    '@tanstack/react-query': {
      useQuery(config) { configs.push(config); return config.queryKey[0] === 'server-alarms' ? queries.rules : queries.events; },
      useQueryClient: () => ({ setQueryData(key, update) { const target = key[0] === 'server-alarms' ? queries.rules : queries.events; target.data = update(target.data); dirty = true; } }),
    },
    'lucide-react': Object.fromEntries(['Bell', 'Pencil', 'Plus', 'RefreshCw', 'Trash2'].map(name => [name, () => null])),
    '@/components/ui/action-dialog': { ActionDialog: Dialog }, '@/components/ui/button': { Button: 'button' },
    '@/components/ui/input': { Input: 'input' }, '@/components/ui/page-shell': { PageShell: 'main' }, '@/components/ui/select': { Select: 'select' },
    '@/lib/api/alarms-api': api, '@/lib/api/core': { ApiError }, '@/lib/hooks/use-session': { useSession: () => session },
    '@/lib/server-alarm-form': form, '@/lib/watchlist-alarms': { loadStoredWatchlists: () => [] },
  }, { window: { location: { search } }, Date: Clock }).default;
  function render() {
    for (let passes = 0; passes < 20; passes++) {
      cursor = 0; effects = []; dirty = false; tree = Page();
      for (const effect of effects) effect();
      if (!dirty) return tree;
    }
    throw new Error('Render did not settle');
  }
  render();
  return {
    requests, configs, queries, render, text: () => text(tree),
    nodes: () => descendants(tree),
    button(name) { const node = descendants(tree).find(item => item.type === 'button' && (item.props['aria-label'] === name || text(item) === name)); assert.ok(node, name); return node; },
    input(name) { const node = descendants(tree).find(item => item.props.name === name); assert.ok(node, name); return node; },
    form() { return descendants(tree).find(item => item.type === 'form'); },
    dialog() { return descendants(tree).find(item => item.type === Dialog); },
    setSession(next) { session = next; render(); },
  };
}

test('unauthenticated and non-admin sessions neither poll nor show cached private rules', () => {
  for (const session of [null, { user: { username: 'reader', is_admin: false } }]) {
    const h = harness({ session });
    assert.ok(h.configs.every(config => config.enabled === false));
    assert.doesNotMatch(h.text(), /BTC dip/);
    assert.match(h.text(), /yönetici/);
    assert.equal(h.form(), undefined);
  }
});

test('refresh failures preserve existing rules and history while reporting unknown runtime', () => {
  const h = harness({ ruleOverrides: { isError: true, error: new Error('offline') }, eventOverrides: { isError: true, error: new Error('offline'), data: { events: [{ id: 1, rule_name: 'old hit', symbol: 'BTCUSDT', market_type: 'Kripto', side: 'dip', value: 29, timeframe: '1h', created_at: new Date(now).toISOString(), bar_time: new Date(now).toISOString(), delivery_status: 'failed', delivery_error: 'Gönderim başarısız' }] } } });
  assert.match(h.text(), /BTC dip/);
  assert.match(h.text(), /old hit/);
  assert.match(h.text(), /Durum doğrulanamadı/);
  assert.match(h.text(), /Son alınan kurallar gösteriliyor/);
  assert.match(h.text(), /Telegram gönderilemedi/);
  assert.match(h.text(), /Gönderim başarısız/);
});

test('URL prefill does not mutate until explicit save and defaults notification off', async () => {
  const h = harness({ search: '?symbol=ETHUSDT&market=Kripto' });
  assert.equal(h.requests.length, 0);
  assert.equal(h.input('cryptoSymbols').props.value, 'ETHUSDT');
  assert.equal(h.input('notify_telegram').props.checked, false);
  await h.form().props.onSubmit({ preventDefault() {} }); h.render();
  assert.equal(h.requests[0][0], 'createServerAlarm');
  assert.equal(h.requests[0][1].notify_telegram, false);
  assert.equal(h.requests[0][1].symbols[0].symbol, 'ETHUSDT');
  assert.match(h.text(), /Alarm sunucuya kaydedildi/);
});

test('invalid rule stays editable without API side effects', async () => {
  const h = harness({ search: '?symbol=THYAO&market=BIST' });
  for (const timeframe of ['1h', '4h']) {
    h.input('timeframe').props.onChange({ target: { value: timeframe } }); h.render();
    await h.form().props.onSubmit({ preventDefault() {} }); h.render();
    assert.match(h.text(), /BIST alarmlarında yalnız 1 gün/);
  }
  assert.equal(h.requests.length, 0);
  assert.ok(h.form());
  assert.match(h.text(), /BIST: yalnız 1 gün/);
});

test('failed save preserves draft and pending guard prevents duplicate submit', async () => {
  let reject;
  const h = harness({ search: '?symbol=ETHUSDT&market=Kripto', implementations: { createServerAlarm: () => new Promise((resolve, failure) => { reject = failure; }) } });
  const submit = h.form().props.onSubmit;
  const first = submit({ preventDefault() {} });
  await submit({ preventDefault() {} });
  h.render();
  assert.equal(h.requests.length, 1);
  assert.equal(h.form().props['aria-busy'], true);
  reject(new ApiError('Service unavailable', 503)); await first; h.render();
  assert.equal(h.input('cryptoSymbols').props.value, 'ETHUSDT');
  assert.match(h.text(), /Sunucuya ulaşılamadı veya geçici bir hata/);
  assert.doesNotMatch(h.text(), /Alarm sunucuya kaydedildi/);
});

test('edit uses PUT and strips read-only state; pause updates cached rule only after success', async () => {
  const h = harness();
  h.button('BTC dip: düzenle').props.onClick(); h.render();
  h.input('threshold').props.onChange({ target: { value: '25' } }); h.render();
  await h.form().props.onSubmit({ preventDefault() {} }); h.render();
  assert.equal(h.requests[0][0], 'updateServerAlarm');
  assert.equal(h.requests[0][2].threshold, 25);
  assert.equal(Object.hasOwn(h.requests[0][2], 'state'), false);
  h.button('BTC dip: duraklat').props.onClick();
  for (let i = 0; i < 8; i++) await Promise.resolve();
  h.render();
  assert.equal(h.requests[1][2].enabled, false);
  assert.ok(h.button('BTC dip: etkinleştir'));
});

test('delete requires dialog confirmation and a failure stays visible inside dialog', async () => {
  const h = harness({ implementations: { deleteServerAlarm: async () => { throw new Error('delete failed'); } } });
  h.button('BTC dip: sil').props.onClick(); h.render();
  assert.equal(h.requests.length, 0);
  h.dialog().props.onConfirm();
  for (let i = 0; i < 8; i++) await Promise.resolve();
  h.render();
  assert.match(h.dialog().props.description, /delete failed/);
  assert.match(h.text(), /BTC dip/);
  assert.equal(h.queries.rules.data.rules.length, 1);
});

test('logging out hides private state without pausing alarms or sending mutations', () => {
  const h = harness();
  h.setSession(null);
  assert.doesNotMatch(h.text(), /BTC dip/);
  assert.equal(h.requests.length, 0);
  assert.match(h.text(), /alarmları durdurmaz/);
});

test('runtime failure or stale cycle cannot be presented as healthy and headings use theme foreground', () => {
  const h = harness({ search: '?symbol=BTCUSDT&market=Kripto' });
  h.queries.rules.data.runtime.last_cycle_error = 'Döngü tamamlanamadı'; h.render();
  assert.match(h.text(), /Son alarm döngüsü tamamlanamadı/);
  assert.ok(h.nodes().some(node => node.props.role === 'alert' && text(node) === 'Döngü tamamlanamadı'));
  h.queries.rules.data.runtime.last_cycle_error = null;
  h.queries.rules.data.runtime.last_cycle_at = new Date(now - 240_000).toISOString(); h.render();
  assert.match(h.text(), /Son kontrol gecikti/);
  assert.ok(h.nodes().filter(node => node.type === 'h2').every(node => node.props.className.includes('text-foreground')));
  assert.match(h.text(), /ertesi gün 00.00/);
  assert.match(h.text(), /30 gün ve 20.000 kayıt/);
});

test('chart creates server form links and legacy page is explicit without local migration', () => {
  const chart = source('../src/components/charts/advanced-chart.tsx');
  assert.match(chart, /\/alarms\?symbol=/);
  assert.match(chart, /\/alarms\?watchlist=/);
  assert.doesNotMatch(chart, /handleCreateWatchlistAlarmRule|createWatchlistAlarmRule/);
  assert.match(chart, /kaydetmeden alarm başlamaz/);
  assert.match(chart, /Eski yerel liste alarmları/);
});
