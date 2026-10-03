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

test('connection form sends secrets only in the write call and immediately clears inputs', async () => {
  const writes = [];
  const status = { installed: true, version: '0.11.0', configured: false, authenticated: false, evds_configured: false, twitter_configured: false, message: 'Hazır' };
  const component = harness('../src/components/research/connection-panel.tsx', 'ConnectionPanel', {
    '@tanstack/react-query': { useQuery: () => ({ data: status, refetch: async () => ({ data: status }) }) },
    '@/components/ui/action-dialog': { ActionDialog: () => null }, '@/components/research/research-utils': utils,
    './research-utils': utils, '@/lib/api/borsapy-api': {
      saveResearchConnection: async payload => { writes.push(payload); return status; },
      fetchResearchConnection: async () => status,
    },
  }, {}, { sessionKey: 'admin:1' });
  for (const [name, value] of [['session', 'secret-session'], ['session_sign', 'secret-sign']]) {
    component.find(node => node.type === 'input' && node.props.name === name).props.onChange({ target: { value } }); component.render();
  }
  component.find(node => node.type === 'form').props.onSubmit({ preventDefault() {} });
  component.render();
  assert.equal(writes.length, 1);
  assert.equal(writes[0].session, 'secret-session');
  assert.ok(component.nodes().filter(node => node.type === 'input').every(node => node.props.value === '' && node.props.type === 'password'));
  for (let i = 0; i < 5; i++) await Promise.resolve();
  component.render();
  assert.ok(!text(component.tree()).includes('secret-session'));
  component.unmount();
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
