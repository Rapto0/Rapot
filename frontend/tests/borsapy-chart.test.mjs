import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
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

test('each chart releases only its subscriber lease', () => {
    api.fetchBorsapyChartSnapshot('THYAO', '5m', undefined, 'chart-a');
    api.releaseBorsapyChart('THYAO', '5m', 'chart-a');
    const [snapshot, release] = requests.slice(-2);
    assert.equal(snapshot[0], '/api/borsapy/stream?symbol=THYAO&interval=5m&subscriber_id=chart-a');
    assert.equal(release[0], snapshot[0]);
    assert.equal(release[1].method, 'DELETE');
});
