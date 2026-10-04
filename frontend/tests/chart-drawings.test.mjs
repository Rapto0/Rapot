import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

const read = path => readFileSync(new URL(path, import.meta.url), 'utf8');
function load(source, imports = {}, globals = {}) {
  const context = vm.createContext({ exports: {}, ...globals, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import ${name}`);
    return imports[name];
  } });
  vm.runInContext(ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
  } }).outputText, context);
  return context.exports;
}
const lib = load(read('../src/lib/chart-drawings.ts'));
const plain = value => JSON.parse(JSON.stringify(value));
const candles = Array.from({ length: 10 }, (_, i) => ({ time: 1000 + i * 60, price: 20 + i, open: 19 + i, high: 22 + i, low: 18 + i, close: 20 + i }));
const times = candles.map(c => c.time);
function drawing(tool = 'trend', points = [{ time: 1060, price: 21 }, { time: 1300, price: 25 }]) {
  return { id: 'example-1', tool, points, style: { ...lib.DEFAULT_DRAWING_STYLE }, text: '', hidden: false, locked: false };
}
const ctx = { width: 400, height: 300, candles, times, step: 60,
  project: anchor => ({ x: lib.timeToLogical(anchor.time, times, 60) * 10, y: 100 - anchor.price }) };

test('all 26 catalog tools produce real finite geometry, including all single/three-point tools', () => {
  assert.equal(lib.DRAWING_TOOLS.length, 26);
  assert.equal(new Set(lib.DRAWING_TOOLS.map(t => t.id)).size, 26);
  for (const tool of lib.DRAWING_TOOLS) {
    const points = [{ time: 1060, price: 21 }, { time: 1300, price: 25 }, { time: 1360, price: 18 }].slice(0, tool.points || 3);
    const shapes = lib.drawingGeometry(drawing(tool.id, points), ctx);
    assert.ok(shapes.length > 0, `${tool.id} must be implemented`);
    for (const shape of shapes) {
      for (const point of [...(shape.points ?? []), shape.a, shape.b, shape.at].filter(Boolean)) {
        assert.ok(Number.isFinite(point.x) && Number.isFinite(point.y), tool.id);
      }
    }
  }
});
test('line clipping handles reversed rays, infinite verticals, off-screen lines and coincident anchors', () => {
  assert.deepEqual(plain(lib.clipLine({ x: 20, y: 20 }, { x: 10, y: 20 }, 100, 80, 'ray')), [{ x: 20, y: 20 }, { x: 0, y: 20 }]);
  assert.deepEqual(plain(lib.clipLine({ x: 20, y: 20 }, { x: 20, y: 40 }, 100, 80, 'line')), [{ x: 20, y: 0 }, { x: 20, y: 80 }]);
  assert.equal(lib.clipLine({ x: -2, y: 10 }, { x: -2, y: 20 }, 100, 80, 'line'), null);
  assert.equal(lib.clipLine({ x: 1, y: 1 }, { x: 1, y: 1 }, 100, 80, 'line'), null);
});
test('anchoring round-trips across weekends, fractional bars and future space without shifting UTC instants', () => {
  const friday = Date.parse('2026-10-02T07:00:00Z') / 1000;
  const monday = Date.parse('2026-10-05T07:00:00Z') / 1000;
  const marketTimes = [friday, friday + 3600, monday, monday + 3600];
  for (const index of [-3, 0, .4, 1, 1.6, 2, 3, 7]) {
    const time = lib.logicalToTime(index, marketTimes, 3600);
    assert.ok(Math.abs(lib.timeToLogical(time, marketTimes, 3600) - index) < 1e-9);
  }
  assert.equal(lib.timeToLogical(monday, marketTimes, 3600), 2, 'Weekend is one visual bar gap, not 71 hourly bars');
  assert.equal(lib.logicalToTime(2, marketTimes, 3600), monday);
});
test('OHLC snapping selects nearest existing candle and price but does not invent future bars', () => {
  assert.deepEqual(plain(lib.snapAnchor({ time: 1077, price: 22.7 }, candles, times, 60)), { time: 1060, price: 23 });
  const future = { time: 5000, price: 27.2 };
  assert.equal(lib.snapAnchor(future, candles, times, 60), future);
});
test('Fibonacci retracement and extension calculate price levels, independent of zoom', () => {
  const points = [{ time: 1060, price: 100 }, { time: 1300, price: 200 }, { time: 1360, price: 150 }];
  const fib = lib.drawingGeometry(drawing('fib', points.slice(0, 2)), { ...ctx, project: a => ({ x: a.time - 1000, y: 400 - a.price }) });
  assert.ok(fib.some(s => s.kind === 'text' && s.text === '0,618 · 161,8'));
  const extension = lib.drawingGeometry(drawing('fib-extension', points), { ...ctx, project: a => ({ x: a.time - 1000, y: 500 - a.price }) });
  assert.ok(extension.some(s => s.kind === 'text' && s.text === '1,618 · 311,8'));
});
test('regression uses real candle closes and reports insufficient data instead of a fictitious channel', () => {
  const shapes = lib.drawingGeometry(drawing('regression'), ctx);
  const lines = shapes.filter(s => s.kind === 'line');
  assert.equal(lines.length, 3);
  assert.deepEqual(plain(lines[0].a), { x: 10, y: 79 });
  assert.deepEqual(plain(lines[0].b), { x: 50, y: 75 });
  assert.ok(shapes.some(s => s.kind === 'text' && s.text === '5 mum · ±2σ 0'));
  const empty = lib.drawingGeometry(drawing('regression'), { ...ctx, candles: [] });
  assert.equal(empty[0].text, 'En az iki mevcut mum seçin');
});
test('long and short position drawings validate target/stop direction and calculate risk/reward', () => {
  const long = drawing('long', [{ time: 1000, price: 100 }, { time: 1200, price: 120 }, { time: 1250, price: 90 }]);
  assert.deepEqual(plain(lib.positionMetrics(long)), { risk: 10, reward: 20, ratio: 2 });
  const short = { ...long, tool: 'short', points: [long.points[0], { ...long.points[1], price: 70 }, { ...long.points[2], price: 110 }] };
  assert.equal(lib.positionMetrics(short).ratio, 3);
  assert.equal(lib.positionMetrics({ ...long, tool: 'short' }).ratio, null);
  assert.equal(lib.positionMetrics({ ...long, points: [long.points[0], long.points[1], long.points[0]] }).ratio, null);
});
test('parallel channel, pitchfork, fan and time zones have their own geometry', () => {
  const points = [{ time: 1060, price: 21 }, { time: 1300, price: 25 }, { time: 1360, price: 18 }];
  assert.ok(lib.drawingGeometry(drawing('channel', points), ctx).some(s => s.kind === 'polygon'));
  assert.equal(lib.drawingGeometry(drawing('pitchfork', points), ctx).filter(s => s.kind === 'line').length, 4);
  assert.equal(lib.drawingGeometry(drawing('fib-fan', points.slice(0, 2)), ctx).filter(s => s.kind === 'line').length, 4);
  const zones = lib.drawingGeometry(drawing('fib-time', [{ time: 1000, price: 20 }, { time: 1060, price: 21 }]), ctx);
  assert.deepEqual(plain(zones.filter(s => s.kind === 'line').map(s => s.a.x)), [0, 10, 20, 30, 50, 80, 130]);
});
test('saved drawings contain time/price and survive round trip while projection follows the viewport', () => {
  const original = drawing();
  const raw = lib.serializeDrawings([original]);
  assert.ok(!raw.includes('"x"') && !raw.includes('"y"'));
  assert.deepEqual(plain(lib.parseDrawings(raw).drawings), [original]);
  const first = lib.drawingGeometry(original, ctx)[0];
  const zoomed = lib.drawingGeometry(original, { ...ctx, project: p => ({ x: ctx.project(p).x * 2, y: ctx.project(p).y * 2 }) })[0];
  assert.equal(zoomed.a.x, first.a.x * 2);
  assert.equal(lib.serializeDrawings([original]), raw, 'Zoom must not mutate the stored anchors');
  assert.notEqual(lib.drawingStorageKey('BIST', 'THYAO', '1d'), lib.drawingStorageKey('BIST', 'THYAO', '1h'));
  assert.notEqual(lib.drawingStorageKey('BIST', 'THYAO', '1d'), lib.drawingStorageKey('Kripto', 'THYAO', '1d'));
  assert.equal(lib.drawingStorageKey('BIST', 'thyao ', '1d'), lib.drawingStorageKey('BIST', 'THYAO', '1d'));
});
test('malformed, oversized, executable-style and unbounded persisted objects are rejected atomically', () => {
  const cases = ['not-json', JSON.stringify({ version: 2, drawings: [] }), ' '.repeat(lib.MAX_STORAGE_BYTES + 1)];
  const invalid = [
    { ...drawing(), tool: 'script' }, { ...drawing(), points: [{ time: 1000, price: 3 }] },
    { ...drawing(), points: [{ time: -1, price: 2 }, { time: 1, price: 3 }] },
    { ...drawing(), style: { ...drawing().style, color: 'url(https://example.com)' } },
    { ...drawing(), text: 'a'.repeat(181) }, { ...drawing(), locked: 'false' },
    { ...drawing(), style: { ...drawing().style, fill: 4 } },
    { ...drawing(), tool: 'freehand', points: Array.from({ length: 241 }, () => ({ time: 1, price: 1 })) },
  ];
  for (const d of invalid) cases.push(JSON.stringify({ version: 1, drawings: [drawing(), { ...d, id: 'invalid' }] }));
  cases.push(JSON.stringify({ version: 1, drawings: [drawing(), drawing()] }));
  cases.push(JSON.stringify({ version: 1, drawings: Array.from({ length: 81 }, (_, i) => ({ ...drawing(), id: `row-${i}` })) }));
  for (const raw of cases) {
    const result = lib.parseDrawings(raw);
    assert.ok(result.error);
    assert.equal(result.drawings.length, 0, 'Do not silently discard only part of a corrupt document');
  }
  assert.throws(() => lib.serializeDrawings([{ ...drawing(), points: [{ time: 1000, price: Infinity }, { time: 1060, price: 2 }] }]));
});
test('history groups edits, preserves lock/style/hide states, bounds memory and forks redo correctly', () => {
  const original = drawing();
  let history = { past: [], present: [], future: [] };
  history = lib.changeDrawings(history, [original]);
  const edited = { ...original, hidden: true, locked: true, style: { ...original.style, color: '#ff0000' } };
  history = lib.changeDrawings(history, [edited]);
  assert.deepEqual(plain(lib.undoDrawing(history).present), [original]);
  assert.deepEqual(plain(lib.redoDrawing(lib.undoDrawing(history)).present), [edited]);
  const branch = lib.changeDrawings(lib.undoDrawing(history), []);
  assert.equal(branch.future.length, 0);
  for (let i = 0; i < 60; i++) history = lib.changeDrawings(history, [{ ...edited, text: String(i) }]);
  assert.equal(history.past.length, 35);
  assert.equal(original.hidden, false);
});

function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}
const componentSource = read('../src/components/charts/chart-drawing-tools.tsx');
function harness(initialStorage = new Map(), hiddenTimeScale = false) {
  const slots = [], frames = new Map(), storage = initialStorage;
  let cursor = 0, effects = [], tree, changed = true, frameId = 0, id = 0;
  const writes = [], modes = [], counts = [], listeners = new Set();
  const hooks = {
    useRef(value) { const index = cursor++; return slots[index] ??= { current: value }; },
    useId() { cursor++; return 'drawing-test'; },
    useState(value) { const index = cursor++; if (!(index in slots)) slots[index] = typeof value === 'function' ? value() : value;
      return [slots[index], next => { const value = typeof next === 'function' ? next(slots[index]) : next; if (!Object.is(slots[index], value)) { slots[index] = value; changed = true; } }]; },
    useMemo(factory, deps) { const index = cursor++; if (!slots[index] || deps.some((d, i) => !Object.is(d, slots[index].deps[i]))) slots[index] = { deps, value: factory() }; return slots[index].value; },
    useCallback(callback, deps) { return hooks.useMemo(() => callback, deps); },
    useEffect(effect, deps) { const index = cursor++, previous = slots[index];
      if (!previous || deps.some((d, i) => !Object.is(d, previous.deps[i]))) {
        slots[index] = { deps, cleanup: previous?.cleanup };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  const globals = {
    requestAnimationFrame(callback) { const next = ++frameId; frames.set(next, callback); return next; },
    cancelAnimationFrame(id) { frames.delete(id); },
    ResizeObserver: class { observe() {} disconnect() {} },
    crypto: { randomUUID() { return `drawing-${++id}`; } },
    localStorage: { getItem(key) { return storage.get(key) ?? null; }, setItem(key, value) { writes.push([key, value]); storage.set(key, value); } },
  };
  const imports = { react: hooks, 'react/jsx-runtime': jsxRuntime, '@/lib/chart-drawings': lib,
    '@/lib/utils': { cn: (...v) => v.filter(Boolean).join(' ') },
    'lucide-react': new Proxy({}, { get: () => () => null }),
  };
  const Component = load(componentSource, imports, globals).ChartDrawingTools;
  const timeScale = { width: () => hiddenTimeScale ? 0 : 400, height: () => hiddenTimeScale ? 0 : 20, coordinateToLogical: x => x / 10, logicalToCoordinate: l => l * 10,
    subscribeVisibleLogicalRangeChange(fn) { listeners.add(fn); }, unsubscribeVisibleLogicalRangeChange(fn) { listeners.delete(fn); } };
  const dom = { focus() {}, setPointerCapture() {}, getBoundingClientRect: () => ({ left: 0, top: 0 }), clientHeight: 320, addEventListener() {}, removeEventListener() {} };
  const props = { chartRef: { current: { timeScale: () => timeScale, paneSize: () => ({ width: 400, height: hiddenTimeScale ? 320 : 300 }) } }, seriesRef: { current: { coordinateToPrice: y => 100 - y, priceToCoordinate: p => 100 - p } },
    containerRef: { current: dom }, ready: true, step: 60, market: 'BIST', symbol: 'THYAO', timeframe: '1m',
    candles: candles.map(c => ({ ...c, time: String(c.time) })), parseTime: Number, projectionVersion: 0, open: true,
    onOpenChange(value) { props.open = value; changed = true; }, onDrawingMode(value) { modes.push(value); }, onCountChange(value) { counts.push(value); } };
  function render(patch = {}) {
    Object.assign(props, patch); changed = true;
    for (let safety = 0; changed || effects.length || frames.size; safety++) {
      assert.ok(safety < 25, 'Component effects must settle');
      changed = false; cursor = 0; tree = Component(props);
      for (const node of descendants(tree)) if (node.props.ref && typeof node.props.ref === 'object') node.props.ref.current = dom;
      const runEffects = effects; effects = []; runEffects.forEach(fn => fn());
      const runFrames = [...frames.values()]; frames.clear(); runFrames.forEach(fn => fn());
    }
    return tree;
  }
  const find = predicate => descendants(tree).find(predicate);
  const button = label => find(node => node.type === 'button' && node.props['aria-label'] === label);
  const svg = () => find(node => node.type === 'svg');
  const event = (x, y) => ({ clientX: x, clientY: y, button: 0, pointerId: 1, preventDefault() {}, stopPropagation() {}, currentTarget: dom });
  render();
  return { render, storage, writes, modes, counts, find, button, svg, event,
    tool(toolId) { render({ open: true }); find(node => node.type === 'button' && node.props.title === lib.toolDefinition(toolId).hint).props.onClick(); render(); },
    point(x, y) { svg().props.onPointerDown(event(x, y)); render(); },
    saved() { return plain(lib.parseDrawings(storage.get(lib.drawingStorageKey('BIST', 'THYAO', '1m')) ?? null).drawings); },
    unmount() { slots.forEach(slot => slot?.cleanup?.()); },
    get tree() { return tree; }, get listeners() { return listeners.size; },
  };
}

test('actual chart UI creates a two-point drawing, persists anchors, edits by dragging and undoes one transaction', () => {
  const h = harness();
  assert.equal(h.writes.length, 0, 'Hydration must not rewrite storage');
  h.tool('trend'); h.point(10, 80); h.point(50, 60);
  assert.equal(h.saved().length, 1);
  assert.deepEqual(h.saved()[0].points, [{ time: 1060, price: 20 }, { time: 1300, price: 40 }]);
  const hit = h.find(node => node.type === 'g' && node.props.role === 'button');
  hit.props.onPointerDown(h.event(10, 80)); h.render();
  h.svg().props.onPointerMove(h.event(20, 75)); h.render();
  assert.equal(h.saved()[0].points[0].time, 1060, 'Drag preview must not save individual move events');
  h.svg().props.onPointerUp(); h.render();
  assert.deepEqual(h.saved()[0].points, [{ time: 1120, price: 25 }, { time: 1360, price: 45 }]);
  h.render({ open: true }); h.button('Çizimi geri al').props.onClick(); h.render();
  assert.deepEqual(h.saved()[0].points, [{ time: 1060, price: 20 }, { time: 1300, price: 40 }]);
  h.button('Çizimi yinele').props.onClick(); h.render();
  assert.equal(h.saved()[0].points[0].time, 1120);
  h.unmount(); assert.equal(h.listeners, 0); assert.equal(h.modes.at(-1), false);
});
test('actual UI supports three-anchor drawings, lock prevents drag/delete, and delete can be undone', () => {
  const h = harness(); h.tool('long'); h.point(10, 70); h.point(50, 50);
  assert.equal(h.saved().length, 0); h.point(60, 80); assert.equal(h.saved()[0].points.length, 3);
  h.render({ open: true }); h.button('Çizimi kilitle').props.onClick(); h.render();
  assert.equal(h.saved()[0].locked, true); assert.equal(h.button('Seçili çizimi sil').props.disabled, true);
  h.find(node => node.type === 'g' && node.props.role === 'button').props.onPointerDown(h.event(10, 70));
  h.svg().props.onPointerMove(h.event(30, 40)); h.svg().props.onPointerUp(); h.render();
  assert.equal(h.saved()[0].points[0].time, 1060);
  h.button('Çizim kilidini aç').props.onClick(); h.render(); h.button('Seçili çizimi sil').props.onClick(); h.render();
  assert.equal(h.saved().length, 0); h.button('Çizimi geri al').props.onClick(); h.render(); assert.equal(h.saved().length, 1);
  h.unmount();
});
test('actual UI cancels partial tools, captures freehand strokes, edits text and restores local drawings on remount', () => {
  const h = harness(); h.tool('triangle'); h.point(10, 80);
  h.tree.props.onKeyDown({ key: 'Escape' }); h.render(); assert.equal(h.saved().length, 0);
  h.tool('freehand'); h.point(10, 80);
  h.svg().props.onPointerMove(h.event(20, 70)); h.render(); h.svg().props.onPointerMove(h.event(30, 60)); h.render();
  h.svg().props.onPointerUp(); h.render(); assert.equal(h.saved()[0].points.length, 3);
  h.tool('text'); h.point(25, 50);
  const text = h.find(node => node.type === 'input' && node.props.maxLength === 180);
  text.props.onChange({ target: { value: '<script>not executable</script>' } }); h.render();
  assert.equal(h.saved()[1].text, '<script>not executable</script>');
  h.unmount(); const remount = harness(h.storage); assert.equal(remount.saved().length, 2); assert.equal(remount.writes.length, 0);
  remount.unmount();
});
test('actual UI does not overwrite malformed storage on load; keyboard shortcuts in inputs do not delete drawings', () => {
  const key = lib.drawingStorageKey('BIST', 'THYAO', '1m');
  const storage = new Map([[key, 'corrupt']]); const h = harness(storage);
  assert.equal(storage.get(key), 'corrupt'); assert.equal(h.writes.length, 0);
  assert.ok(h.find(node => node.props.role === 'status'));
  h.tool('horizontal'); h.point(20, 70);
  let prevented = false;
  h.tree.props.onKeyDown({ key: 'Delete', target: { closest: () => ({}) }, preventDefault() { prevented = true; } });
  h.render(); assert.equal(h.saved().length, 1); assert.equal(prevented, false);
  h.unmount();
});

test('a hidden main time axis leaves a full-width drawing pane and accepts separated anchors', () => {
  const h = harness(new Map(), true);
  assert.equal(h.svg().props.width, 400);
  assert.equal(h.svg().props.height, 320);
  h.tool('trend'); h.point(10, 80); h.point(70, 50);
  assert.deepEqual(h.saved()[0].points, [{ time: 1060, price: 20 }, { time: 1420, price: 50 }]);
  h.unmount();
});
