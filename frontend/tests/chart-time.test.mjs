import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
const transpile = source => ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
function load(source, imports = {}) {
  const context = vm.createContext({ exports: {}, require(name) { assert.ok(Object.hasOwn(imports, name)); return imports[name]; } });
  vm.runInContext(transpile(source), context);
  return context.exports;
}
const helperSource = read('../src/lib/chart-time.ts');
const helper = load(helperSource);
const chartSource = read('../src/components/charts/advanced-chart.tsx');
const chartAst = ts.createSourceFile('advanced-chart.tsx', chartSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
const parserNames = new Set(['DATE_ONLY_RE', 'INTRADAY_RE', 'parseChartTimeToUnix', 'formatTime']);
const parserSource = chartAst.statements.filter(node => ts.isVariableStatement(node)
  && node.declarationList.declarations.some(declaration => parserNames.has(declaration.name.getText(chartAst))))
  .map(node => node.getText(chartAst)).join('\n') + '\nexport { parseChartTimeToUnix, formatTime };';
const parser = load(parserSource);
const istanbul = helper.createChartTimeFormatters(helper.chartTimeZone('BIST'));
const utc = helper.createChartTimeFormatters(helper.chartTimeZone('Kripto'));
const epoch = Date.parse('2026-10-02T07:00:00Z') / 1000;
const tick = (formatter, time, kind = 3) => formatter.tickMarkFormatter(time, kind, 'en-US');

test('BIST history offsets and UTC stream epochs both display 10:00 without shifting their instant', () => {
  for (const input of ['2026-10-02T10:00:00+03:00', '2026-10-02T07:00:00Z']) {
    const actual = parser.formatTime(input);
    assert.equal(actual, epoch);
    assert.equal(tick(istanbul, actual), '10:00');
    assert.match(istanbul.timeFormatter(actual), /10:00/);
    assert.match(istanbul.timeFormatter(input), /10:00/);
  }
  assert.equal(tick(istanbul, epoch, 4), '10:00:00');
  assert.equal(istanbul.label, 'Türkiye saati (UTC+3)');
});

test('merging live and historical BIST bars retains one unchanged UTC epoch', () => {
  const api = load(read('../src/lib/api/borsapy-chart-api.ts'), { './core': { API_BASE_URL: '/api', fetchApi() { assert.fail('No provider request'); } } });
  const prices = { open: 10, high: 12, low: 9, close: 11, volume: 100 };
  const history = Object.freeze([Object.freeze({ ...prices, time: '2026-10-02T10:00:00+03:00' })]);
  const stream = Object.freeze([Object.freeze({ ...prices, close: 12, time: epoch })]);
  const merged = api.mergeBorsapyCandles(history, stream);
  assert.equal(merged.length, 1);
  assert.equal(parser.formatTime(merged[0].time), epoch);
  assert.equal(merged[0].close, 12);
  assert.equal(tick(istanbul, parser.formatTime(merged[0].time)), '10:00');
  assert.equal(history[0].time, '2026-10-02T10:00:00+03:00');
  assert.equal(stream[0].time, epoch);
});

test('day and year boundaries follow Istanbul for instants and UTC for crypto', () => {
  const boundary = Date.parse('2025-12-31T21:30:00Z') / 1000;
  assert.equal(tick(istanbul, boundary), '00:30');
  assert.equal(tick(istanbul, boundary, 0), '2026');
  assert.equal(tick(istanbul, boundary, 2), '01');
  assert.equal(tick(utc, boundary), '21:30');
  assert.equal(tick(utc, boundary, 0), '2025');
  assert.equal(tick(utc, boundary, 2), '31');
  assert.equal(tick(istanbul, Date.parse('2026-10-02T00:00:00+03:00') / 1000), '00:00');
});

test('BusinessDay and daily date strings retain their calendar date without a time or offset', () => {
  const businessDay = Object.freeze({ year: 2026, month: 1, day: 1 });
  assert.equal(parser.formatTime('2026-01-01'), '2026-01-01');
  assert.equal(parser.parseChartTimeToUnix('2026-01-01'), Date.parse('2026-01-01T00:00:00Z') / 1000);
  for (const formatter of [istanbul, utc]) {
    assert.equal(formatter.timeFormatter(businessDay), formatter.timeFormatter('2026-01-01'));
    assert.doesNotMatch(formatter.timeFormatter(businessDay), /\d{2}:\d{2}/);
    assert.equal(tick(formatter, businessDay, 2), '01');
    assert.equal(tick(formatter, '2026-01-01', 0), '2026');
  }
  assert.equal(istanbul.timeFormatter(businessDay), utc.timeFormatter(businessDay));
});

test('historical Istanbul uses the real winter and summer offsets instead of adding a fixed three hours', () => {
  assert.equal(tick(istanbul, Date.parse('2015-01-15T07:00:00Z') / 1000), '09:00');
  assert.equal(tick(istanbul, Date.parse('2015-07-15T07:00:00Z') / 1000), '10:00');
  assert.equal(tick(istanbul, Date.parse('2026-01-15T07:00:00Z') / 1000), '10:00');
});

test('crypto and legacy naive crypto parsing retain UTC semantics', () => {
  for (const input of ['2026-10-02 07:00:00', '2026-10-02T07:00:00', '2026-10-02T07:00']) {
    assert.equal(parser.parseChartTimeToUnix(input), epoch);
    assert.equal(tick(utc, parser.formatTime(input)), '07:00');
    assert.match(utc.timeFormatter(input), /07:00/);
  }
  assert.match(utc.timeFormatter(epoch), /07:00/);
  assert.equal(utc.label, 'UTC');
});

test('formatting and actual chart parsing are independent of the host timezone', () => {
  const child = `const vm = require('node:vm'); const helper = {exports:{}}; const parser = {exports:{}};
    vm.runInNewContext(${JSON.stringify(transpile(helperSource))}, helper);
    vm.runInNewContext(${JSON.stringify(transpile(parserSource))}, parser);
    const local = helper.exports.createChartTimeFormatters('Europe/Istanbul');
    const utc = helper.exports.createChartTimeFormatters('UTC');
    const result = ['2026-10-02T10:00:00+03:00', '2026-10-02T07:00:00Z', '2026-10-02 07:00:00'].map(value => {
      const instant = parser.exports.parseChartTimeToUnix(value);
      return [instant, local.timeFormatter(instant), utc.timeFormatter(instant)];
    }); console.log(JSON.stringify(result));`;
  const outputs = ['UTC', 'America/Los_Angeles', 'Asia/Tokyo', 'Europe/Istanbul'].map(TZ =>
    execFileSync(process.execPath, ['-e', child], { env: { ...process.env, TZ }, encoding: 'utf8' }).trim());
  assert.ok(outputs.every(output => output === outputs[0]));
});

test('unsupported or unrepresentable times have an empty label rather than breaking chart rendering', () => {
  for (const value of [null, undefined, NaN, Infinity, 1e20, '', 'not-a-date', {}]) {
    assert.equal(istanbul.timeFormatter(value), '');
    assert.equal(tick(istanbul, value), '');
  }
});

function findNodes(node, predicate, result = []) {
  if (predicate(node)) result.push(node);
  ts.forEachChild(node, child => { findNodes(child, predicate, result); });
  return result;
}
test('both real chart update effects switch axis and crosshair formatters without retaining the previous market', () => {
  const effects = findNodes(chartAst, node => ts.isCallExpression(node) && node.expression.getText(chartAst) === 'useEffect'
    && node.arguments[0].getText(chartAst).includes('timeFormattersRef.current = timeFormatters'));
  assert.equal(effects.length, 2, 'Main and every indicator pane have their own formatter update');
  for (const effect of effects) {
    assert.equal(effect.arguments[1].getText(chartAst), '[timeFormatters]');
    const applied = [];
    const ref = { current: { applyOptions: value => applied.push(value) } };
    const context = vm.createContext({ exports: {}, timeFormatters: istanbul, timeFormattersRef: { current: null }, chartInstance: ref, chartRef: ref });
    vm.runInContext(transpile(`exports.update = ${effect.arguments[0].getText(chartAst)};`), context);
    context.exports.update();
    assert.equal(applied[0].timeScale.tickMarkFormatter(epoch, 3, 'en'), '10:00');
    context.timeFormatters = utc;
    context.exports.update();
    assert.equal(applied[1].timeScale.tickMarkFormatter(epoch, 3, 'en'), '07:00');
    assert.match(applied[1].localization.timeFormatter(epoch), /07:00/);
    assert.equal(context.timeFormattersRef.current, utc, 'A later dynamic import reads the latest zone');
  }
});

function mainChartLifecycleHarness() {
  const effects = findNodes(chartAst, node => ts.isCallExpression(node) && node.expression.getText(chartAst) === 'useEffect');
  const visibility = effects.find(node => node.arguments[0].getText(chartAst).includes('showMainTimeScaleRef.current = showMainTimeScale'));
  const creation = effects.find(node => node.arguments[0].getText(chartAst).includes('const candlestickSeries = chart.addSeries'));
  assert.ok(visibility && creation);
  const charts = [];
  const previousDependencies = [];
  const pending = [];
  let effectIndex = 0;
  let fits = 0;
  const chartInstance = { current: null };
  const seriesInstance = { current: null };
  const context = vm.createContext({
    exports: {}, chartInstance, seriesInstance, showMainTimeScaleRef: { current: true },
    chartContainerRef: { current: { clientWidth: 900 } }, markersInstance: { current: null },
    timeFormattersRef: { current: istanbul }, isFullscreen: false, chartColors: {},
    setChartReady() {}, syncIndicatorPanesToMainRange() {}, requestOverlayProjectionRefresh() {},
    window: { innerHeight: 900, addEventListener() {}, removeEventListener() {} },
    useEffect(callback, dependencies) {
      const index = effectIndex++;
      const previous = previousDependencies[index];
      if (!previous || dependencies.some((value, i) => !Object.is(value, previous[i]))) pending.push(callback);
      previousDependencies[index] = dependencies;
    },
    require(name) {
      assert.equal(name, 'lightweight-charts');
      return {
        ColorType: { Solid: 'solid' }, CrosshairMode: { Normal: 0 }, CandlestickSeries: {},
        createChart(_container, options) {
          const chart = {
            options, removed: false, range: { from: 12, to: 34 },
            addSeries() { return { data: [], setData(data) { this.data = data; } }; },
            applyOptions(next) {
              for (const [key, value] of Object.entries(next)) this.options[key] = { ...this.options[key], ...value };
            },
            remove() { this.removed = true; }, subscribeCrosshairMove() {},
            timeScale() {
              return { subscribeVisibleLogicalRangeChange() {}, unsubscribeVisibleLogicalRangeChange() {},
                getVisibleLogicalRange: () => chart.range, fitContent() { fits++; } };
            },
          };
          charts.push(chart);
          return chart;
        },
      };
    },
  });
  // Execute the real component effects with React-style dependency scheduling.
  vm.runInContext(transpile(`exports.render = (showMainTimeScale) => {
    ${visibility.getText(chartAst)};
    ${creation.getText(chartAst)};
  };`), context);
  return {
    charts, chartInstance, seriesInstance, get fits() { return fits; },
    render(visible) {
      effectIndex = 0;
      context.exports.render(visible);
      while (pending.length) pending.shift()();
    },
    flush: () => new Promise(resolve => setImmediate(resolve)),
  };
}

test('adding and removing an indicator pane retains the populated main chart and its zoom', async () => {
  const harness = mainChartLifecycleHarness();
  harness.render(true);
  await harness.flush();
  const chart = harness.chartInstance.current;
  const series = harness.seriesInstance.current;
  const candles = Object.freeze([Object.freeze({ time: epoch, open: 10, high: 12, low: 9, close: 11 })]);
  series.setData(candles);
  const range = chart.range;
  for (const visible of [false, true, false, true]) {
    harness.render(visible);
    await harness.flush();
    assert.equal(harness.charts.length, 1, 'Pane changes must not replace the populated chart');
    assert.equal(harness.chartInstance.current, chart);
    assert.equal(harness.seriesInstance.current, series);
    assert.equal(series.data, candles);
    assert.equal(chart.range, range);
    assert.equal(chart.removed, false);
    assert.equal(chart.options.timeScale.visible, visible);
    assert.equal(chart.options.rightPriceScale.scaleMargins.bottom, visible ? 0.05 : 0.2);
  }
  assert.equal(harness.fits, 0, 'Changing pane visibility must not reset the user zoom');
});

test('a pane opened while the chart module loads uses the latest axis visibility on creation', async () => {
  const harness = mainChartLifecycleHarness();
  harness.render(true);
  harness.render(false);
  await harness.flush();
  assert.equal(harness.charts.length, 1);
  assert.equal(harness.chartInstance.current.options.timeScale.visible, false);
  assert.equal(harness.chartInstance.current.options.rightPriceScale.scaleMargins.bottom, 0.2);
});
