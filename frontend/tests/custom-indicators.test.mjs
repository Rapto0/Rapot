import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const catalog = JSON.parse(read('./fixtures/custom-indicator-catalog.json'));
const serverRows = JSON.parse(read('./fixtures/custom-indicator-rows.json'));
const plain = value => JSON.parse(JSON.stringify(value));
const nodes = node => React.isValidElement(node) ? [node, ...React.Children.toArray(node.props.children).flatMap(nodes)] : [];
const text = node => Array.isArray(node) ? node.map(text).join('') : React.isValidElement(node) ? text(node.props.children) : typeof node === 'string' || typeof node === 'number' ? String(node) : '';
function load(path, imports = {}, globals = {}) {
    const context = vm.createContext({ exports: {}, TextEncoder, ...globals, require(name) { assert.ok(Object.hasOwn(imports, name), `Unexpected import ${name}`); return imports[name]; } });
    vm.runInContext(ts.transpileModule(read(path), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText, context);
    return context.exports;
}
const ui = { '@/components/ui/button': { Button: 'button' }, '@/components/ui/input': { Input: 'input' }, '@/components/ui/select': { Select: 'select' } };
const helpers = load('../src/components/indicators/custom-indicator-inputs.tsx', { 'react/jsx-runtime': jsxRuntime, ...ui });

test('catalog and preview use authenticated core transport and cancellation without rule writes', async () => {
    const calls = [];
    const api = load('../src/lib/api/custom-indicators-api.ts', { './core': { API_BASE_URL: '/api', fetchApi: async (...args) => { calls.push(args); return {}; } } });
    const signal = new AbortController().signal;
    const request = { indicator: 'rsi_snapshot', inputs: { en1: false, tf7: '7D', tfPts1: 0 }, symbol: 'BTCUSDT', market_type: 'Kripto', chart_timeframe: '1D' };
    await api.fetchCustomIndicatorCatalog(signal);
    await api.previewCustomIndicator(request, signal);
    assert.equal(calls[0][0], '/api/advanced-alarms/indicators/catalog');
    assert.equal(calls[1][0], '/api/advanced-alarms/indicators/preview');
    assert.equal(calls[1][1].method, 'POST');
    assert.equal(calls[0][1].signal, signal);
    assert.equal(calls[1][1].signal, signal);
    assert.deepEqual(JSON.parse(calls[1][1].body), request);
});

for (const spec of catalog.indicators) {
    test(`${spec.id}: every original input renders its default, bounds and change callback`, () => {
        let changed;
        const result = helpers.CustomIndicatorInputs({ spec, value: {}, onChange: value => { changed = value; }, prefix: 'Test' });
        const controls = nodes(result).filter(node => node.type === 'input' || node.type === 'select');
        assert.equal(controls.length, spec.inputs.length);
        for (let index = 0; index < controls.length; index++) {
            const element = controls[index], field = spec.inputs[index];
            assert.equal(element.props['aria-label'], `Test: ${field.group}: ${field.label}`);
            if (field.type === 'bool') {
                assert.equal(element.props.checked, field.default);
                element.props.onChange({ target: { checked: !field.default } });
                assert.equal(changed[field.key], !field.default);
            } else {
                assert.equal(element.props.value, field.default);
                assert.equal(element.props.min, field.min);
                assert.equal(element.props.max, field.max);
                element.props.onChange({ target: { value: String(field.default) } });
                assert.equal(changed[field.key], field.default);
            }
            assert.equal(Object.keys(changed).length, spec.inputs.length);
        }
        assert.deepEqual(plain(helpers.validateCustomInputs(spec, {})), plain(helpers.customDefaults(spec)));
    });
}

test('zero and false are preserved; malformed numeric and boolean values cannot be applied', () => {
    const spec = catalog.indicators[0];
    const result = helpers.validateCustomInputs(spec, { en_1d: false, w_1d: 0 });
    assert.equal(result.en_1d, false);
    assert.equal(result.w_1d, 0);
    for (const value of ['', 'Infinity', NaN, Infinity, 1, 51, 2.5, false]) assert.throws(() => helpers.validateCustomInputs(spec, { rsiLength: value }));
    assert.throws(() => helpers.validateCustomInputs(spec, { showTable: 'false' }));
    const snapshot = catalog.indicators.find(item => item.id === 'rsi_snapshot');
    assert.equal(helpers.validateCustomInputs(snapshot, { tf7: '7D', tf1: '' }).tf7, '7D');
    assert.equal(helpers.validateCustomInputs(snapshot, { tf1: '' }).tf1, '');
    assert.throws(() => helpers.validateCustomInputs(snapshot, { tf1: '1h' }));
});

test('clearing a numeric input retains an invalid value instead of silently turning it into zero', () => {
    const spec = catalog.indicators[0];
    let changed;
    const result = helpers.CustomIndicatorInputs({ spec, value: {}, onChange: value => { changed = value; } });
    nodes(result).find(node => node.props.type === 'number').props.onChange({ target: { value: '' } });
    assert.ok(Number.isNaN(changed.rsiLength));
    assert.throws(() => helpers.validateCustomInputs(spec, changed));
    const rerender = helpers.CustomIndicatorInputs({ spec, value: changed, onChange() {} });
    assert.equal(nodes(rerender).find(node => node.props.type === 'number').props.value, '');
});

test('score plot keeps unknown gaps and valid zero, with a bounded 500 point surface', () => {
    const point = (time, value) => ({ time, outputs: { score: value } });
    const result = helpers.customSeriesPath([point(1, 0), point(2, null), point(3, 20)], 'score');
    assert.equal((result.path.match(/M/g) ?? []).length, 2);
    assert.equal(result.min, 0);
    assert.equal(result.max, 20);
    assert.equal(helpers.customSeriesPath([point(1, null)], 'score'), null);
    assert.equal(helpers.customSeriesPath(Array.from({ length: 600 }, (_, index) => point(index, 0)), 'score').count, 500);
});

test('catalog queries are private-session scoped, cancellable and disabled without an admin', () => {
    let session = null;
    const queries = [], calls = [];
    const loaded = load('../src/components/indicators/custom-indicator-catalog.ts', {
        '@tanstack/react-query': { useQuery(options) { queries.push(options); return {}; } },
        '@/lib/hooks/use-session': { useSession: () => session },
        '@/lib/api/custom-indicators-api': { fetchCustomIndicatorCatalog: signal => calls.push(signal) },
    });
    loaded.useCustomIndicatorCatalog();
    assert.equal(queries.at(-1).enabled, false);
    session = { user: { username: 'one', is_admin: true }, expiresAt: 1 };
    loaded.useCustomIndicatorCatalog();
    const first = queries.at(-1);
    assert.equal(first.enabled, true);
    assert.equal(first.gcTime, 0);
    session = { user: { username: 'two', is_admin: true }, expiresAt: 2 };
    loaded.useCustomIndicatorCatalog();
    assert.notDeepEqual(queries.at(-1).queryKey, first.queryKey);
    const signal = new AbortController().signal;
    first.queryFn({ signal });
    assert.equal(calls[0], signal);
    session.user.disabled = true;
    loaded.useCustomIndicatorCatalog();
    assert.equal(queries.at(-1).enabled, false);
});

function panelHarness({ session = { user: { username: 'one', is_admin: true }, expiresAt: 1 }, data } = {}) {
    let states = [], cursor = 0, outer = true;
    const queries = [], requests = [], transfers = [], navigations = [];
    const hooks = { useState(initial) { if (outer) return [true, () => {}]; const index = cursor++; if (!(index in states)) states[index] = initial; return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }]; } };
    const loaded = load('../src/components/indicators/custom-indicator-panel.tsx', {
        react: hooks, 'react/jsx-runtime': jsxRuntime, 'next/link': { default: 'a' }, ...ui,
        'next/navigation': { useRouter: () => ({ push: path => navigations.push(path) }) },
        '@tanstack/react-query': { useQuery(options) { queries.push(options); return { data: options.enabled ? data : undefined, isFetching: false, isError: false }; } },
        '@/lib/hooks/use-session': { useSession: () => session },
        '@/lib/custom-indicator-presets': { storeCustomIndicatorPreset: (...args) => { transfers.push(args); return 'preset-token'; } },
        '@/lib/api/custom-indicators-api': { previewCustomIndicator: (...args) => { requests.push(args); return data; } },
        './custom-indicator-catalog': { useCustomIndicatorCatalog: () => ({ query: { data: catalog } }) },
        './custom-indicator-inputs': helpers,
    });
    const props = { symbol: 'THYAO', market: 'BIST', timeframe: '1d' };
    const wrapper = loaded.CustomIndicatorPanel(props);
    const workspace = nodes(wrapper).find(node => typeof node.type === 'function');
    outer = false;
    const render = changes => { if (!workspace) return null; cursor = 0; Object.assign(props, changes); return workspace.type({ ...workspace.props, ...props }); };
    return { wrapper, workspace, render, queries, requests, transfers, navigations };
}

test('chart panel mounts no private workspace signed out and replaces it per login identity', () => {
    assert.equal(panelHarness({ session: null }).wrapper, null);
    const first = panelHarness();
    const second = panelHarness({ session: { user: { username: 'two', is_admin: true }, expiresAt: 2 } });
    assert.notEqual(first.workspace.key, second.workspace.key);
});

test('preview starts only on Apply, follows current market/symbol and stops explicitly', async () => {
    const view = panelHarness();
    let tree = view.render();
    assert.equal(view.queries.at(-1).enabled, false);
    assert.equal(view.requests.length, 0);
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    assert.equal(view.queries.at(-1).enabled, true);
    assert.equal(view.queries.at(-1).refetchInterval, 1000);
    assert.equal(view.queries.at(-1).refetchIntervalInBackground, false);
    assert.equal(view.queries.at(-1).gcTime, 0);
    const oldKey = plain(view.queries.at(-1).queryKey);
    view.render({ symbol: 'BTCUSDT', market: 'Kripto', timeframe: '1h' });
    const query = view.queries.at(-1);
    assert.notDeepEqual(plain(query.queryKey), oldKey);
    const signal = new AbortController().signal;
    await query.queryFn({ signal });
    assert.equal(view.requests[0][0].symbol, 'BTCUSDT');
    assert.equal(view.requests[0][0].market_type, 'Kripto');
    assert.equal(view.requests[0][0].chart_timeframe, '1h');
    assert.equal(Object.keys(view.requests[0][0].inputs).length, 24);
    assert.equal(view.requests[0][1], signal);
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Önizlemeyi durdur').props.onClick();
    view.render();
    assert.equal(view.queries.at(-1).enabled, false);
});

test('custom base period is editable independently of the chart and carries into the alarm draft', async () => {
    const view = panelHarness();
    let tree = view.render();
    nodes(tree).find(node => node.props['aria-label'] === 'Gösterge ana periyodu').props.onChange({ target: { value: '3D' } });
    tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    await view.queries.at(-1).queryFn({ signal: undefined });
    assert.equal(view.requests[0][0].chart_timeframe, '3D');
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Bu ayarlarla alarm oluştur').props.onClick();
    assert.equal(view.transfers[0][0].timeframe, '3D');
    assert.equal(view.transfers[0][0].indicator, 'htf_rsi_score');
    assert.equal(Object.keys(view.transfers[0][0].inputs).length, 24);
    assert.equal(view.transfers[0][1], 'one:1');
    assert.equal(view.navigations[0], '/alarms?customPreset=preset-token');
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Grafikteki periyodu kullan').props.onClick();
    tree = view.render();
    assert.match(text(tree), /Son uygulanan ayarlar/);
    assert.equal(nodes(tree).find(node => node.type === 'button' && text(node) === 'Bu ayarlarla alarm oluştur').props.disabled, true);
});

test('stale server state never labels retained numeric output as ready', () => {
    const latest = { time: 1700000000, confirmed: true, ready: true, outputs: { score: 20 }, rows: [] };
    const view = panelHarness({ data: { state: 'stale', reason: 'Veri eski', received_at: 1700000000, source: 'TradingView/BIST', points: [latest], latest } });
    let tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    assert.doesNotMatch(text(tree), /Hesap hazır/);
    assert.match(text(tree), /Güncel sonuç hazır değil/);
    assert.match(text(tree), /Veri yaşı:/);
    assert.match(text(tree), /son hesaplamadır/);
    assert.equal(helpers.customReceivedTime('bad-date'), null);
    assert.equal(helpers.customReceivedTime('2023-11-14T22:13:20Z'), 1700000000);
});

test('settings edits keep applied preview explicit and table visibility obeys showTable', () => {
    const latest = { time: 1700000000, confirmed: false, ready: true, outputs: { score: 0 }, rows: [{ slot: '1d', timeframe: '1D', rsi: 0, ready: true }] };
    const view = panelHarness({ data: { state: 'ready', source: 'TradingView/BIST', points: [latest], latest } });
    let tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    assert.match(text(tree), /Kaynak: TradingView\/BIST/);
    assert.match(text(tree), /Gelişen mum/);
    const form = nodes(tree).find(node => node.type === helpers.CustomIndicatorInputs);
    form.props.onChange({ ...helpers.customDefaults(catalog.indicators[0]), showTable: false });
    tree = view.render();
    assert.match(text(tree), /Son uygulanan ayarlar/);
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    assert.equal(nodes(tree).filter(node => typeof node.type === 'function' && node.type.name === 'ResultRows').length, 0);
});

for (const fixture of serverRows) {
    test(`${fixture.indicator}: actual calculator rows expose oscillator values, thresholds and score details`, () => {
        const latest = fixture.latest;
        const view = panelHarness({ data: { state: 'ready', points: [latest], latest } });
        let tree = view.render();
        nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
        tree = view.render();
        const tableComponent = nodes(tree).find(node => typeof node.type === 'function' && node.type.name === 'ResultRows');
        const table = tableComponent.type(tableComponent.props);
        const all = nodes(table);
        const rowKeys = Object.keys(latest.rows[0]).filter(key => key !== 'value');
        assert.equal(all.filter(node => node.type === 'th').length, rowKeys.length);
        assert.equal(all.filter(node => node.type === 'tr').length, 11);
        const family = fixture.indicator.split('_')[0];
        assert.match(text(table), new RegExp(family === 'htf' ? 'RSI' : family.toUpperCase()));
        if (fixture.indicator.endsWith('_votes')) {
            assert.match(text(table), /DİP eşiği/);
            assert.match(text(table), /TEPE eşiği/);
            assert.doesNotMatch(text(table), /Gösterge değeri/);
        }
        if (fixture.indicator === 'rsi_snapshot') {
            assert.match(text(table), /DİP serisi/);
            assert.match(text(table), /TEPE puanı/);
        }
    });
}

test('generic native oscillator value is visible without a family alias and preserves zero', () => {
    const latest = { ...serverRows[2].latest, rows: [{ slot: 1, timeframe: '1D', value: 0, ready: true }] };
    const view = panelHarness({ data: { state: 'ready', points: [latest], latest } });
    let tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    const component = nodes(tree).find(node => typeof node.type === 'function' && node.type.name === 'ResultRows');
    const table = component.type(component.props);
    assert.match(text(table), /Gösterge değeri/);
    assert.deepEqual(nodes(table).filter(node => node.type === 'td').map(node => text(node)), ['1', '1D', '0', 'Evet']);
});

test('signal history shows only the last twenty computed signal bars, with original timestamps and no delivery claim', () => {
    const points = Array.from({ length: 25 }, (_, index) => ({ time: 1700000000 + index * 86400, confirmed: index !== 24, ready: true, outputs: { score: index, buy_signal: index % 2 ? 1 : 0, sell_signal: index % 2 ? 0 : 1 }, rows: [] }));
    points.push({ time: 1800000000, confirmed: false, ready: false, outputs: { buy_signal: 1, sell_signal: 1 }, rows: [] });
    const view = panelHarness({ data: { state: 'ready', points, latest: points[24] } });
    let tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    const history = nodes(tree).find(node => node.props['aria-label'] === 'Gösterge sinyal geçmişi');
    const items = nodes(history).filter(node => node.type === 'li');
    assert.equal(items.length, 20);
    assert.equal(nodes(items[0]).find(node => node.type === 'time').props.dateTime, new Date(points[24].time * 1000).toISOString());
    assert.match(text(items[0]), /SATMum içi/);
    assert.match(text(history), /gönderilmiş alarm bildirimi değildir/);
    assert.match(text(history), /Saatler TSİ/);
    tree = view.render({ market: 'Kripto' });
    assert.match(text(nodes(tree).find(node => node.props['aria-label'] === 'Gösterge sinyal geçmişi')), /Saatler UTC/);
});

test('custom alarm field selects a full independent configuration and output without making requests', () => {
    let changed;
    const loaded = load('../src/components/indicators/custom-indicator-field.tsx', {
        'react/jsx-runtime': jsxRuntime, ...ui,
        './custom-indicator-catalog': { useCustomIndicatorCatalog: () => ({ allowed: true, query: { data: catalog } }) },
        './custom-indicator-inputs': helpers,
    });
    const value = { field: 'custom', timeframe: '1D', indicator: 'htf_rsi_score', output: 'score', inputs: {} };
    let tree = loaded.CustomIndicatorField({ value, onChange: next => { changed = next; }, label: 'Koşul sol' });
    nodes(tree).find(node => node.props['aria-label'] === 'Koşul sol: özel gösterge').props.onChange({ target: { value: 'rsi_snapshot' } });
    assert.equal(changed.indicator, 'rsi_snapshot');
    assert.equal(changed.output, 'buy_signal');
    assert.equal(changed.timeframe, '1D');
    assert.equal(Object.keys(changed.inputs).length, 73);
    tree = loaded.CustomIndicatorField({ value: changed, onChange: next => { changed = next; }, label: 'Koşul sol' });
    nodes(tree).find(node => node.props['aria-label'] === 'Koşul sol: gösterge çıktısı').props.onChange({ target: { value: 'dip_score' } });
    assert.equal(changed.output, 'dip_score');
    assert.match(text(tree), /Eşittir 1/);
});

test('all five fixture catalogues contain the expected original 289 inputs', () => {
    assert.equal(catalog.indicators.length, 5);
    assert.equal(catalog.indicators.reduce((total, spec) => total + spec.inputs.length, 0), 289);
});

function presetHarness() {
    const stored = new Map();
    const storage = { get length() { return stored.size; }, key: index => [...stored.keys()][index] ?? null, getItem: key => stored.get(key) ?? null, setItem: (key, value) => stored.set(key, value), removeItem: key => stored.delete(key) };
    let clock = 2_000_000, counter = 0;
    const api = load('../src/lib/custom-indicator-presets.ts', {}, { window: { sessionStorage: storage }, crypto: { randomUUID: () => `12345678-1234-1234-1234-${String(++counter).padStart(12, '0')}` }, Date: { now: () => clock } });
    return { api, stored, advance: duration => { clock += duration; } };
}
const preset = { indicator: 'rsi_snapshot', inputs: { en1: false, tf7: '7D', tfPts1: 0 }, timeframe: '1D', symbol: 'THYAO', market_type: 'BIST' };

test('alarm transfer is one-time, identity scoped, bounded and contains configuration only', () => {
    const { api, stored } = presetHarness();
    const first = api.storeCustomIndicatorPreset(preset, 'one:1');
    const other = api.storeCustomIndicatorPreset(preset, 'two:2');
    assert.equal(api.consumeCustomIndicatorPreset(first, 'two:2'), null);
    assert.equal(stored.size, 2);
    assert.deepEqual(plain(api.consumeCustomIndicatorPreset(first, 'one:1')), preset);
    assert.equal(api.consumeCustomIndicatorPreset(first, 'one:1'), null);
    for (let index = 0; index < 10; index++) api.storeCustomIndicatorPreset(preset, 'one:1');
    assert.equal(stored.size, 6); // five own keys and the untouched other identity
    assert.deepEqual(plain(api.consumeCustomIndicatorPreset(other, 'two:2')), preset);
    for (const raw of stored.values()) {
        assert.equal(Object.hasOwn(JSON.parse(raw), 'outputs'), false);
        assert.doesNotMatch(raw, /accessToken|Bearer/);
    }
});

test('expired, forged or malformed transfers cannot create a draft', () => {
    const { api, advance } = presetHarness();
    const token = api.storeCustomIndicatorPreset(preset, 'one:1');
    advance(30 * 60_000 + 1);
    assert.equal(api.consumeCustomIndicatorPreset(token, 'one:1'), null);
    assert.equal(api.consumeCustomIndicatorPreset('../../other-storage', 'one:1'), null);
    assert.throws(() => api.storeCustomIndicatorPreset({ ...preset, indicator: 'other' }, 'one:1'));
    assert.throws(() => api.storeCustomIndicatorPreset({ ...preset, inputs: { len1: NaN } }, 'one:1'));
    assert.throws(() => api.storeCustomIndicatorPreset({ ...preset, inputs: { text: 'x'.repeat(6000) } }, 'one:1'));
});


test('preview separates native bar time from the shared current price observation time', () => {
    const latest = { time: 1791853200, confirmed: false, ready: true, outputs: { score: 20 }, rows: [] };
    const view = panelHarness({ data: { state: 'ready', source_timestamp: '2026-10-13T07:02:03Z', received_at: '2026-10-13T07:02:04Z', source: 'TradingView/BIST', points: [latest], latest } });
    let tree = view.render();
    nodes(tree).find(node => node.type === 'button' && text(node) === 'Ayarları uygula ve izle').props.onClick();
    tree = view.render();
    assert.match(text(tree), /Bütün etkin periyotların ortak fiyat zamanı:/);
    assert.match(text(tree), /10:02:03/);
    assert.match(text(tree), /alarm bu ekranı beklemeden/);
    assert.equal(view.queries.at(-1).refetchInterval, 1000);
    assert.equal(view.queries.at(-1).refetchIntervalInBackground, false);
});
