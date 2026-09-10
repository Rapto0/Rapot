import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

function loadSource(path, imports = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
      esModuleInterop: true,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {},
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const normalizers = loadSource('../src/lib/api/normalizers.ts');
const metrics = loadSource('../src/lib/metric-display.ts');
const trade = {
  id: 1, symbol: 'THYAO', market_type: 'BIST', direction: 'BUY',
  price: 100, quantity: 1, pnl: 50, status: 'CLOSED', created_at: '2026-09-10T10:00:00Z',
};
const stats = {
  total_signals: 0, total_trades: 3, open_trades: 1, closed_trades: 1,
  total_pnl: 0, win_rate: 0, scan_count: 0,
};

function tradeStats(rawStats) {
  const hooks = loadSource('../src/lib/hooks/use-trades.ts', {
    '@tanstack/react-query': { useQuery: options => ({ data: options.select(rawStats) }) },
    '@/lib/api/client': { ...normalizers, fetchStats() {}, fetchTrades() {} },
  });
  return hooks.useTradeStats().data;
}

const container = ({ children, className }) => React.createElement('div', { className }, children);
const utils = {
  cn: (...values) => values.filter(Boolean).join(' '),
  formatDate: value => value,
  getTimeAgo: value => value,
};
const sharedImports = {
  react: React,
  'react/jsx-runtime': jsxRuntime,
  'lucide-react': icons,
  '@/lib/utils': utils,
  '@/lib/metric-display': metrics,
  '@/components/ui/card': {
    Card: container, CardContent: container, CardHeader: container, CardTitle: container,
  },
  '@/components/ui/badge': { Badge: container },
};

function renderTrades(rawTrades, rawStats = undefined) {
  const page = loadSource('../src/app/trades/page.tsx', {
    ...sharedImports,
    '@/components/ui/button': { Button: container },
    '@/components/ui/page-shell': { PageShell: ({ children, description }) => React.createElement('main', null, description, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: ({ items }) => React.createElement('aside', null,
      items.map(item => React.createElement('span', { key: item.label, 'data-tone': item.tone }, `${item.label}: ${item.value}`))) },
    '@/components/ui/filter-chips': { FilterChips: () => null },
    '@/components/ui/table': Object.fromEntries([
      ['Table', 'table'], ['TableBody', 'tbody'], ['TableCell', 'td'], ['TableHead', 'th'],
      ['TableHeader', 'thead'], ['TableRow', 'tr'],
    ]),
    '@/lib/hooks/use-trades': {
      useTrades: () => ({ data: rawTrades.map(normalizers.transformTrade), isLoading: false, isError: false }),
      useTradeStats: () => ({ data: rawStats === undefined ? undefined : tradeStats(rawStats) }),
    },
    '@/components/shared/error-boundary': { EmptyState: () => null },
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

function cells(html) {
  return [...html.matchAll(/<td[^>]*>(.*?)<\/td>/gs)].map(match => match[1].replace(/<[^>]*>/g, ''));
}

test('realized PnL percentage uses entry price times quantity, including loss and measured zero', () => {
  for (const [quantity, pnl, expected] of [[1, 50, 50], [5, 50, 10], [5, -25, -5], [5, 0, 0]]) {
    const result = normalizers.transformTrade({ ...trade, quantity, pnl });
    assert.equal(result.pnl, pnl);
    assert.equal(result.pnlPercent, expected);
    assert.equal(result.currentPrice, null);
  }
});

test('missing, non-numeric and non-finite PnL is unknown rather than zero', () => {
  for (const pnl of [null, undefined, NaN, Infinity, -Infinity, '50']) {
    const result = normalizers.transformTrade({ ...trade, pnl });
    assert.equal(result.pnl, null);
    assert.equal(result.pnlPercent, null);
  }
});

test('invalid or overflowing notional never yields a fabricated percentage', () => {
  for (const invalid of [
    { quantity: 0 }, { quantity: -1 }, { quantity: null }, { quantity: NaN }, { quantity: Infinity },
    { price: 0 }, { price: -1 }, { price: null }, { price: NaN }, { price: Infinity },
    { price: Number.MAX_VALUE, quantity: 2 }, { price: Number.MIN_VALUE, quantity: 0.5 },
    { price: Number.MIN_VALUE, pnl: Number.MAX_VALUE },
  ]) {
    const result = normalizers.transformTrade({ ...trade, ...invalid });
    assert.equal(result.pnlPercent, null, JSON.stringify(invalid));
    assert.equal(result.pnl, invalid.pnl ?? trade.pnl, 'A measured realized amount remains distinct from unknown percentage');
  }
});

test('OPEN, CANCELLED and unknown status cannot claim a measured PnL or current quote', () => {
  for (const status of ['OPEN', 'CANCELLED', 'BROKEN', null, undefined]) {
    const result = normalizers.transformTrade({ ...trade, status, pnl: 123, current_price: 150 });
    assert.equal(result.pnl, null);
    assert.equal(result.pnlPercent, null);
    assert.equal(result.currentPrice, null);
    assert.equal(result.status, ['OPEN', 'CANCELLED'].includes(status) ? status : null);
  }
});

test('missing dates and unknown trade direction never become now or BUY', () => {
  for (const created_at of [null, undefined, '', 'invalid']) {
    const result = normalizers.transformTrade({ ...trade, created_at, direction: 'invalid' });
    assert.equal(result.createdAt, null);
    assert.equal(result.direction, null);
  }
});

test('stats use the explicit CLOSED count and preserve legacy unknown counts and absent metrics', () => {
  const result = tradeStats(stats);
  assert.equal(result.closed, 1, 'The third CANCELLED trade is not CLOSED');
  assert.equal(result.openPnL, null);
  assert.equal(result.totalPnL, 0);
  assert.equal(result.closedPnL, 0);
  const legacy = normalizers.transformStats({ ...stats, closed_trades: undefined });
  assert.equal(legacy.closedPositions, null);
  for (const key of ['totalPnLPercent', 'lastScanTime', 'todaySignals']) assert.equal(legacy[key], null);
  const overview = normalizers.transformOpsOverviewReadModel({ ...stats, last_scan_at: null });
  for (const key of ['closedPositions', 'totalPnLPercent', 'winRate', 'lastScanTime', 'todaySignals']) {
    assert.equal(overview[key], null);
  }
});

test('invalid aggregate fields and dates stay unknown while source zero counts remain zero', () => {
  const result = normalizers.transformStats({
    ...stats, total_pnl: Infinity, win_rate: NaN, total_trades: -1, open_trades: 1.5,
    closed_trades: null, total_signals: 0,
  });
  for (const key of ['totalPnL', 'winRate', 'totalTrades', 'openPositions', 'closedPositions']) {
    assert.equal(result[key], null);
  }
  assert.equal(result.totalSignals, 0);
  assert.equal(normalizers.transformOpsOverviewReadModel({ ...stats, last_scan_at: 'invalid' }).lastScanTime, null);
});

test('metric renderers give unknown values a neutral dash and measured zero remains visible', () => {
  for (const value of [undefined, null, NaN, Infinity, -Infinity]) {
    assert.equal(metrics.formatMetric(value), '—');
    assert.equal(metrics.formatMetricPercent(value), '—');
    assert.equal(metrics.formatTradePrice(value, 'BIST'), '—');
    assert.equal(metrics.metricTone(value), 'neutral');
    assert.equal(metrics.metricTextClass(value), 'text-muted-foreground');
  }
  assert.equal(metrics.formatMetric(0), '0,00');
  assert.equal(metrics.formatMetricPercent(0), '0,00%');
});

test('actual trades page renders quantity-adjusted PnL, loss and measured zero', () => {
  for (const [quantity, pnl, percentage] of [[1, 50, '+50,00%'], [5, 50, '+10,00%'], [5, -25, '-5,00%'], [5, 0, '+0,00%']]) {
    const result = cells(renderTrades([{ ...trade, quantity, pnl }], stats));
    assert.equal(result[4], '—', 'Current price is not copied from entry');
    assert.ok(result[6].endsWith(percentage), result[6]);
    assert.equal(result[7], 'Kapalı');
  }
});

test('actual trades page renders unknown current/PnL/date and separates cancelled or unknown status', () => {
  for (const [status, label] of [['OPEN', 'Açık'], ['CANCELLED', 'İptal'], ['invalid', 'Bilinmiyor']]) {
    const html = renderTrades([{ ...trade, status, created_at: null }]);
    const result = cells(html);
    assert.equal(result[4], '—');
    assert.equal(result[6], '——');
    assert.equal(result[7], label);
    assert.equal(result[8], '—');
    assert.ok(html.includes('Gerçekleşmiş PnL: —'));
    assert.ok(html.includes('Kapalı: —'));
    assert.ok(html.includes('döviz dönüşümü içermez'));
  }
  const zeroQuantity = cells(renderTrades([{ ...trade, quantity: 0 }]));
  assert.ok(zeroQuantity[6].endsWith('—'));
});

test('portfolio and mini portfolio show unknown aggregates and no fabricated open-position valuation', () => {
  const loaded = loadSource('../src/components/dashboard/portfolio-panel.tsx', {
    ...sharedImports,
    '@/lib/hooks': {
      useTrades: () => ({ data: [normalizers.transformTrade({ ...trade, status: 'OPEN' })] }),
      useTradeStats: () => ({ data: undefined }),
    },
  });
  for (const Component of [loaded.PortfolioPanel, loaded.MiniPortfolio]) {
    const html = renderToStaticMarkup(React.createElement(Component));
    assert.ok(html.includes('—'));
    assert.ok(!html.includes('+0,00'));
    assert.ok(!html.includes('text-profit'));
  }
  const html = renderToStaticMarkup(React.createElement(loaded.PortfolioPanel));
  assert.ok(html.includes('İşlem gönderimi bağlı değil'));
  assert.ok(!html.includes('Paper Trading Aktif'));
  assert.ok(!html.includes('Bağlı'));
  for (const button of html.matchAll(/<button([^>]*)>(.*?)<\/button>/gs)) {
    const label = button[2].replace(/<[^>]*>/g, '');
    if (['AL', 'SAT'].includes(label) || button[1].includes('Pozisyonu Kapat')) {
      assert.ok(button[1].includes('disabled'), label || 'close');
    }
  }
});

test('actual dashboard KPI consumers show unavailable overview metrics and errors as dashes', () => {
  for (const response of [
    { data: normalizers.transformOpsOverviewReadModel({ ...stats, last_scan_at: null }), isLoading: false, isError: false },
    { data: undefined, isLoading: false, isError: true },
  ]) {
    const loaded = loadSource('../src/components/dashboard/kpi-cards.tsx', {
      ...sharedImports,
      '@/lib/hooks/use-dashboard': { useDashboardKPIs: () => response },
      '@/components/ui/skeleton': { SkeletonKPICard: () => React.createElement('b', null, 'Loading') },
    });
    const html = renderToStaticMarkup(React.createElement(loaded.KPICards));
    assert.ok(html.includes('—'));
    assert.ok(!html.includes('Loading'));
    assert.ok(!html.includes('NaN'));
    assert.ok(!html.includes('0.00%'));
    assert.ok(!html.includes('₺'));
    const mini = renderToStaticMarkup(React.createElement(loaded.MiniStats));
    assert.ok(mini.includes('—'));
  }
});

test('portfolio has no executable buy, sell or close event path', () => {
  // Inspect actual component event props as well as the server-rendered disabled markup.
  const loaded = loadSource('../src/components/dashboard/portfolio-panel.tsx', {
    ...sharedImports,
    react: { ...React, useState: () => [false, () => {}], useMemo: callback => callback() },
    '@/lib/hooks': {
      useTrades: () => ({ data: [normalizers.transformTrade({ ...trade, status: 'OPEN' })] }),
      useTradeStats: () => ({ data: undefined }),
    },
  });
  const buttons = [];
  function visit(element) {
    if (!element || typeof element !== 'object') return;
    if (Array.isArray(element)) return element.forEach(visit);
    if (typeof element.type === 'function') return visit(element.type(element.props));
    if (element.type === 'button' && element.props.disabled) buttons.push(element.props);
    visit(element.props?.children);
  }
  visit(loaded.PortfolioPanel({}));
  assert.equal(buttons.length, 3, 'BUY, SELL and close are all disabled');
  for (const props of buttons) {
    assert.equal(props.onClick, undefined, 'No buy/sell/close callback can be dispatched');
  }
});

test('bot dashboard and open positions apply the shared measured-source contract', () => {
  const rawRows = [
    { ...trade, status: 'OPEN', pnl: 123 },
    { ...trade, id: 2, status: 'CANCELLED', pnl: 123 },
    { ...trade, id: 3, status: 'CLOSED', pnl: null },
  ];
  const query = {
    useQuery: options => {
      const raw = options.queryKey[0] === 'stats' ? stats : rawRows;
      return { data: options.select(raw), isLoading: false, isError: false };
    },
  };
  const bot = loadSource('../src/components/dashboard/bot-dashboard.tsx', {
    ...sharedImports,
    '@tanstack/react-query': query,
    '@/lib/api/client': { ...normalizers, fetchStats() {}, fetchTrades() {} },
    '@/lib/hooks/use-health': { useBotHealth: () => ({ state: 'unknown', lastScanTime: null }) },
  });
  const botHtml = renderToStaticMarkup(React.createElement(bot.BotDashboard));
  assert.ok(botHtml.includes('AÇIK'));
  assert.ok(botHtml.includes('İPTAL'));
  assert.ok(botHtml.includes('—'));
  assert.ok(!botHtml.includes('123'));
  const positions = loadSource('../src/components/dashboard/market-overview.tsx', {
    ...sharedImports,
    '@tanstack/react-query': query,
    '@/lib/api/client': { ...normalizers, fetchMarketOverview() {}, fetchTrades() {} },
    '@/lib/hooks/use-binance-ticker': { useBinanceTicker: () => ({}) },
    recharts: {},
  });
  const html = renderToStaticMarkup(React.createElement(positions.OpenPositions));
  assert.ok(html.includes('—'));
  assert.ok(!html.includes('123'));
  assert.ok(!html.includes('0.00%'));
});
