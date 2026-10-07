import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import { QueryClient } from '@tanstack/react-query';
import ts from 'typescript';

const compiled = ts.transpileModule(readFileSync(new URL('../src/lib/api/borsapy-chart-api.ts', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
const requests = [];
const context = vm.createContext({ exports: {}, URLSearchParams,
    require(name) {
        assert.equal(name, './core');
        return { API_BASE_URL: '/api', fetchApi: (...args) => requests.push(args) };
    },
});
vm.runInContext(compiled, context);
const api = context.exports;
const candle = (time, close = 11) => ({ time, open: 10, high: 12, low: 9, close, volume: 100 });
const plain = value => JSON.parse(JSON.stringify(value));

const errorContext = vm.createContext({ exports: {}, require(name) {
    assert.equal(name, 'react/jsx-runtime');
    return jsxRuntime;
} });
vm.runInContext(ts.transpileModule(readFileSync(new URL('../src/components/charts/chart-data-error.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
}).outputText, errorContext);
const { ChartDataError, hasDisplayableCandles } = errorContext.exports;
const errorProps = { message: 'Sunucu şu anda meşgul.', fetching: false, onRetry() {} };

test('forming bar updates replace matching history and new bars append in time order', () => {
    const seconds = Date.parse('2026-10-02T07:00:00Z') / 1000;
    const result = plain(api.mergeBorsapyCandles([candle('2026-10-02T10:00:00+03:00')], [
        candle(seconds + 60, 12), candle(seconds, 10),
    ]));
    assert.equal(result.length, 2);
    assert.equal(result[0].close, 10);
    assert.equal(result[1].time, '2026-10-02T07:01:00.000Z');
});

test('malformed stream prices and timestamps cannot corrupt loaded chart data', () => {
    const history = [candle('2026-10-02T07:00:00Z')];
    const result = plain(api.mergeBorsapyCandles(history, [
        candle(Infinity), candle(1e100), candle(100, NaN), { ...candle(100), high: 5 },
        { ...candle(100), volume: -1 },
    ]));
    assert.deepEqual(result, history);
});

test('chart data calls private endpoints with an explicit interval', () => {
    api.fetchBorsapyCandles('THYAO', '1m');
    api.fetchBorsapyChartSnapshot('GARAN', '1h');
    assert.equal(requests[0][0], '/api/borsapy/candles/THYAO?interval=1m&limit=1000');
    assert.equal(requests[1][0], '/api/borsapy/stream?symbol=GARAN&interval=1h');
    assert.equal(api.BORSAPY_INTERVALS.has('3m'), false);
});

test('missing native volume keeps OHLC candles without inventing zero', () => {
    const seconds = Date.parse('2026-10-07T07:00:00Z') / 1000;
    const rows = plain(api.mergeBorsapyCandles([], [
        { ...candle(seconds), volume: null },
        { ...candle(seconds + 60), volume: undefined },
        { ...candle(seconds + 120), volume: 0 },
        { ...candle(seconds + 180), volume: 1e100 },
    ]));
    assert.equal(rows.length, 3);
    assert.deepEqual(rows.map(row => row.volume), [null, null, 0]);
    assert.ok(rows.every(row => row.close === 11));
    assert.equal(hasDisplayableCandles(rows), true);
});

test('live verified volume never hides unverified historical volume', () => {
    const verified = { state: 'verified', verified: true, message: 'Verified' };
    const unknown = { state: 'unverified', verified: false, message: 'History not verified' };
    const absent = { state: 'unavailable', verified: false, message: 'Volume absent, not zero' };
    assert.equal(api.borsapyVolumeWarning(unknown, verified), unknown.message);
    assert.equal(api.borsapyVolumeWarning(unknown, absent), absent.message);
    assert.equal(api.borsapyVolumeWarning(verified, verified), null);
    assert.equal(api.borsapyVolumeWarning(), null);
});

test('each chart releases only its subscriber lease', () => {
    api.fetchBorsapyChartSnapshot('THYAO', '5m', undefined, 'chart-a');
    api.releaseBorsapyChart('THYAO', '5m', 'chart-a');
    const [snapshot, release] = requests.slice(-2);
    assert.equal(snapshot[0], '/api/borsapy/stream?symbol=THYAO&interval=5m&subscriber_id=chart-a');
    assert.equal(release[0], snapshot[0]);
    assert.equal(release[1].method, 'DELETE');
});

test('failed history refresh retains 1002 history/live candles with a nonblocking warning', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
    const key = ['chart-candles', 'THYAO', 'BIST', '1m', 'borsapy', 'admin', 1234];
    const start = Date.parse('2026-10-05T07:00:00Z');
    const history = Array.from({ length: 1000 }, (_, index) => candle(new Date(start + index * 60000).toISOString()));
    try {
        client.setQueryData(key, { candles: history });
        await assert.rejects(client.fetchQuery({ queryKey: key, queryFn: async () => { throw new Error('busy'); } }));
        const state = client.getQueryState(key);
        assert.equal(state.status, 'error');
        const merged = api.mergeBorsapyCandles(state.data.candles, [candle(start / 1000 + 60000), candle(start / 1000 + 60060)]);
        assert.equal(merged.length, 1002);
        assert.equal(hasDisplayableCandles(merged), true);
        const html = renderToStaticMarkup(ChartDataError({ ...errorProps, mode: 'refresh' }));
        assert.match(html, /mevcut mumlar gösteriliyor/);
        assert.match(html, /Geçmiş veriler güncel olmayabilir/);
        assert.match(html, /Sunucu şu anda meşgul/);
        assert.doesNotMatch(html, /absolute|inset-0|backdrop-blur|Grafik verisi yüklenemedi/);
    } finally { client.clear(); }
});

test('a failed request for a new selection cannot reuse another symbol or timeframe to hide the fatal error', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
    const previous = ['chart-candles', 'THYAO', 'BIST', '1m', 'borsapy', 'admin', 1234];
    try {
        client.setQueryData(previous, { candles: [candle('2026-10-07T07:00:00Z')] });
        for (const selection of [
            ['chart-candles', 'GARAN', 'BIST', '1m', 'borsapy', 'admin', 1234],
            ['chart-candles', 'THYAO', 'BIST', '5m', 'borsapy', 'admin', 1234],
            ['chart-candles', 'THYAO', 'BIST', '1m', 'borsapy', 'admin', 5678],
        ]) {
            await assert.rejects(client.fetchQuery({ queryKey: selection, queryFn: async () => { throw new Error('busy'); } }));
            assert.equal(hasDisplayableCandles(client.getQueryState(selection).data?.candles ?? []), false);
        }
        const html = renderToStaticMarkup(ChartDataError({ ...errorProps, mode: 'fatal' }));
        assert.match(html, /absolute inset-0/);
        assert.match(html, /Grafik verisi yüklenemedi/);
        assert.match(html, /Tekrar dene/);
    } finally { client.clear(); }
});

test('invalid candles alone do not suppress a chart load error', () => {
    assert.equal(hasDisplayableCandles([]), false);
    for (const invalid of [candle('invalid'), candle('2026-10-07', NaN), { ...candle('2026-10-07'), low: 0 }, { ...candle('2026-10-07'), high: 5 }]) {
        assert.equal(hasDisplayableCandles([invalid]), false);
    }
    assert.equal(hasDisplayableCandles([candle('2026-10-07')]), true);
});

test('both error presentations preserve retry and disable it during refresh', () => {
    const findButton = node => {
        if (!node || typeof node !== 'object') return undefined;
        if (node.type === 'button') return node;
        return [node.props?.children].flat(Infinity).map(findButton).find(Boolean);
    };
    for (const mode of ['fatal', 'refresh']) {
        let retries = 0;
        const tree = ChartDataError({ ...errorProps, mode, onRetry: () => retries++ });
        const button = findButton(tree);
        assert.equal(button.props.disabled, false);
        button.props.onClick();
        assert.equal(retries, 1);
        const fetching = ChartDataError({ ...errorProps, mode, fetching: true });
        assert.equal(findButton(fetching).props.disabled, true);
        assert.match(renderToStaticMarkup(fetching), /Yenileniyor/);
    }
});
