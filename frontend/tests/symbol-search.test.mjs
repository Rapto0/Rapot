import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

function load(path, imports = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {},
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
    fetch() { assert.fail('Symbol search must not request provider data'); },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const chartRoute = load('../src/lib/chart-route.ts');

function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}

function searchHarness() {
  const states = [], navigation = [];
  let cursor = 0, focused = 0, prevented = 0;
  const hooks = {
    useState(initial) {
      const index = cursor++;
      if (!(index in states)) states[index] = initial;
      return [states[index], value => { states[index] = value; }];
    },
    useId: () => 'search-test',
    useRef: () => ({ current: { focus() { focused++; } } }),
  };
  const Search = load('../src/components/dashboard/symbol-search.tsx', {
    react: hooks,
    'react/jsx-runtime': jsxRuntime,
    'next/navigation': { useRouter: () => ({ push: url => navigation.push(url) }) },
    'lucide-react': icons,
    '@/components/ui/input': {
      Input: React.forwardRef(function TestInput(props, ref) {
        return React.createElement('input', { ...props, ref });
      }),
    },
    '@/components/ui/button': { Button: props => React.createElement('button', props) },
  }).SymbolSearch;
  const render = () => { cursor = 0; return Search(); };
  const field = name => descendants(render()).find(node => node.props.name === name);
  return {
    render, navigation, field,
    change(name, value) { field(name).props.onChange({ target: { value } }); },
    submit() { render().props.onSubmit({ preventDefault() { prevented++; } }); },
    get focused() { return focused; },
    get prevented() { return prevented; },
  };
}

test('search exposes linked labels, explicit BIST default and native form submission', () => {
  const h = searchHarness();
  const tree = h.render();
  assert.equal(tree.type, 'form');
  assert.equal(tree.props.role, 'search');
  assert.equal(tree.props['aria-label'], 'Grafik için sembol ara');
  const nodes = descendants(tree);
  for (const name of ['market', 'symbol']) {
    const field = nodes.find(node => node.props.name === name);
    assert.ok(nodes.some(node => node.type === 'label' && node.props.htmlFor === field.props.id));
  }
  assert.equal(h.field('market').props.value, 'BIST');
  assert.equal(h.field('symbol').props.onKeyDown, undefined);
  assert.equal(nodes.find(node => node.props.type === 'submit').props.onClick, undefined);
  assert.match(renderToStaticMarkup(tree), /Örn\. THYAO/);
  assert.match(renderToStaticMarkup(tree), /<option value="Kripto">Kripto<\/option>/);
  h.change('symbol', 'BTCIM');
  h.submit();
  assert.deepEqual(h.navigation, ['/chart?symbol=BTCIM&market=BIST']);
});

test('form submit normalizes the symbol while preserving the explicitly selected market', () => {
  const h = searchHarness();
  for (const [market, input, symbol] of [
    ['BIST', ' thyAo ', 'THYAO'],
    ['BIST', 'BTC', 'BTC'],
    ['BIST', 'BTCIM', 'BTCIM'],
    ['BIST', 'ETHUSDT', 'ETHUSDT'],
    ['Kripto', 'dogeusdc', 'DOGEUSDC'],
    ['Kripto', '1000satsusdt', '1000SATSUSDT'],
    ['BIST', 'NOTLISTED', 'NOTLISTED'],
    ['BIST', 'A'.repeat(32), 'A'.repeat(32)],
  ]) {
    h.change('market', market);
    h.change('symbol', input);
    h.submit();
    const url = new URL(h.navigation.at(-1), 'https://example.invalid');
    assert.equal(url.pathname, '/chart');
    assert.deepEqual([...url.searchParams], [['symbol', symbol], ['market', market]]);
    const resolved = chartRoute.resolveChartSelection(Object.fromEntries(url.searchParams));
    assert.equal(resolved.symbol, symbol, 'Search must never trigger chart-route fallback');
    assert.equal(resolved.market, market);
  }
  assert.equal(h.prevented, 8);
  assert.equal(h.navigation.length, 8);
  assert.equal(h.focused, 0);
});

test('empty or invalid symbols show a local linked error, focus the input and never navigate', () => {
  for (const market of ['BIST', 'Kripto']) {
    for (const input of ['', '  ', 'BTC/USDT', '../x', 'BTC?market=BIST', '<script>',
      'A'.repeat(33), 'SI\nSE', 'İSCTR', 'THYAO.IS', 'BTC USDT']) {
      const h = searchHarness();
      h.change('market', market);
      h.change('symbol', input);
      h.submit();
      const inputNode = h.field('symbol');
      const alert = descendants(h.render()).find(node => node.props.role === 'alert');
      assert.equal(h.navigation.length, 0);
      assert.equal(h.focused, 1);
      assert.equal(h.prevented, 1);
      assert.equal(inputNode.props['aria-invalid'], true);
      assert.ok(inputNode.props['aria-describedby'].split(' ').includes(alert.props.id));
      assert.match(alert.props.children, input.trim() ? /1–32/ : /Bir sembol yazın/);
    }
  }
});

test('editing an error clears its state and a corrected symbol can be submitted', () => {
  const h = searchHarness();
  h.change('symbol', 'BTC/USDT');
  h.submit();
  h.change('symbol', 'BTCUSDT');
  assert.equal(h.field('symbol').props['aria-invalid'], false);
  assert.equal(descendants(h.render()).some(node => node.props.role === 'alert'), false);
  h.change('market', 'Kripto');
  h.submit();
  assert.deepEqual(h.navigation, ['/chart?symbol=BTCUSDT&market=Kripto']);
});

test('changing market updates the example without guessing from or overwriting the query', () => {
  const h = searchHarness();
  h.change('symbol', 'ETH/USDT');
  h.submit();
  h.change('market', 'Kripto');
  assert.equal(h.field('symbol').props.value, 'ETH/USDT');
  assert.equal(h.field('symbol').props['aria-invalid'], false);
  assert.match(renderToStaticMarkup(h.render()), /Örn\. BTCUSDT/);
  h.change('symbol', '');
  h.submit();
  assert.match(renderToStaticMarkup(h.render()), /Bir sembol yazın\. Örneğin BTCUSDT\./);
  assert.deepEqual(h.navigation, []);
});

test('landing page uses the search component and clear heading hierarchy without a seconds claim', () => {
  const Page = load('../src/app/page.tsx', {
    react: { useState: () => [{}, () => {}], useEffect: () => {}, useMemo: callback => callback() },
    'react/jsx-runtime': jsxRuntime,
    'next/link': { default: props => React.createElement('a', props) },
    'lucide-react': icons,
    '@/components/dashboard/symbol-search': {
      SymbolSearch: () => React.createElement('form', { 'data-symbol-search': true }),
    },
    '@/lib/hooks/use-binance-ticker': { useBinanceTicker: () => ({}) },
    '@/lib/api/client': { fetchGlobalIndices() { assert.fail('Page render must not fetch'); } },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
  }).default;
  const html = renderToStaticMarkup(Page());
  assert.match(html, /<h1[^>]*>Piyasalara genel bakış<\/h1>/);
  assert.match(html, /data-symbol-search="true"/);
  assert.match(html, /<h2[^>]*>BIST<\/h2>/);
  assert.match(html, /<h3[^>]*>Apple \(AAPL\)<\/h3>/);
  assert.match(html, /<h3[^>]*>İşlemler<\/h3>/);
  assert.doesNotMatch(html, /AAPLE|Saniyelik/);
});
