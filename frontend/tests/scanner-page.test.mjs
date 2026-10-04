import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

const compiled = ts.transpileModule(
  readFileSync(new URL('../src/app/scanner/page.tsx', import.meta.url), 'utf8') + '\nexport { SignalHistoryScanner };',
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } },
).outputText;
const PREFS = 'rapot.scanner.preferences.v2';
const LISTS = 'rapot.scanner.watchlists.v2';
const ACTIVE = 'rapot.scanner.watchlists.active.v2';
const now = Date.parse('2026-10-02T12:00:00Z');
const plain = value => JSON.parse(JSON.stringify(value));

function signal(id, symbol, marketType, overrides = {}) {
  return {
    id, symbol, marketType, strategy: 'COMBO', signalType: 'AL', timeframe: '1 GUN', score: '4/4',
    price: 100, createdAt: new Date(now - id * 60_000).toISOString(), details: { RSI: 40 }, ...overrides,
  };
}

function fixtures() {
  return {
    BIST: [
      signal(1, 'THYAO', 'BIST'),
      signal(2, 'GARAN', 'BIST', { price: 120, timeframe: '1 HAFTA', details: { RSI: 60 } }),
      signal(3, 'ASELS', 'BIST', { price: 150, strategy: 'HUNTER', signalType: 'SAT', details: { RSI: 70 } }),
      signal(4, 'THYAO', 'BIST', { price: 80, strategy: 'HUNTER', signalType: 'SAT', timeframe: '1 HAFTA', details: { RSI: 90 } }),
    ],
    Kripto: [signal(5, 'BTCUSDT', 'Kripto', { price: 50, details: { RSI: 60 } })],
  };
}

function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}

function text(element) {
  if (Array.isArray(element)) return element.map(text).join('');
  if (React.isValidElement(element)) return text(element.props.children);
  return typeof element === 'string' || typeof element === 'number' ? String(element) : '';
}

function memoryStorage(initial = {}, { failRead, failWrite } = {}) {
  const data = new Map(Object.entries(initial));
  const reads = [], writes = [];
  return {
    data, reads, writes,
    getItem(key) { reads.push(key); if (failRead?.(key)) throw new Error('Storage blocked'); return data.get(key) ?? null; },
    setItem(key, value) { writes.push(key); if (failWrite?.(key)) throw new Error('Storage full'); data.set(key, value); },
  };
}

function harness({ storage = memoryStorage(), blockedStorage = false, queryOverrides = {}, signals = fixtures(), workspace = false, allowed = true, metricResponse = {} } = {}) {
  const slots = [], requests = [], toasts = [], logs = [], configs = new Map(), timers = new Map();
  let position = 0, effects = [], dirty = false, tree, timerId = 0;
  const different = (a, b) => !a || b.some((value, index) => !Object.is(value, a[index]));
  const hooks = {
    useState(initial) {
      const index = position++;
      slots[index] ??= { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, value => {
        const next = typeof value === 'function' ? value(slots[index].value) : value;
        if (!Object.is(next, slots[index].value)) { slots[index].value = next; dirty = true; }
      }];
    },
    useMemo(factory, deps) {
      const index = position++;
      if (!slots[index] || different(slots[index].deps, deps)) slots[index] = { value: factory(), deps };
      return slots[index].value;
    },
    useEffect(effect, deps) {
      const index = position++;
      const previous = slots[index];
      if (!previous || different(previous.deps, deps)) {
        slots[index] = { deps, cleanup: previous?.cleanup };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  const query = (data, overrides = {}) => ({
    data, isLoading: false, isError: false, isFetching: false, error: null,
    async refetch() { return { data }; }, ...overrides,
  });
  const queries = {
    BIST: query(signals.BIST), Kripto: query(signals.Kripto),
    scanHistory: query([]), logs: query([]), 'special-tag-health': query(undefined), 'market-metrics': query({}),
  };
  for (const [name, override] of Object.entries(queryOverrides)) Object.assign(queries[name], override);
  const window = {
    get localStorage() { if (blockedStorage) throw new Error('Storage denied'); return storage; },
    setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
    clearTimeout(id) { timers.delete(id); },
  };
  const Dialog = () => null;
  const imports = {
    react: hooks, 'react/jsx-runtime': jsxRuntime,
    'lucide-react': Object.fromEntries(['AlertTriangle', 'Check', 'ListPlus', 'RefreshCw', 'Search', 'Settings2', 'Star', 'StarOff', 'X'].map(name => [name, () => null])),
    '@tanstack/react-query': { useQuery(config) {
      const name = config.queryKey[1] === 'signals' ? config.queryKey[2] : config.queryKey[1];
      assert.ok(Object.hasOwn(queries, name), `Unexpected query: ${name}`);
      configs.set(name, config);
      return queries[name];
    } },
    '@/lib/api/client': {
      async fetchSignals(params) { requests.push(['signals', params]); return []; },
      async fetchMarketMetrics(keys) { requests.push(['metrics', keys]); return metricResponse; },
      async fetchScanHistory(limit) { requests.push(['scans', limit]); return []; },
      async fetchLogs(limit) { requests.push(['logs', limit]); return []; },
      async fetchSpecialTagHealth(params) { requests.push(['health', params]); return {}; },
    },
    '@/lib/hooks/use-health': { useBotHealth: () => ({ label: 'Durum bilinmiyor', scanningLabel: 'Bekleniyor', tone: 'neutral', scanCount: null }) },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: allowed ? 'admin:123' : 'guest' }) },
    '@/components/market-data-status': { MarketDataStatus: () => null },
    '@/components/scanner/borsapy-screener': { BorsapyScreener: () => null },
    '@/components/ui/button': { Button: 'button' }, '@/components/ui/input': { Input: 'input' },
    '@/components/ui/select': { Select: 'select' }, '@/components/ui/action-dialog': { ActionDialog: Dialog },
    '@/components/ui/toast': { useToast: () => ({ addToast: toast => toasts.push(toast) }) },
    '@/components/scanner/scan-status': { ScanStatus: () => null },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), getTimeAgo: () => 'az önce' },
  };
  class Clock extends Date { static now() { return now; } }
  const context = vm.createContext({
    exports: {}, window, Date: Clock, console: { error: (...args) => logs.push(args) },
    document: { getElementById(id) { assert.equal(id, 'scanner-search'); return { focus() {} }; } },
    fetch() { assert.fail('Scanner tests must never access a network'); },
    require(name) { assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`); return imports[name]; },
  });
  vm.runInContext(compiled, context);
  const render = () => {
    for (let pass = 0; pass < 30; pass++) {
      dirty = false; position = 0;
      tree = workspace ? context.exports.default() : context.exports.SignalHistoryScanner();
      const scheduled = effects; effects = [];
      scheduled.forEach(effect => effect());
      if (!dirty) return tree;
    }
    assert.fail('Scanner effects did not settle');
  };
  const find = predicate => { const found = descendants(tree).find(predicate); assert.ok(found, 'Expected UI control missing'); return found; };
  const button = name => find(node => node.type === 'button' && (node.props['aria-label'] === name || text(node) === name));
  const h = {
    render, storage, requests, configs, queries, toasts, logs,
    get tree() { return tree; },
    get text() { return text(tree); },
    get dialog() { return find(node => node.type === Dialog); },
    rows() { return descendants(tree).filter(node => node.type === 'tr' && node.props['aria-label']).map(node => node.props['aria-label'].replace(' satırını seç', '')).sort(); },
    row(symbol) { return find(node => node.type === 'tr' && node.props['aria-label'] === `${symbol} satırını seç`); },
    button,
    click(name) { button(name).props.onClick({ stopPropagation() {} }); return render(); },
    select(label, value) {
      const owner = find(node => node.type === 'label' && text(node).startsWith(label));
      descendants(owner).find(node => node.type === 'select').props.onChange({ target: { value } });
      return render();
    },
    search(value) { find(node => node.type === 'input' && node.props.type === 'search').props.onChange({ target: { value } }); return render(); },
    numeric(label, value) {
      h.click(`${label} filtresini düzenle`);
      h.dialog.props.onValueChange(value); render();
      h.dialog.props.onConfirm(); return render();
    },
    updateQuery(name, values) { Object.assign(queries[name], values); return render(); },
    unmount() { for (const slot of slots) slot?.cleanup?.(); },
  };
  render();
  return h;
}

test('scanner retains bounded read-only queries and labels latest-signal filter semantics', async () => {
  const h = harness();
  for (const name of ['BIST', 'Kripto']) await h.configs.get(name).queryFn();
  assert.deepEqual(plain(h.requests), [
    ['signals', { market_type: 'BIST', limit: 700 }], ['signals', { market_type: 'Kripto', limit: 700 }],
  ]);
  assert.match(h.text, /en son 700 sinyal kaydı/);
  assert.match(h.text, /sembolün son sinyaline göre/);
  assert.ok(!h.text.includes('CTRL+K'));
  for (const label of ['Piyasa', 'Son strateji', 'Son sinyal yönü', 'İzleme listesi']) {
    assert.ok(descendants(h.tree).some(node => node.type === 'label' && text(node).startsWith(label) && descendants(node).some(child => child.type === 'select')));
  }
});

test('missing current metrics never display the historical signal price as the current price', () => {
  const h = harness();
  const currentPrice = symbol => descendants(h.row(symbol)).find(node => node.type === 'span' && node.props.title?.includes('Güncel fiyat'));
  assert.equal(text(currentPrice('THYAO')), '—');
  assert.doesNotMatch(text(h.row('THYAO')), /NaN|Infinity/);
  h.updateQuery('market-metrics', { data: { 'BIST:THYAO': { latestPrice: 0, changePct: 0, perf7d: null, perf30d: null, message: 'Sıfır ölçümü' } } });
  const zero = descendants(h.row('THYAO')).find(node => node.type === 'span' && node.props.title === 'Sıfır ölçümü');
  assert.equal(text(zero), '0,00');
  h.updateQuery('market-metrics', { data: {} });
  assert.equal(text(currentPrice('THYAO')), '—');
});

test('scanner workspace keeps private scans behind admin access and separates market scans from history', () => {
  const guest = harness({ workspace: true, allowed: false });
  assert.doesNotMatch(guest.text, /Borsapy piyasa taraması|COMBO \/ HUNTER geçmişi/);
  assert.equal(guest.configs.size, 0);
  const admin = harness({ workspace: true });
  assert.equal(admin.button('Borsapy piyasa taraması').props['aria-selected'], true);
  admin.click('COMBO / HUNTER geçmişi');
  assert.equal(admin.button('COMBO / HUNTER geçmişi').props['aria-selected'], true);
  assert.ok(descendants(admin.tree).some(node => node.type?.name === 'SignalHistoryScanner'));
});

test('current metric rows preserve source and freshness through the actual request adapter', async () => {
  const timestamp = '2026-10-02T09:30:00Z';
  const h = harness({ metricResponse: {
    'BIST:THYAO': { latest_price: 126.8, change_pct: 0, perf_7d: null, perf_30d: null, source: 'borsapy_tradingview', state: 'stale', provider_time: timestamp, received_at: '2026-10-02T12:00:00Z', message: 'Fiyat eskidi' },
    'BIST:GARAN': { latest_price: null, change_pct: null, perf_7d: null, perf_30d: null, source: 'borsapy_tradingview', state: 'waiting', message: 'Güncel fiyat bekleniyor' },
    'Kripto:BTCUSDT': { latest_price: 70000, change_pct: null, perf_7d: null, perf_30d: null, source: 'binance', state: 'ok', provider_time: timestamp },
  } });
  const data = await h.configs.get('market-metrics').queryFn({ signal: new AbortController().signal });
  assert.equal(data['BIST:THYAO'].state, 'stale');
  assert.equal(data['BIST:THYAO'].provider_time, timestamp);
  h.updateQuery('market-metrics', { data });
  assert.match(text(h.row('THYAO')), /Borsapy \/ TradingView · Eski veri/);
  assert.match(text(h.row('THYAO')), /126,80/);
  const priceContext = descendants(h.row('THYAO')).find(node => node.props.title?.includes('Sağlayıcı zamanı:'));
  assert.ok(priceContext.props.title.includes(timestamp));
  assert.ok(priceContext.props.title.includes('Fiyat eskidi'));
  assert.match(text(h.row('GARAN')), /Borsapy \/ TradingView · Veri bekleniyor/);
  assert.equal(text(descendants(h.row('GARAN')).find(node => node.type === 'span' && node.props.title === 'Güncel fiyat bekleniyor')), '—');
  assert.match(text(h.row('BTCUSDT')), /Binance · Veri alındı/);
  assert.ok(descendants(h.tree).some(node => node.type === 'button' && node.props.title?.includes('BIST: sağlayıcının seans değişimi; kripto: Binance son 24 saat')));
});

test('scanner requests only one hundred filtered symbols in bounded chunks and propagates cancellation', async () => {
  const h = harness({ signals: { BIST: Array.from({ length: 150 }, (_, i) => signal(i + 1, `S${String(i).padStart(3, '0')}`, 'BIST')), Kripto: [] } });
  const abort = new AbortController();
  await h.configs.get('market-metrics').queryFn({ signal: abort.signal });
  assert.deepEqual(h.requests.map(request => request[1].length), [50, 50]);
  assert.equal(new Set(h.requests.flatMap(request => [...request[1]])).size, 100);
  h.requests.length = 0;
  h.search('S149');
  await h.configs.get('market-metrics').queryFn({ signal: abort.signal });
  assert.deepEqual(plain(h.requests), [['metrics', ['BIST:S149']]]);
});

test('market, strategy, signal, search and numeric filters combine with AND; periods combine with OR', () => {
  const h = harness();
  assert.deepEqual(h.rows(), ['ASELS', 'BTCUSDT', 'GARAN', 'THYAO']);
  h.select('Piyasa', 'BIST'); h.select('Son strateji', 'COMBO'); h.select('Son sinyal yönü', 'AL');
  assert.deepEqual(h.rows(), ['GARAN', 'THYAO']);
  h.click('1 GUN'); assert.deepEqual(h.rows(), ['THYAO']);
  h.click('1 HAFTA'); assert.deepEqual(h.rows(), ['GARAN', 'THYAO']);
  h.numeric('RSI(14)', '>=50'); assert.deepEqual(h.rows(), ['GARAN']);
  h.search('  gArA  '); assert.deepEqual(h.rows(), ['GARAN']);
  h.search('THYAO'); assert.deepEqual(h.rows(), []);
  assert.match(h.text, /Filtrelere uygun sembol yok/);
});

test('historical matching signals do not override a symbol’s latest strategy, direction or period', () => {
  const h = harness();
  h.select('Son strateji', 'HUNTER'); assert.deepEqual(h.rows(), ['ASELS']);
  h.click('Son strateji: HUNTER filtresini kaldır');
  h.select('Son sinyal yönü', 'SAT'); assert.deepEqual(h.rows(), ['ASELS']);
  h.click('Son yön: SAT filtresini kaldır');
  h.click('1 HAFTA'); assert.deepEqual(h.rows(), ['GARAN']);
});

test('numeric zero, comma decimals and inclusive reversed ranges retain their filter meaning', () => {
  const h = harness({ signals: { BIST: [
    signal(1, 'ZERO', 'BIST', { details: { RSI: 0 } }),
    signal(2, 'LOW', 'BIST', { details: { RSI: 20.5 } }),
    signal(3, 'HIGH', 'BIST', { details: { RSI: 40 } }),
    signal(4, 'MISSING', 'BIST', { details: null }),
  ], Kripto: [] } });
  h.numeric('RSI(14)', '=0'); assert.deepEqual(h.rows(), ['ZERO']);
  h.numeric('RSI(14)', '40..20,5'); assert.deepEqual(h.rows(), ['HIGH', 'LOW']);
  h.numeric('RSI(14)', '<40'); assert.deepEqual(h.rows(), ['LOW', 'ZERO']);
});

test('a filter stays visible and removable after its column is hidden by a view preset', () => {
  const h = harness();
  h.numeric('RSI(14)', '>=50');
  const before = h.rows();
  h.click('Akış');
  assert.deepEqual(h.rows(), before);
  assert.equal(descendants(h.tree).some(node => node.props['aria-label'] === 'RSI(14) filtresini düzenle'), false);
  h.click('RSI(14): >=50 filtresini kaldır');
  assert.deepEqual(h.rows(), ['ASELS', 'BTCUSDT', 'GARAN', 'THYAO']);
});

test('a persisted missing period remains shown as selected and can be removed independently', () => {
  const h = harness({ storage: memoryStorage({ [PREFS]: JSON.stringify({ marketFilter: 'BIST', timeframeFilter: ['15 DAKIKA'] }) }) });
  assert.deepEqual(h.rows(), []);
  assert.equal(h.button('15 DAKIKA').props['aria-pressed'], true);
  h.click('Periyot: 15 DAKIKA filtresini kaldır');
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.ok(h.button('Piyasa: BIST filtresini kaldır'));
});

test('clearing filters preserves lists, selected list and the active view, and never persists search', () => {
  const lists = [{ id: 'own', name: 'Benim listem', symbols: ['BIST:GARAN'] }];
  const storage = memoryStorage({ [LISTS]: JSON.stringify(lists), [ACTIVE]: 'own', [PREFS]: JSON.stringify({ activeView: 'akim', watchOnly: true, marketFilter: 'BIST' }) });
  const h = harness({ storage });
  assert.deepEqual(h.rows(), ['GARAN']);
  h.search('garan'); h.click('Tüm filtreleri temizle');
  assert.deepEqual(h.rows(), ['ASELS', 'BTCUSDT', 'GARAN', 'THYAO']);
  assert.deepEqual(JSON.parse(storage.data.get(LISTS)), lists);
  assert.equal(storage.data.get(ACTIVE), 'own');
  const prefs = JSON.parse(storage.data.get(PREFS));
  assert.equal(prefs.activeView, 'akim');
  assert.equal(prefs.watchOnly, false);
  assert.deepEqual(prefs.timeframeFilter, []);
  assert.deepEqual(prefs.columnFilterInputs, {});
  assert.equal(Object.hasOwn(prefs, 'searchQuery'), false);
  assert.equal(h.button('Akış').props['aria-pressed'], true);
});

test('blocked storage remains usable in memory without uncaught errors or persistence attempts', () => {
  const h = harness({ blockedStorage: true });
  assert.match(h.text, /Değişiklikleri bu oturumda kullanabilirsiniz/);
  h.select('Piyasa', 'Kripto'); assert.deepEqual(h.rows(), ['BTCUSDT']);
  assert.deepEqual(h.storage.writes, []);
});

test('invalid stored JSON is not replaced, while unrelated valid preference keys still restore', () => {
  const storage = memoryStorage({ [LISTS]: '{broken', [ACTIVE]: 'missing', [PREFS]: JSON.stringify({ marketFilter: 'Kripto' }) });
  const h = harness({ storage });
  assert.deepEqual(h.rows(), ['BTCUSDT']);
  assert.equal(storage.data.get(LISTS), '{broken');
  assert.deepEqual(storage.writes, []);
  h.click('Piyasa: Kripto filtresini kaldır');
  assert.equal(storage.data.get(LISTS), '{broken');
  assert.deepEqual(storage.writes, []);
});

test('a failing preference read does not prevent independently restored lists and fallback active id', () => {
  const lists = [{ id: 'first', name: 'İlk liste', symbols: [] }];
  const storage = memoryStorage({ [LISTS]: JSON.stringify(lists), [ACTIVE]: 'deleted' }, { failRead: key => key === PREFS });
  const h = harness({ storage });
  h.click('GARAN BIST izleme listesi');
  assert.equal(h.button('GARAN BIST izleme listesi').props['aria-pressed'], true, 'Fallback displayed list must also receive edits');
  h.click('Yalnız seçili liste'); assert.deepEqual(h.rows(), ['GARAN']);
  assert.deepEqual(storage.writes, []);
  assert.deepEqual(JSON.parse(storage.data.get(LISTS)), lists);
});

test('storage quota errors show an in-memory notice and stop further automatic writes', () => {
  const storage = memoryStorage({}, { failWrite: () => true });
  const h = harness({ storage });
  assert.match(h.text, /kaydedilemedi/);
  const attempted = storage.writes.length;
  h.select('Piyasa', 'Kripto');
  assert.deepEqual(h.rows(), ['BTCUSDT']);
  assert.equal(storage.writes.length, attempted);
});

test('successful rows survive the other market loading or failing and cached refresh failures', () => {
  const h = harness({ queryOverrides: { Kripto: { data: undefined, isLoading: true, isFetching: true } } });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.match(h.text, /Diğer kayıtlar ve fiyat bilgileri yükleniyor/);
  h.updateQuery('Kripto', { isLoading: false, isFetching: false, isError: true });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.match(h.text, /Mevcut kayıtlar gösteriliyor; eksik veya eski olabilir/);
  h.updateQuery('BIST', { isError: true });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.ok(!h.text.includes('Tarama kayıtları yüklenemedi'));
});

test('an initially paused request without data reports waiting rather than successful empty results', () => {
  const paused = { data: undefined, isLoading: false, isFetching: false, isError: false, fetchStatus: 'paused' };
  const h = harness({ queryOverrides: { BIST: paused, Kripto: paused } });
  assert.deepEqual(h.rows(), []);
  assert.match(h.text, /Bağlantı bekleniyor; henüz kayıt alınmadı/);
  assert.ok(!h.text.includes('Henüz tarama kaydı yok'));
  assert.ok(!h.text.includes('Filtrelere uygun sembol yok'));
  assert.ok(!h.text.includes('Tarama kayıtları yüklenemedi'));
  assert.ok(descendants(h.tree).some(node => node.props.role === 'status' && text(node).includes('Bağlantı bekleniyor')));
  h.updateQuery('BIST', { data: [], fetchStatus: 'idle' });
  h.updateQuery('Kripto', { data: [], fetchStatus: 'idle' });
  assert.match(h.text, /Henüz tarama kaydı yok/);
  assert.ok(!h.text.includes('Bağlantı bekleniyor; henüz kayıt alınmadı'));
});

test('a paused missing market or eligible metric request keeps existing rows with a waiting warning', () => {
  const paused = { data: undefined, isLoading: false, isFetching: false, isError: false, fetchStatus: 'paused' };
  const h = harness({ queryOverrides: { Kripto: paused } });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.match(h.text, /Bağlantı bekleniyor; mevcut sonuçlar eksik veya eski olabilir/);
  assert.ok(!h.text.includes('Henüz tarama kaydı yok'));
  h.updateQuery('market-metrics', paused);
  h.updateQuery('Kripto', { data: [], fetchStatus: 'idle' });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.match(h.text, /Bağlantı bekleniyor; mevcut sonuçlar eksik veya eski olabilir/);
  h.updateQuery('market-metrics', { data: {}, fetchStatus: 'idle' });
  assert.deepEqual(h.rows(), ['ASELS', 'GARAN', 'THYAO']);
  assert.ok(!h.text.includes('Bağlantı bekleniyor; mevcut sonuçlar eksik veya eski olabilir'));
});

test('initial loading, full request failure, empty success and empty list have distinct messages', () => {
  const h = harness({ queryOverrides: { BIST: { data: undefined, isLoading: true }, Kripto: { data: undefined, isLoading: true } } });
  assert.match(h.text, /Tarama kayıtları yükleniyor/);
  assert.ok(!h.text.includes('Henüz tarama kaydı yok'));
  h.updateQuery('BIST', { isLoading: false, isError: true });
  h.updateQuery('Kripto', { isLoading: false, isError: true });
  assert.match(h.text, /Tarama kayıtları yüklenemedi/);
  assert.ok(descendants(h.tree).some(node => node.props.role === 'alert'));
  h.updateQuery('BIST', { data: [], isError: false });
  h.updateQuery('Kripto', { data: [], isError: false });
  assert.match(h.text, /Henüz tarama kaydı yok/);
  const emptyList = harness({ storage: memoryStorage({ [LISTS]: JSON.stringify([{ id: 'empty', name: 'Boş', symbols: [] }]), [PREFS]: JSON.stringify({ watchOnly: true }) }) });
  assert.match(emptyList.text, /Seçili izleme listesi boş/);
  emptyList.click('Filtreleri temizle');
  assert.deepEqual(emptyList.rows(), ['ASELS', 'BTCUSDT', 'GARAN', 'THYAO']);
});

test('keyboard events from the watch button are not consumed by row selection', () => {
  const h = harness();
  const row = h.row('GARAN');
  const originalSelection = descendants(h.tree).find(node => node.type === 'tr' && node.props['aria-selected']);
  for (const key of ['Enter', ' ']) {
    let prevented = false;
    row.props.onKeyDown({ key, target: {}, currentTarget: row, preventDefault() { prevented = true; } });
    h.render();
    assert.equal(prevented, false);
    assert.equal(descendants(h.tree).find(node => node.type === 'tr' && node.props['aria-selected']).props['aria-label'], originalSelection.props['aria-label']);
  }
  let prevented = false;
  const ownTarget = {};
  h.row('GARAN').props.onKeyDown({ key: 'Enter', target: ownTarget, currentTarget: ownTarget, preventDefault() { prevented = true; } });
  h.render();
  assert.equal(prevented, true);
  assert.equal(h.row('GARAN').props['aria-selected'], true);
  const initialWatch = h.button('GARAN BIST izleme listesi').props['aria-pressed'];
  h.click('GARAN BIST izleme listesi');
  assert.equal(h.button('GARAN BIST izleme listesi').props['aria-pressed'], !initialWatch);
});

test('sortable headers expose current order and the horizontal table region is keyboard focusable', () => {
  const h = harness();
  const header = label => descendants(h.tree).find(node => node.type === 'th' && text(node).startsWith(label));
  assert.equal(header('Sinyal 24s').props['aria-sort'], 'descending');
  const sortPrice = () => { descendants(header('Fiyat')).find(node => node.type === 'button').props.onClick(); h.render(); };
  sortPrice(); assert.equal(header('Fiyat').props['aria-sort'], 'descending');
  sortPrice(); assert.equal(header('Fiyat').props['aria-sort'], 'ascending');
  assert.equal(header('Sinyal 24s').props['aria-sort'], 'none');
  assert.equal(descendants(h.tree).find(node => node.props.role === 'region').props.tabIndex, 0);
  assert.ok(descendants(h.tree).some(node => node.type === 'caption'));
});
