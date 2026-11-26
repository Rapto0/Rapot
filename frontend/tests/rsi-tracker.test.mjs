import assert from 'node:assert/strict';
import test from 'node:test';
import { load, hooks, nodes, text, primitives } from './view-harness.mjs';

const model = load('../src/lib/rsi-tracker.ts');
const symbols = Array.from({ length: 53 }, (_, index) => `PAY${String(index).padStart(2, '0')}`);

function tracker({ allowed = true, responses = {}, bistQuote = {}, rsiRows = {}, rsiQuery = {}, lists = [] } = {}) {
  const state = hooks();
  const queries = [], requests = [], snapshots = [], streams = [], intervals = [];
  let mounted = false;
  const source = load('../src/components/scanner/rsi-tracker.tsx', { ...primitives,
    react: { ...state.react, useEffect(effect, deps) {
      if (!mounted && deps.length === 0) effect();
    } },
    '@tanstack/react-query': { useQuery: options => {
      queries.push(options);
      if (options.queryKey[0] === 'rsi-tracker-values') return { data: { rows: rsiRows }, dataUpdatedAt: 0, refetch: () => requests.push('refresh-rsi'), ...rsiQuery };
      if (options.queryKey[0] === 'rsi-tracker-watchlists') return { data: { watchlists: lists }, refetch: () => requests.push('refresh-watchlists') };
      return { data: { symbols: options.queryKey[2] === 'BIST' ? symbols : ['BTCUSDT', 'ETHUSDT'] },
        refetch: () => requests.push('refresh-symbols'), ...responses[options.queryKey[2]] };
    } },
    '@/lib/api/ops-api': {
      fetchBistSymbols: signal => { requests.push(['BIST', signal]); },
      fetchCryptoSymbols: signal => { requests.push(['Kripto', signal]); },
      fetchRsiSnapshot: (...args) => { requests.push(['RSI', ...args]); },
    },
    '@/lib/api/advanced-alarms-api': { fetchServerWatchlists: signal => requests.push(['watchlists', signal]) },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: 'admin:100' }) },
    '@/lib/hooks/use-market-snapshot': { useMarketSnapshot: (values, interval) => {
      snapshots.push(Array.from(values));
      intervals.push(interval);
      return { data: bistQuote, dataUpdatedAt: 0, refetch: () => requests.push('refresh-quotes') };
    } },
    '@/lib/hooks/use-binance-ticker': { useBinanceTickerFeed: (values, options) => {
      streams.push({ values: Array.from(values), ...options });
      return { prices: {}, receivedAtBySymbol: {}, status: 'connecting', flush: () => requests.push('refresh-crypto') };
    } },
    '@/lib/rsi-tracker': model,
  }, `\nconst window = { crypto: { randomUUID: () => '12345678-test-1234-1234-123456789abc' } };`);
  state.reset(); source.RsiTracker(); mounted = true;
  return { queries, requests, snapshots, streams, intervals, render() { state.reset(); return source.RsiTracker(); } };
}

const button = (tree, label) => nodes(tree).find(node => node.type === 'button' && text(node) === label);
const symbolRows = tree => nodes(tree).filter(node => node.type === 'th' && node.props.scope === 'row');

test('tracker contains all sixteen unambiguous periods including two calendar months', () => {
  assert.deepEqual(Array.from(model.RSI_TIMEFRAMES, item => item.id),
    ['15m', '30m', '1h', '2h', '4h', '1D', '2D', '3D', '4D', '5D', '6D', '1W', '2W', '3W', '1M', '2M']);
  assert.equal(model.RSI_TIMEFRAMES.at(-1).label, '2 ay');
  assert.equal(new Set(model.RSI_TIMEFRAMES.map(item => item.short)).size, 16);
});

test('symbol normalization, search, ordering and pagination exclude malformed or duplicate entries', () => {
  const page = model.trackerPage([...symbols, ' pay00 ', '', '<script>', 'PAY00'], '', false, 900);
  assert.equal(page.total, 53); assert.equal(page.page, 2); assert.equal(page.pages, 3);
  assert.deepEqual(Array.from(page.rows), ['PAY50', 'PAY51', 'PAY52']);
  const search = model.trackerPage(['SISE', 'THYAO', 'ISCTR'], 'si', false, 1);
  assert.deepEqual(Array.from(search.rows), ['SISE']); assert.equal(search.page, 0);
  assert.deepEqual(Array.from(model.trackerPage(['A', 'B'], '', true, NaN).rows), ['B', 'A']);
  for (const payload of [null, undefined, {}, 'THYAO', 123]) assert.equal(model.trackerPage(payload, '', false, 0).total, 0);
  assert.deepEqual(Array.from(model.trackerPage(['THYAO', null, {}, 42], '', false, 0).rows), ['THYAO']);
});

test('column selection preserves at least one period and canonical order', () => {
  assert.deepEqual(Array.from(model.toggleRsiColumn(['1M'], '1M')), ['1M']);
  assert.deepEqual(Array.from(model.toggleRsiColumn(['1M'], '15m')), ['15m', '1M']);
  assert.deepEqual(Array.from(model.toggleRsiColumn(['15m', '1M'], '15m')), ['1M']);
});

test('chart links carry explicit market and price formatting never invents zero for missing data', () => {
  assert.equal(model.trackerChartHref('THYAO', 'BIST'), '/chart?symbol=THYAO&market=BIST');
  assert.equal(model.trackerChartHref('BTCUSDT', 'Kripto'), '/chart?symbol=BTCUSDT&market=Kripto');
  for (const value of [null, undefined, NaN, Infinity]) assert.equal(model.trackerNumber(value), '—');
  assert.equal(model.trackerNumber(0), '0');
});

test('active market automatically subscribes only its fixed page of 25 symbols', async () => {
  const app = tracker(); const tree = app.render(); const query = app.queries.findLast(query => query.queryKey[0] === 'rsi-tracker-symbols');
  assert.deepEqual(Array.from(query.queryKey), ['rsi-tracker-symbols', 'admin:100', 'BIST']);
  assert.equal(query.enabled, true); assert.equal(query.staleTime, 300_000); assert.equal(query.retry, false);
  assert.equal(query.placeholderData, undefined);
  assert.equal(symbolRows(tree).length, 25);
  assert.equal(app.snapshots.at(-1).length, 25);
  assert.ok(app.snapshots.at(-1).every(symbol => symbol.endsWith('.IS')));
  assert.deepEqual(app.streams.at(-1).values, []); assert.equal(app.streams.at(-1).paused, true);
  assert.deepEqual(app.requests, []);
  const signal = new AbortController().signal; await query.queryFn({ signal });
  assert.deepEqual(app.requests, [['BIST', signal]]);
  assert.equal(app.queries.at(-1).enabled, true);
  await app.queries.at(-1).queryFn({ signal });
  assert.equal(app.requests.at(-1)[3].length, 25);
  assert.equal(nodes(tree).filter(node => node.type === 'td' && node.props.title === 'Veri hazırlanıyor').length, 25 * 16);
});

test('switching markets resets page and search, retires BIST reads and never displays old market rows', async () => {
  const app = tracker(); let tree = app.render();
  button(tree, 'Sonraki').props.onClick(); tree = app.render();
  assert.match(text(symbolRows(tree)[0]), /PAY25/);
  nodes(tree).find(node => node.type === 'input' && node.props.type === 'search').props.onChange({ target: { value: 'PAY' } });
  button(tree, 'Kripto').props.onClick(); tree = app.render();
  assert.equal(nodes(tree).find(node => node.type === 'input' && node.props.type === 'search').props.value, '');
  assert.match(text(tree), /BTCUSDT/); assert.doesNotMatch(text(tree), /PAY25/);
  assert.deepEqual(app.snapshots.at(-1), []);
  assert.deepEqual(app.streams.at(-1).values, ['BTCUSDT', 'ETHUSDT']);
  assert.equal(app.streams.at(-1).paused, false);
  const query = app.queries.findLast(query => query.queryKey[0] === 'rsi-tracker-symbols'), signal = new AbortController().signal;
  assert.deepEqual(Array.from(query.queryKey), ['rsi-tracker-symbols', 'admin:100', 'Kripto']);
  await query.queryFn({ signal }); assert.deepEqual(app.requests, [['Kripto', signal]]);
});

test('page replacement keeps the lease identity and only submits the new 25 members', async () => {
  const app = tracker({ rsiRows: { PAY00: { source_time: 1794651000, price: 42, cells: {
    '15m': { status: 'ready', value: 0, bar_time: 1794650400 },
    '1D': { status: 'candle', value: 71.123, bar_time: 1794614400 },
  } } } });
  let tree = app.render();
  assert.match(text(tree), /0Güncel fiyatla hesaplandı/);
  assert.match(text(tree), /71,12Son mum kaydı/);
  const signal = new AbortController().signal;
  await app.queries.at(-1).queryFn({ signal });
  const first = app.requests.at(-1);
  assert.equal(first[3].length, 25); assert.equal(first[4].length, 16);
  button(tree, 'Sonraki').props.onClick(); tree = app.render();
  await app.queries.at(-1).queryFn({ signal });
  const next = app.requests.at(-1);
  assert.equal(next[1], first[1]);
  assert.deepEqual(Array.from(next[3]), symbols.slice(25, 50));
  assert.doesNotMatch(text(tree), /71,12/);
  button(tree, 'Kripto').props.onClick(); tree = app.render();
  await app.queries.at(-1).queryFn({ signal });
  assert.deepEqual(Array.from(app.requests.at(-1)[3]), ['BTCUSDT', 'ETHUSDT']);
  assert.equal(app.requests.at(-1)[2], 'Kripto');
  assert.equal(app.requests.at(-1)[1], first[1]);
});

test('scanner bounds preparation checks and the refresh button immediately requests active data', async () => {
  const app = tracker();
  let tree = app.render();
  const values = app.queries.findLast(options => options.queryKey[0] === 'rsi-tracker-values');
  const lists = app.queries.findLast(options => options.queryKey[0] === 'rsi-tracker-watchlists');
  const data = { rows: { PAY00: { cells: { '1D': { status: 'waiting' } } } } };
  assert.equal(lists.refetchInterval, 120_000);
  assert.equal(values.refetchIntervalInBackground, false);
  await values.queryFn({ signal: new AbortController().signal });
  app.requests.length = 0;
  assert.equal(values.refetchInterval({ state: { status: 'success', data } }), 10_000);
  assert.equal(values.refetchInterval({ state: { status: 'error', data } }), 120_000);
  assert.equal(model.trackerPollInterval(data, 1_000, 51_000), 10_000);
  assert.equal(model.trackerPollInterval(data, 1_000, 51_001), 120_000);
  assert.equal(model.trackerPollInterval({ rows: {} }, 1_000, 1_000), 120_000);
  assert.equal(app.intervals.at(-1), 120_000);
  assert.equal(app.streams.at(-1).flushIntervalMs, 120_000);
  button(tree, 'Yenile').props.onClick();
  assert.deepEqual(app.requests.splice(0), ['refresh-symbols', 'refresh-watchlists', 'refresh-rsi', 'refresh-quotes']);
  button(tree, 'Kripto').props.onClick(); tree = app.render();
  button(tree, 'Yenile').props.onClick();
  assert.deepEqual(app.requests, ['refresh-symbols', 'refresh-watchlists', 'refresh-rsi', 'refresh-crypto']);
});

test('sign-out suppresses cached symbols, provider subscriptions and queries', () => {
  const app = tracker({ allowed: false }); const tree = app.render();
  assert.equal(app.queries.at(-1).enabled, false);
  assert.deepEqual(app.snapshots.at(-1), []); assert.deepEqual(app.streams.at(-1).values, []);
  assert.equal(app.streams.at(-1).paused, true);
  assert.doesNotMatch(text(tree), /PAY00/); assert.match(text(tree), /yönetici girişi/);
});

test('column picker removes columns, keeps the last one, and restores all periods', () => {
  const app = tracker(); let tree = app.render();
  nodes(tree).find(node => node.props['aria-controls'] === 'rsi-column-picker').props.onClick(); tree = app.render();
  for (let index = 0; index < 15; index++) { nodes(tree).filter(node => node.type === 'input' && node.props.type === 'checkbox')[index].props.onChange(); tree = app.render(); }
  tree = app.render();
  const choices = nodes(tree).filter(node => node.type === 'input' && node.props.type === 'checkbox');
  assert.equal(choices.filter(node => node.props.checked).length, 1);
  assert.equal(choices.at(-1).props.disabled, true);
  assert.equal(nodes(tree).filter(node => node.type === 'th' && node.props['aria-label']?.startsWith('RSI ')).length, 1);
  button(tree, 'Tüm sütunlar').props.onClick(); tree = app.render();
  assert.equal(nodes(tree).filter(node => node.type === 'th' && node.props['aria-label']?.startsWith('RSI ')).length, 16);
});

test('empty search, unavailable source and stale list errors remain distinct', () => {
  const empty = tracker(); let tree = empty.render();
  nodes(tree).find(node => node.type === 'input' && node.props.type === 'search').props.onChange({ target: { value: 'ZZZZ' } });
  tree = empty.render(); assert.match(text(tree), /Aramanızla eşleşen sembol yok/);
  assert.deepEqual(empty.snapshots.at(-1), []);
  const unavailable = tracker({ responses: { BIST: { data: undefined, isError: true } } }).render();
  assert.match(text(unavailable), /Sembol listesine erişilemiyor/); assert.doesNotMatch(text(unavailable), /eşleşen sembol yok/);
  const stale = tracker({ responses: { BIST: { isError: true } } }).render();
  assert.match(text(stale), /Son alınan liste gösteriliyor; güncel olmayabilir/);
  assert.equal(symbolRows(stale).length, 25);
});


test('saved column preferences allowlist known periods and reject empty or malformed storage', () => {
  for (const raw of [null, 'bad', '[]', '{}', '["secret"]', 'null']) {
    assert.deepEqual(Array.from(model.storedRsiColumns(raw)), Array.from(model.ALL_RSI_COLUMNS));
  }
  assert.deepEqual(Array.from(model.storedRsiColumns('["2M","1D","secret","1D"]')), ['1D', '2M']);
});

test('RSI filtering combines periods and excludes missing, candle, stale and invalid values', () => {
  const snapshot = { rows: {} };
  const cell = (value, status = 'ready') => ({ value, status, bar_time: 99 });
  for (const symbol of ['A', 'B', 'C', 'D', 'E']) snapshot.rows[symbol] = { source_time: 100, cells: { '1D': cell(20), '2W': cell(70) } };
  snapshot.rows.B.cells['2W'].value = 90;
  snapshot.rows.C.cells['1D'].status = 'candle';
  snapshot.rows.D.source_time = 20;
  snapshot.rows.E.cells['1D'].value = NaN;
  const filters = [{ period: '1D', min: '0', max: '30' }, { period: '2W', min: '50', max: '80' }];
  assert.deepEqual(Array.from(model.trackerResultRows(['A', 'B', 'C', 'D', 'E', 'MISSING'], snapshot, filters, null, true, 101)), ['A']);
  assert.equal(model.trackerResultRows(['A'], snapshot, filters, null, false, 101).length, 0);
  assert.equal(model.trackerResultRows(['A'], snapshot, [{ period: '1D', min: '90', max: '20' }], null, true, 101).length, 0);
  assert.equal(model.trackerResultRows(['A'], snapshot, [{ period: '1D', min: 'bad', max: '' }], null, true, 101).length, 0);
  assert.deepEqual(Array.from(model.trackerResultRows(['A', 'C', 'MISSING'], snapshot, [], null, false, 101)), ['A', 'C', 'MISSING']);
});

test('RSI sorting keeps missing or stale observations last in both directions', () => {
  const snapshot = { rows: { A: { source_time: 100, cells: { '1D': { value: 0, status: 'ready' } } },
    B: { source_time: 100, cells: { '1D': { value: 80, status: 'ready' } } },
    C: { source_time: 10, cells: { '1D': { value: 90, status: 'ready' } } } } };
  assert.deepEqual(Array.from(model.trackerResultRows(['B', 'C', 'A'], snapshot, [], { period: '1D', descending: false }, true, 101)), ['A', 'B', 'C']);
  assert.deepEqual(Array.from(model.trackerResultRows(['A', 'C', 'B'], snapshot, [], { period: '1D', descending: true }, true, 101)), ['B', 'A', 'C']);
});

test('watchlist selection is read-only, separates markets and excludes unsupported members', async () => {
  const app = tracker({ lists: [{ id: 'mine', name: 'Karma', symbols: [{ market_type: 'BIST', symbol: 'PAY01' },
    { market_type: 'Kripto', symbol: 'BTCUSDT' }, { market_type: 'BIST', symbol: 'NOTSUPPORTED' }] }] });
  let tree = app.render();
  nodes(tree).find(node => node.props['aria-label'] === 'İzleme listesi').props.onChange({ target: { value: 'mine' } });
  tree = app.render();
  assert.equal(symbolRows(tree).length, 1); assert.match(text(symbolRows(tree)[0]), /PAY01/);
  assert.match(text(tree), /1 liste üyesi/);
  button(tree, 'Kripto').props.onClick(); tree = app.render();
  assert.equal(symbolRows(tree).length, 1); assert.match(text(symbolRows(tree)[0]), /BTCUSDT/);
  const signal = new AbortController().signal;
  await app.queries.findLast(query => query.queryKey[0] === 'rsi-tracker-watchlists').queryFn({ signal });
  assert.deepEqual(app.requests, [['watchlists', signal]]);
});

test('filtering the displayed page never changes the subscribed page or provider scope', async () => {
  const app = tracker({ rsiRows: { PAY00: { source_time: 1794651000, cells: { '15m': { value: 20, status: 'ready' } } } } });
  let tree = app.render();
  button(tree, 'RSI koşulu ekle').props.onClick(); tree = app.render();
  nodes(tree).find(node => node.props['aria-label'] === 'RSI koşulu 1 en çok').props.onChange({ target: { value: '30' } });
  tree = app.render();
  assert.equal(symbolRows(tree).length, 1);
  assert.match(text(tree), /1 \/ 25 sembol/);
  assert.match(text(tree), /Diğer sayfalar değerlendirilmedi/);
  await app.queries.at(-1).queryFn({ signal: undefined });
  assert.deepEqual(Array.from(app.requests.at(-1)[3]), symbols.slice(0, 25));
  button(tree, 'RSI koşullarını temizle').props.onClick(); tree = app.render();
  assert.equal(symbolRows(tree).length, 25);
});

test('URL serialization, readiness summary, alarm links, presets and CSV export stay safe and exact', () => {
  const encoded = model.serializeTrackerUrlState({
    market: 'Kripto', search: 'BTC', descending: true, page: 2, listId: 'list-1',
    filters: [{ period: '1D', min: '0', max: '30' }], sort: { period: '15m', descending: false },
  });
  const parsed = model.parseTrackerUrlState(`?${encoded}`);
  assert.equal(parsed.market, 'Kripto');
  assert.equal(parsed.search, 'BTC');
  assert.equal(parsed.descending, true);
  assert.equal(parsed.page, 2);
  assert.equal(parsed.listId, 'list-1');
  assert.deepEqual(JSON.parse(JSON.stringify(parsed.filters)), [{ period: '1D', min: '0', max: '30' }]);
  assert.deepEqual(JSON.parse(JSON.stringify(parsed.sort)), { period: '15m', descending: false });
  assert.equal(model.parseTrackerUrlState('?market=INVALID&page=-3&filters=BAD:1:2,1D:999:0').market, undefined);

  assert.equal(model.trackerAlarmHref('THYAO', 'BIST'), '/alarms?symbol=THYAO&market=BIST');
  const summary = model.summarizeRsiCells(['A', 'B'], {
    rows: {
      A: { source_time: 100, price: 10, cells: { '15m': { status: 'ready', value: 25, bar_time: 90 }, '1D': { status: 'insufficient', value: null, bar_time: null } } },
      B: { source_time: null, price: null, cells: { '15m': { status: 'waiting', value: null, bar_time: null }, '1D': { status: 'candle', value: 55, bar_time: 80 } } },
    },
  }, ['15m', '1D']);
  assert.deepEqual(JSON.parse(JSON.stringify(summary)), {
    total: 4, numeric: 2, ready: 1, stale: 0, candle: 1, retained: 0, waiting: 1, insufficient: 1, other: 0, percent: 75,
  });

  const csv = model.buildTrackerCsv(['THYAO', '=CMD'], 'BIST', { THYAO: { price: 312.5, change: 1.25 } }, {
    rows: { THYAO: { source_time: 100, price: 312.5, cells: { '1D': { status: 'ready', value: 28.456, bar_time: 90 } } } },
  }, ['1D']);
  assert.ok(csv.startsWith('\uFEFF'));
  assert.match(csv, /THYAO,BIST,312\.5,1\.25,28\.46/);
  assert.match(csv, /'=CMD,BIST,,,/);

  const app = tracker({ rsiRows: { PAY00: { source_time: 1794651000, cells: { '1D': { value: 22, status: 'ready' } } } } });
  let tree = app.render();
  assert.match(text(tree), /1 \/ 400 hücre sayısal/);
  button(tree, 'Aşırı satım (1G ≤ 30)').props.onClick(); tree = app.render();
  assert.equal(symbolRows(tree).length, 1);
  assert.match(text(symbolRows(tree)[0]), /PAY00/);
});

test('last records survive a timeout with labels and never satisfy a live filter', () => {
  const last = { value: 23, bar_time: 1794614400, received_at: 1794651000, kind: 'closed' };
  const row = { source_time: null, price: null, session_ended: true,
    last_price: { value: 42, source_time: 1794651000, received_at: 1794651001 },
    cells: { '1D': { value: null, status: 'waiting', last } } };
  const snapshot = { rows: { PAY00: row } };
  const app = tracker({ rsiRows: snapshot.rows, rsiQuery: { isError: true, error: { status: 408 } } });
  const tree = app.render();
  assert.match(text(tree), /23Son kapanış · Veri hazırlanıyor/);
  assert.match(text(tree), /42Son kayıt/);
  assert.match(text(tree), /RSI isteği zaman aşımına uğradı/);
  const summary = model.summarizeRsiCells(['PAY00'], snapshot, ['1D']);
  assert.equal(summary.numeric, 1);
  assert.equal(summary.retained, 1);
  assert.equal(summary.ready, 0);
  assert.equal(summary.percent, 0);
  assert.equal(model.trackerResultRows(['PAY00'], snapshot, [{ period: '1D', min: '', max: '30' }], null, true, 1794651001).length, 0);
  assert.match(model.buildTrackerCsv(['PAY00'], 'BIST', {}, snapshot, ['1D']), /23\.00,Son kapanış/);
});
