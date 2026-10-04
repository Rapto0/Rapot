import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

function load(path, imports = {}, globals = {}) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const context = vm.createContext({ exports: {}, URL, URLSearchParams, AbortController, Error,
    setTimeout, clearTimeout, setInterval, clearInterval, ...globals,
    require(name) { assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`); return imports[name]; },
  });
  vm.runInContext(ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText, context);
  return context.exports;
}
const utils = load('../src/components/research/research-utils.ts');
const plain = value => JSON.parse(JSON.stringify(value));
const descendants = element => !React.isValidElement(element) ? [] : [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
function text(element) {
  if (Array.isArray(element)) return element.map(text).join('');
  if (React.isValidElement(element)) return text(element.props.children);
  return typeof element === 'string' || typeof element === 'number' ? String(element) : '';
}
const icons = Object.fromEntries(['Play', 'Plus', 'Square', 'Radio', 'Trash2', 'CheckCircle2', 'KeyRound', 'RefreshCw', 'Save', 'ArrowUpRight', 'BookOpen', 'ChevronRight', 'Compass', 'Search'].map(name => [name, () => null]));
const ui = { '@/components/ui/button': { Button: 'button' }, '@/components/ui/input': { Input: 'input' }, '@/components/ui/select': { Select: 'select' } };

function harness(path, exportName, imports, globals = {}, initialProps = {}) {
  const slots = [];
  let cursor = 0, effects = [], dirty = false, tree;
  const hooks = {
    useState(initial) {
      const index = cursor++;
      if (!slots[index]) slots[index] = { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, next => { slots[index].value = typeof next === 'function' ? next(slots[index].value) : next; dirty = true; }];
    },
    useRef(value) { const index = cursor++; return slots[index] ??= { current: value }; },
    useEffect(effect, deps) {
      const index = cursor++;
      if (!slots[index] || !deps || deps.some((value, i) => !Object.is(value, slots[index].deps[i]))) {
        const previous = slots[index]; slots[index] = { deps };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  const Component = load(path, { react: hooks, 'react/jsx-runtime': jsxRuntime, 'lucide-react': icons, ...ui, ...imports }, globals)[exportName];
  function render() {
    for (let pass = 0; pass < 20; pass++) {
      cursor = 0; effects = []; dirty = false; tree = Component(initialProps);
      for (const effect of effects) effect();
      if (!dirty) return tree;
    }
    throw new Error('Render did not settle');
  }
  render();
  return {
    render, tree: () => tree, nodes: () => descendants(tree),
    find: predicate => { const result = descendants(tree).find(predicate); assert.ok(result, 'Element not found'); return result; },
    unmount: () => slots.forEach(slot => slot?.cleanup?.()),
  };
}

test('API transports remain authenticated-core calls and stream deletion targets the exact subscriber', async () => {
  const calls = [];
  const api = load('../src/lib/api/borsapy-api.ts', { './core': { API_BASE_URL: '/api', fetchApi: async (...args) => { calls.push(args); return {}; } } });
  const signal = new AbortController().signal;
  const subscription = { symbol: 'VIOP:F_XU030&other', interval: '1m', study: 'PUB;mine', studyInputs: { length: 7 }, subscriberId: 'panel-one' };
  await api.fetchResearchStream(subscription, signal);
  await api.stopResearchStream(subscription);
  const first = new URL(calls[0][0], 'https://local.test');
  assert.equal(first.pathname, '/api/borsapy/stream');
  assert.equal(first.searchParams.get('symbol'), subscription.symbol);
  assert.equal(first.searchParams.get('subscriber_id'), 'panel-one');
  assert.deepEqual(JSON.parse(first.searchParams.get('study_inputs')), { length: 7 });
  assert.equal(calls[0][1].signal, signal);
  assert.equal(calls[1][0], calls[0][0]);
  assert.equal(calls[1][1].method, 'DELETE');
  await api.saveResearchConnection({ session: 'private', session_sign: 'signature' }, signal);
  assert.equal(calls[2][0], '/api/borsapy/connection');
  assert.deepEqual(JSON.parse(calls[2][1].body), { session: 'private', session_sign: 'signature' });
  await api.deleteSavedResearch('id/with?characters', signal);
  assert.equal(calls[3][0], '/api/borsapy/saved/id%2Fwith%3Fcharacters');
  await api.runResearchQuery('portfolio', { positions: [{ symbol: 'USD', shares: 1, cost: 40, asset_type: 'fx' }] }, signal);
  assert.equal(calls[4][1].signal, signal);
  assert.equal(JSON.parse(calls[4][1].body).operation, 'portfolio');
});

test('catalog fields preserve zero and reject invalid numeric/select/required values', () => {
  const fields = [{ name: 'amount', label: 'Tutar', type: 'number', min: 0, max: 100, required: true }, { name: 'kind', label: 'Tür', type: 'select', options: [{ value: 'daily', label: 'Günlük' }] }];
  assert.deepEqual(plain(utils.researchParams(fields, { amount: '0', kind: 'daily' })), { amount: 0, kind: 'daily' });
  for (const amount of ['', 'NaN', 'Infinity', '-1', '101']) assert.throws(() => utils.researchParams(fields, { amount }), /Tutar/);
  assert.throws(() => utils.researchParams(fields, { amount: '1', kind: 'injected' }), /listeden/);
});

test('intraday selection shortens incompatible history and never expands a shorter choice', () => {
  const fields = [{ name: 'period', options: ['1d', '5d', '1mo', '3mo', '6mo', '1y'].map(value => ({ value, label: value })) }, { name: 'interval' }];
  assert.equal(utils.changeResearchParam(fields, { period: '1y', interval: '1d' }, 'interval', '1m').period, '5d');
  assert.equal(utils.changeResearchParam(fields, { period: '1d', interval: '1m' }, 'interval', '1h').period, '1d');
  assert.deepEqual(plain(utils.availableResearchPeriods(fields, '15m')).map(row => row.value), ['1d', '5d', '1mo', '3mo']);
  assert.equal(utils.researchOptionLabel({ name: 'interval' }, '1m', '1m'), '1 dakika');
  assert.equal(utils.researchOptionLabel({ name: 'period' }, '1mo', '1mo'), '1 ay');
});

test('CSV escapes spreadsheet formulas and quotes without corrupting numeric negatives', () => {
  const csv = utils.researchCsv({ columns: ['title', 'value'], rows: [{ title: '=HYPERLINK("bad")', value: -2 }, { title: ' +cmd', value: 0 }, { title: 'satır\nsonu', value: null }] });
  assert.ok(csv.startsWith('\uFEFF'));
  assert.ok(csv.includes('"\'=HYPERLINK(""bad"")"'));
  assert.ok(csv.includes('"\' +cmd","0"'));
  assert.ok(csv.includes('"-2"'));
  assert.ok(!csv.includes('"\'-2"'));
});

test('provider links cannot execute scripts or expose embedded credentials', () => {
  assert.equal(utils.researchLink('https://kap.org.tr/tr/Bildirim/123'), 'https://kap.org.tr/tr/Bildirim/123');
  for (const value of ['javascript:alert(1)', 'data:text/html,test', '//other.test', 'https://user:secret@host.test', {}, null]) assert.equal(utils.researchLink(value), null);
});

test('chart input rejects invalid time/OHLC/volume and orders deduplicated valid candles', () => {
  const candle = { time: 1700000000, open: 10, high: 12, low: 9, close: 11, volume: 0 };
  const data = [candle, { ...candle, close: 12 }, { ...candle, time: 1600000000 }, { ...candle, time: 1e20 }, { ...candle, time: 1700000001, low: 13 }, { ...candle, time: 1700000002, volume: Infinity }];
  const valid = utils.validResearchCandles(data);
  assert.equal(valid.length, 2);
  assert.equal(valid[0].time, 1600000000);
  assert.equal(valid[1].close, 12);
  assert.equal(valid[1].volume, 0);
});

test('series extraction retains missing indicator gaps and excludes financial row labels', () => {
  const result = utils.researchSeries({ columns: ['index', 'RSI'], rows: [{ index: '2026-01-01', RSI: 0 }, { index: '2026-01-02', RSI: null }, { index: '2026-01-03', RSI: 40 }] });
  assert.equal(result.points.length, 3);
  assert.equal(result.points[0].RSI, 0);
  assert.equal(result.points[1].RSI, undefined);
  assert.equal(utils.researchSeries({ columns: ['index', 'value'], rows: [{ index: 'Assets', value: 20 }, { index: 'Equity', value: 10 }] }), null);
});

test('Pine parameter rows are scalar, finite, named and unique', () => {
  assert.deepEqual(plain(utils.studyInputValues([{ name: 'length', type: 'number', value: '7' }, { name: 'overlay', type: 'boolean', value: 'false' }])), { length: 7, overlay: false });
  for (const name of ['__proto__', 'constructor', 'bad-name', '']) assert.throws(() => utils.studyInputValues([{ name, type: 'number', value: '7' }]));
  assert.throws(() => utils.studyInputValues([{ name: 'length', type: 'number', value: '' }]));
  assert.throws(() => utils.studyInputValues([{ name: 'length', type: 'number', value: '7' }, { name: 'length', type: 'number', value: '14' }]));
});

test('private research page mounts no workspace when signed out and keys workspace per session', () => {
  let session = null;
  const Page = load('../src/app/research/page.tsx', {
    react: {}, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' }, 'lucide-react': icons,
    '@tanstack/react-query': { useQuery: () => { throw new Error('Must not request private data'); } }, ...ui,
    '@/components/ui/page-shell': { PageShell: 'main' }, '@/components/ui/action-dialog': { ActionDialog: () => null },
    '@/components/research/connection-panel': {}, '@/components/research/operation-panel': {}, '@/components/research/stream-panel': {},
    '@/components/research/research-utils': utils, '@/lib/api/borsapy-api': {},
    '@/lib/hooks/use-session': { useSession: () => session },
  }).default;
  assert.match(text(Page()), /giriş yapın/);
  session = { user: { username: 'one', is_admin: true }, expiresAt: 1 };
  const first = descendants(Page()).find(node => typeof node.type === 'function');
  assert.equal(first.props.sessionKey, 'one:1');
  session = { user: { username: 'two', is_admin: true }, expiresAt: 2 };
  const second = descendants(Page()).find(node => typeof node.type === 'function');
  assert.equal(second.props.sessionKey, 'two:2');
  assert.notEqual(second.key, first.key);
  session.user.disabled = true;
  assert.match(text(Page()), /yönetici yetkisi/);
});

const emptyConnection = { installed: true, version: '0.11.0', configured: false, authenticated: false, evds_configured: false, twitter_configured: false, state: 'unconfigured', message: 'Hazır' };
function connectionFixture({ operation = async () => ({}), refreshed = emptyConnection, refreshError = null, initial = emptyConnection } = {}) {
  const writes = [], queryKeys = [];
  let session = { user: { username: 'admin', is_admin: true, disabled: false }, expiresAt: Date.now() + 60_000 };
  let refreshCount = 0;
  const query = {
    data: initial, isError: false,
    async refetch() {
      refreshCount++;
      if (refreshError) { query.isError = true; query.error = refreshError; return { data: query.data, isError: true }; }
      query.data = refreshed;
      return { data: refreshed, isError: false };
    },
  };
  const queryImports = { useQuery: options => { queryKeys.push(plain(options.queryKey)); return query; } };
  const sessionKey = `${session.user.username}:${session.expiresAt}`;
  const component = harness('../src/components/research/connection-panel.tsx', 'ConnectionPanel', {
    '@tanstack/react-query': queryImports,
    '@/components/ui/action-dialog': { ActionDialog: 'dialog' },
    '@/lib/auth/session': { getSession: () => session },
    './research-utils': utils, '@/lib/api/borsapy-api': {
      saveResearchConnection: async (payload, signal) => { writes.push(payload); return operation(signal); },
      verifyResearchConnection: signal => operation(signal),
      clearResearchConnection: signal => operation(signal),
      fetchResearchConnection: async () => query.data,
    },
  }, {}, { sessionKey });
  const market = load('../src/lib/hooks/use-private-market.ts', {
    '@tanstack/react-query': queryImports, './use-session': { useSession: () => session },
    '@/lib/api/borsapy-api': { fetchResearchConnection: async () => query.data },
  });
  return { component, writes, queryKeys, sessionKey, query, market,
    refreshCount: () => refreshCount, setSession: next => { session = next; },
  };
}
function submitConnection(component) {
  for (const [name, value] of [['session', 'secret-session'], ['session_sign', 'secret-sign']]) {
    component.find(node => node.type === 'input' && node.props.name === name).props.onChange({ target: { value } }); component.render();
  }
  component.find(node => node.type === 'form').props.onSubmit({ preventDefault() {} });
  component.render();
}
async function settleConnection(component) {
  for (let i = 0; i < 12; i++) await Promise.resolve();
  component.render();
}

test('connection form sends secrets only in the write call and immediately clears inputs', async () => {
  const fixture = connectionFixture();
  const { component, writes } = fixture;
  submitConnection(component);
  assert.equal(writes.length, 1);
  assert.equal(writes[0].session, 'secret-session');
  assert.ok(component.nodes().filter(node => node.type === 'input').every(node => node.props.value === '' && node.props.type === 'password'));
  await settleConnection(component);
  assert.equal(fixture.refreshCount(), 1);
  assert.ok(!text(component.tree()).includes('secret-session'));
  component.unmount();
});

test('saved credentials with a rejected provider login refresh the shared market status and enable verification', async () => {
  const fixture = connectionFixture({
    operation: async () => { throw { status: 409, message: 'secret-session raw provider error' }; },
    refreshed: { ...emptyConnection, configured: true, state: 'auth_needed', message: 'TradingView oturumu doğrulanamadı.' },
  });
  submitConnection(fixture.component);
  await settleConnection(fixture.component);
  const marketConnection = fixture.market.usePrivateMarket().connection;
  assert.equal(fixture.refreshCount(), 1);
  assert.ok(fixture.queryKeys.every(key => JSON.stringify(key) === JSON.stringify(['borsapy-connection', fixture.sessionKey])));
  assert.equal(marketConnection.data.configured, true, 'Other market consumers observe the same cache entry');
  assert.equal(marketConnection.data.authenticated, false);
  assert.match(text(fixture.component.tree()), /Bağlantı bilgileri sunucuda kayıtlı; TradingView oturumu doğrulanamadı/);
  assert.match(text(fixture.component.tree()), /Kayıtlı · doğrulanmadı/);
  assert.equal(fixture.component.find(node => node.type === 'button' && text(node) === 'Oturumu doğrula').props.disabled, false);
  assert.ok(fixture.component.nodes().filter(node => node.type === 'input').every(node => node.props.value === ''));
  assert.doesNotMatch(text(fixture.component.tree()), /secret-session|raw provider error/);
  fixture.component.unmount();
});

test('verification and removal refresh shared connection state after success or provider failure', async () => {
  for (const action of ['verify', 'clear']) {
    for (const failed of [false, true]) {
      const fixture = connectionFixture({
        initial: { ...emptyConnection, configured: true },
        operation: async () => { if (failed) throw { status: 502 }; return {}; },
        refreshed: action === 'clear' ? emptyConnection : { ...emptyConnection, configured: true, authenticated: !failed },
      });
      if (action === 'verify') fixture.component.find(node => node.type === 'button' && text(node) === 'Oturumu doğrula').props.onClick();
      else fixture.component.find(node => node.type === 'dialog').props.onConfirm();
      await settleConnection(fixture.component);
      assert.equal(fixture.refreshCount(), 1);
      assert.equal(fixture.market.usePrivateMarket().connection.data.configured, action !== 'clear');
      if (failed) assert.match(text(fixture.component.tree()), /İşlem tamamlanamadı/);
      fixture.component.unmount();
    }
  }
});

test('failed status refresh never treats stale configured data as a saved or verified connection', async () => {
  for (const rejected of [false, true]) {
    const fixture = connectionFixture({
      initial: { ...emptyConnection, configured: true, state: 'auth_needed' },
      operation: async () => { if (rejected) throw { status: 409 }; return {}; },
      refreshError: { status: 503 },
    });
    submitConnection(fixture.component);
    await settleConnection(fixture.component);
    const content = text(fixture.component.tree());
    assert.match(content, /Güncel bağlantı durumu alınamadı/);
    if (rejected) assert.match(content, /Sağlayıcı oturumu doğrulanamadı/);
    assert.doesNotMatch(content, /sunucuda kayıtlı|Kayıtlı · doğrulanmadı|sunucuya gönderildi/);
    assert.equal(fixture.component.find(node => node.type === 'button' && text(node) === 'Oturumu doğrula').props.disabled, true);
    fixture.component.unmount();
  }
});

test('a storage error does not present in-memory credentials as successfully saved', async () => {
  const fixture = connectionFixture({
    operation: async () => { throw { status: 503, message: 'private-storage-detail' }; },
    refreshed: { ...emptyConnection, configured: true, evds_configured: true, state: 'storage_error' },
  });
  submitConnection(fixture.component);
  await settleConnection(fixture.component);
  assert.match(text(fixture.component.tree()), /Bağlantı kaydının durumu alınamadı/);
  assert.doesNotMatch(text(fixture.component.tree()), /sunucuda kayıtlı|Kayıtlı · doğrulanmadı|Anahtar kayıtlı|private-storage-detail/);
  fixture.component.unmount();
});

test('a storage error still permits confirmed removal without claiming the old credentials are saved', async () => {
  let finish, clearCount = 0;
  const fixture = connectionFixture({
    initial: { ...emptyConnection, configured: true, evds_configured: true, state: 'storage_error' },
    operation: () => { clearCount++; return new Promise(resolve => { finish = resolve; }); },
    refreshed: emptyConnection,
  });
  const clearButton = () => fixture.component.find(node => node.type === 'button' && text(node) === 'Bağlantıları kaldır');
  assert.equal(clearButton().props.disabled, false);
  assert.equal(fixture.component.find(node => node.type === 'button' && text(node) === 'Oturumu doğrula').props.disabled, true);
  assert.doesNotMatch(text(fixture.component.tree()), /Kayıtlı · doğrulanmadı|Anahtar kayıtlı/);
  clearButton().props.onClick(); fixture.component.render();
  assert.equal(clearCount, 0, 'Opening the confirmation must not delete credentials');
  assert.equal(fixture.component.find(node => node.type === 'dialog').props.open, true);
  fixture.component.find(node => node.type === 'dialog').props.onConfirm(); fixture.component.render();
  assert.equal(clearCount, 1);
  assert.equal(clearButton().props.disabled, true, 'Removal cannot be repeated while pending');
  finish({});
  await settleConnection(fixture.component);
  assert.equal(fixture.refreshCount(), 1);
  assert.equal(fixture.market.usePrivateMarket().connection.data.configured, false);
  assert.equal(fixture.component.find(node => node.type === 'dialog').props.open, false);
  assert.match(text(fixture.component.tree()), /Bağlantı bilgileri kaldırıldı/);
  fixture.component.unmount();
});

test('permission failures, logout, expired or replaced sessions and unmount never trigger a follow-up status request', async () => {
  for (const failure of [401, 403, 'logout', 'expired', 'replaced', 'unmount']) {
    let finish;
    const fixture = connectionFixture({ operation: signal => new Promise((resolve, reject) => { finish = { resolve, reject, signal }; }) });
    submitConnection(fixture.component);
    if (failure === 'logout') fixture.setSession(null);
    if (failure === 'expired') fixture.setSession({ user: { username: 'admin', is_admin: true }, expiresAt: 1 });
    if (failure === 'replaced') fixture.setSession({ user: { username: 'other', is_admin: true }, expiresAt: Date.now() + 60_000 });
    if (failure === 'unmount') { fixture.component.unmount(); assert.equal(finish.signal.aborted, true); }
    if (typeof failure === 'number') finish.reject({ status: failure });
    else finish.resolve({});
    await settleConnection(fixture.component);
    assert.equal(fixture.refreshCount(), 0, String(failure));
    assert.doesNotMatch(text(fixture.component.tree()), /sunucuya gönderildi/);
    fixture.component.unmount();
  }
});

test('stream polling is opt-in, serial, abortable, and stop releases only its own lease', async () => {
  const calls = [], released = [], timers = [];
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  const component = harness('../src/components/research/stream-panel.tsx', 'StreamPanel', {
    '@/lib/api/borsapy-api': { fetchResearchStream: async (...args) => { calls.push(args); return pending; }, stopResearchStream: async input => { released.push(input); } },
    './research-chart': { CandleView: () => null }, './research-utils': utils,
  }, { crypto: { randomUUID: () => 'private-panel-uuid' }, setTimeout: callback => { timers.push(callback); return timers.length; }, clearTimeout() {} });
  assert.equal(calls.length, 0);
  component.find(node => node.type === 'form').props.onSubmit({ preventDefault() {} }); component.render();
  assert.equal(calls.length, 1);
  assert.equal(timers.length, 0, 'No second request scheduled until first completes');
  assert.equal(calls[0][0].subscriberId, 'private-panel-uuid');
  resolve({ state: 'active_unverified', message: 'Veri', quote: null, candles: [], study: null, received_at: null });
  for (let i = 0; i < 5; i++) await Promise.resolve();
  component.render();
  assert.equal(timers.length, 1);
  await component.find(node => node.type === 'button' && text(node) === 'Durdur').props.onClick(); component.render();
  assert.equal(released.length, 1);
  assert.deepEqual(plain(released[0]), plain(calls[0][0]));
  assert.equal(calls[0][1].aborted, true);
  timers[0]();
  assert.equal(calls.length, 1);
  component.unmount();
  assert.equal(released.length, 1, 'Unmount cannot globally close another panel');
});

test('portfolio editor preserves case-sensitive FX aliases and renders editable rows instead of JSON', () => {
  let next;
  const component = harness('../src/components/research/operation-panel.tsx', 'PositionsEditor', {
    '@/lib/api/borsapy-api': {}, './research-chart': {}, './result-table': {}, './value-chart': {}, './research-utils': utils,
  }, {}, { value: '[{"symbol":"gram-altin","shares":1,"cost":2000,"asset_type":"fx"}]', onChange: value => { next = value; } });
  assert.ok(!component.nodes().some(node => node.type === 'textarea'));
  component.find(node => node.type === 'input' && node.props.value === 'gram-altin').props.onChange({ target: { value: 'ons-altin' } });
  assert.equal(JSON.parse(next)[0].symbol, 'ons-altin');
});
