import assert from 'node:assert/strict';
import test from 'node:test';
import { load, hooks, nodes, text, primitives } from './view-harness.mjs';

const model = load('../src/lib/rsi-tracker.ts');
const symbols = Array.from({ length: 53 }, (_, index) => `PAY${String(index).padStart(2, '0')}`);

function tracker({ allowed = true, responses = {}, bistQuote = {}, rsiRows = {} } = {}) {
  const state = hooks();
  const queries = [], requests = [], snapshots = [], streams = [];
  const source = load('../src/components/scanner/rsi-tracker.tsx', { ...primitives,
    react: state.react,
    '@tanstack/react-query': { useQuery: options => {
      queries.push(options);
      if (options.queryKey[0] === 'rsi-tracker-values') return { data: { rows: rsiRows }, dataUpdatedAt: 0 };
      return { data: { symbols: options.queryKey[2] === 'BIST' ? symbols : ['BTCUSDT', 'ETHUSDT'] },
        refetch: () => requests.push('refresh-symbols'), ...responses[options.queryKey[2]] };
    } },
    '@/lib/api/ops-api': {
      fetchBistSymbols: signal => { requests.push(['BIST', signal]); },
      fetchCryptoSymbols: signal => { requests.push(['Kripto', signal]); },
      fetchRsiSnapshot: (...args) => { requests.push(['RSI', ...args]); },
    },
    '@/lib/hooks/use-private-market': { usePrivateMarket: () => ({ allowed, sessionKey: 'admin:100' }) },
    '@/lib/hooks/use-market-snapshot': { useMarketSnapshot: values => {
      snapshots.push(Array.from(values));
      return { data: bistQuote, dataUpdatedAt: 0, refetch: () => requests.push('refresh-quotes') };
    } },
    '@/lib/hooks/use-binance-ticker': { useBinanceTickerFeed: (values, options) => {
      streams.push({ values: Array.from(values), ...options });
      return { prices: {}, receivedAtBySymbol: {}, status: 'connecting', reconnect: () => requests.push('reconnect') };
    } },
    '@/lib/rsi-tracker': model,
  }, `\nconst window = { crypto: { randomUUID: () => '12345678-test-1234-1234-123456789abc' } };`);
  return { queries, requests, snapshots, streams, render() { state.reset(); return source.RsiTracker(); } };
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

test('active market loads only its symbols and at most 25 prices without starting RSI calls', async () => {
  const app = tracker(); const tree = app.render(); const query = app.queries.at(-2);
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
  assert.equal(app.queries.at(-1).enabled, false);
  assert.equal(nodes(tree).filter(node => node.type === 'td' && node.props.title === 'RSI takibi kapalı').length, 25 * 16);
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
  const query = app.queries.at(-2), signal = new AbortController().signal;
  assert.deepEqual(Array.from(query.queryKey), ['rsi-tracker-symbols', 'admin:100', 'Kripto']);
  await query.queryFn({ signal }); assert.deepEqual(app.requests, [['Kripto', signal]]);
});

test('only explicitly tracked symbols request RSI and candle and fresh values are distinguishable', async () => {
  const app = tracker({ rsiRows: { PAY00: { source_time: 1794651000, price: 42, cells: {
    '15m': { status: 'ready', value: 0, bar_time: 1794650400 },
    '1D': { status: 'candle', value: 71.123, bar_time: 1794614400 },
  } } } });
  let tree = app.render();
  const follow = (symbol) => nodes(tree).find(node => node.type === 'button' && node.props['aria-label'] === `${symbol} RSI takibini aç`);
  follow('PAY00').props.onClick(); tree = app.render();
  follow('PAY01').props.onClick(); tree = app.render();
  assert.equal(follow('PAY02').props.disabled, true);
  const query = app.queries.at(-1), signal = new AbortController().signal;
  assert.equal(query.enabled, true);
  await query.queryFn({ signal });
  assert.deepEqual(Array.from(app.requests[0][3]), ['PAY00', 'PAY01']);
  assert.equal(app.requests[0][4].length, 16);
  assert.equal(app.requests[0][5], signal);
  assert.match(text(tree), /0Güncel fiyatla hesaplandı/);
  assert.match(text(tree), /71,12Son mum kaydı/);
  button(tree, 'Kripto').props.onClick(); tree = app.render();
  assert.equal(app.queries.at(-1).enabled, false);
  assert.doesNotMatch(text(tree), /71,12/);
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
  for (const checkbox of nodes(tree).filter(node => node.type === 'input' && node.props.type === 'checkbox').slice(0, 15)) checkbox.props.onChange();
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
