import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

function load(file, imports, globals = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(file, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({
    exports: {}, ...globals,
    require(name) { assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`); return imports[name]; },
    fetch() { assert.fail('Signals page tests must never access an API or provider'); },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const csv = load('../src/lib/signal-export.ts', {});
const signal = {
  id: 1, symbol: 'THYAO', marketType: 'BIST', strategy: 'COMBO', signalType: 'AL',
  timeframe: '1D', score: '+4/-0', price: 300, createdAt: '2026-10-01T12:00:00Z', specialTag: null,
};
const second = { ...signal, id: 2, symbol: 'BTCUSDT', marketType: 'Kripto', strategy: 'HUNTER', signalType: 'SAT' };
const text = child => React.Children.toArray(child).map(node =>
  typeof node === 'string' || typeof node === 'number' ? String(node)
    : React.isValidElement(node) ? text(node.props.children) : '').join('');

function harness(initialQuery = {}) {
  const states = [], focused = [], blobs = [];
  let cursor = 0, refreshes = 0, options, buttons = [], inputs = [], kpis = [], inspector;
  let query = { data: [signal, second], isLoading: false, isFetching: false, isError: false, fetchStatus: 'idle', ...initialQuery };
  const hooks = {
    useState(initial) {
      const index = cursor++;
      if (!(index in states)) states[index] = initial;
      return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }];
    },
    useMemo: callback => callback(),
  };
  const { default: Page } = load('../src/app/signals/page.tsx', {
    react: hooks, 'react/jsx-runtime': jsxRuntime, 'lucide-react': icons,
    '@/lib/signal-export': csv,
    '@/lib/hooks/use-signals': { useSignals(value) { options = value; return { ...query, refetch() { refreshes++; } }; } },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), formatDate: value => value },
    '@/components/ui/button': { Button(props) {
      buttons.push(props);
      const dom = { ...props };
      delete dom.variant;
      delete dom.size;
      return React.createElement('button', dom);
    } },
    '@/components/ui/input': { Input(props) { inputs.push(props); return React.createElement('input', props); } },
    '@/components/ui/badge': { Badge: ({ children }) => React.createElement('span', null, children) },
    '@/components/ui/page-shell': { PageShell: ({ title, description, actions, children }) => React.createElement('main', null,
      React.createElement('h1', null, title), React.createElement('p', null, description), actions, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: ({ items }) => { kpis = items; return null; } },
    '@/components/ui/table': Object.fromEntries([['Table', 'table'], ['TableBody', 'tbody'], ['TableCell', 'td'],
      ['TableHead', 'th'], ['TableHeader', 'thead'], ['TableRow', 'tr']]),
    '@/components/shared/error-boundary': { EmptyState: ({ title, description, action }) => React.createElement('div', null,
      React.createElement('h3', null, title), React.createElement('p', null, description), action) },
    '@/components/signals/strategy-inspector-panel': { StrategyInspectorPanel(props) {
      inspector = props; return React.createElement('aside', { 'data-inspector': props.selectedSymbol });
    } },
  }, {
    Blob,
    URL: { createObjectURL(blob) { blobs.push(blob); return 'blob:synthetic'; }, revokeObjectURL() {} },
    window: { setTimeout() { return 1; } },
    document: {
      getElementById: id => ({ focus() { focused.push(id); } }),
      createElement: () => ({ click() {}, remove() {} }), body: { appendChild() {} },
    },
  });
  const h = {
    focused, blobs,
    render() { cursor = 0; buttons = []; inputs = []; kpis = []; inspector = undefined; return renderToStaticMarkup(React.createElement(Page)); },
    setQuery(next) { query = { ...query, ...next }; },
    byId(id) { h.render(); const result = buttons.find(button => button.id === id); assert.ok(result, `Missing control: ${id}`); return result; },
    button(label) { h.render(); const result = buttons.find(button => button['aria-label'] === label || text(button.children) === label); assert.ok(result, `Missing button: ${label}`); return result; },
    search(value) { h.render(); inputs[0].onChange({ target: { value } }); },
    get buttons() { return buttons; }, get input() { return inputs[0]; },
    get options() { return options; }, get kpis() { return kpis; }, get inspector() { return inspector; },
    get refreshes() { return refreshes; },
  };
  h.render();
  return h;
}

test('search has a visible associated label and help; all four filter groups expose native pressed buttons', () => {
  const h = harness();
  const html = h.render();
  assert.match(html, /<label[^>]*for="signals-search"[^>]*>Sembol ara<\/label>/);
  assert.equal(h.input.id, 'signals-search');
  assert.equal(h.input.type, 'search');
  assert.equal(h.input['aria-describedby'], 'signals-search-help');
  assert.match(html, /Arama yalnız yüklenen kayıtlarda/);
  for (const label of ['Piyasa', 'Strateji', 'Yön', 'Özel etiket']) {
    assert.ok(html.includes(`>${label}</legend>`));
  }
  assert.equal((html.match(/<fieldset/g) ?? []).length, 4);
  for (const group of ['market', 'strategy', 'direction', 'special']) {
    assert.equal(h.byId(`signal-${group}-all`)['aria-pressed'], true);
    assert.equal(h.byId(`signal-${group}-all`).type, 'button');
  }
  assert.match(html, /Etkin filtre veya sembol araması yok/);
});

test('each filter and local symbol query preserve the useSignals options and fixed 300-record limit', () => {
  const h = harness();
  h.byId('signal-market-Kripto').onClick();
  h.byId('signal-strategy-HUNTER').onClick();
  h.byId('signal-direction-SAT').onClick();
  h.byId('signal-special-FAHIS_FIYAT').onClick();
  h.search('btC');
  const html = h.render();
  assert.deepEqual({ ...h.options }, {
    marketType: 'Kripto', strategy: 'HUNTER', direction: 'SAT', specialTag: 'FAHIS_FIYAT', searchQuery: 'btC', limit: 300,
  });
  assert.match(html, /Etkin seçimler: 5/);
  assert.match(html, /Özel etiket: FAHİŞ FİYAT/);
  assert.equal(h.byId('signal-market-Kripto')['aria-pressed'], true);
  assert.equal(h.byId('signal-market-all')['aria-pressed'], false);
  assert.match(html, /Seçili piyasada en fazla 300 kayıt/);
});

test('single clear only removes its own filter and restores focus to a surviving control', () => {
  const cases = [
    ['signal-market-BIST', 'Piyasa: BIST seçimini temizle', 'marketType', 'signal-market-all'],
    ['signal-strategy-HUNTER', 'Strateji: HUNTER seçimini temizle', 'strategy', 'signal-strategy-all'],
    ['signal-direction-AL', 'Yön: AL seçimini temizle', 'direction', 'signal-direction-all'],
    ['signal-special-COK_UCUZ', 'Özel etiket: ÇOK UCUZ seçimini temizle', 'specialTag', 'signal-special-all'],
  ];
  for (const [id, label, option, focus] of cases) {
    const h = harness();
    h.byId(id).onClick();
    h.search('THY');
    h.button(label).onClick();
    h.render();
    assert.equal(h.options[option], 'all');
    assert.equal(h.options.searchQuery, 'THY');
    assert.equal(h.focused.at(-1), focus);
  }
  const h = harness();
  h.byId('signal-market-BIST').onClick();
  h.search('THY');
  h.button('Sembol: THY seçimini temizle').onClick();
  h.render();
  assert.equal(h.options.searchQuery, '');
  assert.equal(h.options.marketType, 'BIST');
  assert.equal(h.focused.at(-1), 'signals-search');
});

test('clear all resets every filter and search, including the empty-result recovery action', () => {
  for (const label of ['Tümünü temizle', 'Filtreleri ve aramayı temizle']) {
    const h = harness({ data: [] });
    for (const id of ['signal-market-BIST', 'signal-strategy-HUNTER', 'signal-direction-AL', 'signal-special-BELES']) h.byId(id).onClick();
    h.search('THY');
    h.button(label).onClick();
    const html = h.render();
    assert.deepEqual({ ...h.options }, { marketType: 'all', strategy: 'all', direction: 'all', specialTag: 'all', searchQuery: '', limit: 300 });
    assert.equal(h.focused.at(-1), 'signals-search');
    assert.match(html, /Etkin filtre veya sembol araması yok/);
    assert.doesNotMatch(html, /Seçimlere uygun sinyal bulunamadı/);
  }
});

test('loading and paused initial queries never claim zero records or successful empty data', () => {
  for (const query of [
    { data: undefined, isLoading: true, isFetching: true },
    { data: undefined, isLoading: false, isFetching: false, fetchStatus: 'paused' },
  ]) {
    const h = harness(query);
    const html = h.render();
    assert.match(html, /role="status"/);
    assert.match(html, query.fetchStatus === 'paused' ? /Bağlantı bekleniyor/ : /Sinyaller yükleniyor/);
    assert.doesNotMatch(html, /0 kayıt gösteriliyor|Gösterilecek sinyal kaydı yok|Seçimlere uygun sinyal bulunamadı|<table/);
    assert.deepEqual(Array.from(h.kpis, item => item.value), ['—', '—', '—']);
    assert.equal(h.inspector, undefined);
    assert.equal(h.button('Dışa aktar').disabled, true);
  }
});

test('initial error is distinct from empty results, provides retry and does not leak error details', () => {
  const h = harness({ data: undefined, isError: true, error: new Error('private backend diagnostics') });
  const html = h.render();
  assert.match(html, /role="alert"/);
  assert.match(html, /Sinyaller yüklenemedi/);
  assert.match(html, /kayıt olmadığı anlamına gelmez/);
  assert.doesNotMatch(html, /Gösterilecek sinyal kaydı yok|Seçimlere uygun sinyal bulunamadı|private backend/);
  assert.deepEqual(Array.from(h.kpis, item => item.value), ['—', '—', '—']);
  h.button('Tekrar dene').onClick();
  assert.equal(h.refreshes, 1);
});

test('successful unfiltered emptiness differs from server-filtered or symbol-filtered emptiness', () => {
  const h = harness({ data: [] });
  assert.match(h.render(), /Gösterilecek sinyal kaydı yok/);
  assert.match(h.render(), /BIST ve Kripto listeleri boş döndü/);
  assert.deepEqual(Array.from(h.kpis, item => item.value), ['0', '0', '0']);
  h.button('Yeniden kontrol et').onClick();
  assert.equal(h.refreshes, 1);
  h.byId('signal-market-BIST').onClick();
  assert.match(h.render(), /Seçimlere uygun sinyal bulunamadı/);
  assert.doesNotMatch(h.render(), /BIST ve Kripto listeleri boş döndü/);
  h.button('Tümünü temizle').onClick();
  h.search('NOT-FOUND');
  assert.match(h.render(), /Seçimlere uygun sinyal bulunamadı/);
  assert.match(h.render(), /yüklenen kayıtlarda/i);
});

test('background refresh retains rows and shows progress; a refresh error keeps them with a stale-data warning', () => {
  const h = harness({ isFetching: true });
  assert.match(h.render(), /2 kayıt gösteriliyor\. Liste yenileniyor/);
  assert.match(h.render(), /<table/);
  assert.equal(h.button('Yenileniyor').disabled, true);
  assert.equal(h.button('Dışa aktar').disabled, true);
  h.setQuery({ isFetching: false, isError: true });
  const html = h.render();
  assert.match(html, /2 önceki kayıt gösteriliyor/);
  assert.match(html, /Sinyaller yenilenemedi/);
  assert.match(html, /Son alınan kayıtlar gösteriliyor; güncel olmayabilir/);
  assert.match(html, /<table/);
  assert.deepEqual(Array.from(h.kpis, item => item.value), ['2', '1', '1']);
  assert.equal(h.button('Dışa aktar').disabled, true);
  h.button('Tekrar dene').onClick();
  h.setQuery({ isError: false });
  assert.doesNotMatch(h.render(), /güncel olmayabilir|role="alert"/);
  assert.equal(h.button('Dışa aktar').disabled, false);
});

test('counts and CSV explicitly refer to the visible capped list, never the database total', async () => {
  const h = harness({ data: [second] });
  const html = h.render();
  assert.match(html, /1 kayıt gösteriliyor/);
  assert.equal(h.kpis[0].label, 'Gösterilen');
  assert.match(html, /tüm kayıtların toplamı değildir/);
  assert.match(html, /ayrı ayrı en fazla 150 kayıt/);
  assert.match(html, /en fazla 300 kayıttan aramaya uyan ve ekranda görünen/);
  assert.equal(h.button('Dışa aktar')['aria-describedby'], 'signal-export-scope');
  h.button('Dışa aktar').onClick();
  const output = await h.blobs[0].text();
  assert.match(output, /BTCUSDT/);
  assert.doesNotMatch(output, /THYAO/);
});

test('row selection uses native accessible buttons and retains the inspector fallback when rows change', () => {
  const h = harness();
  assert.equal(h.inspector.selectedSymbol, 'THYAO');
  const action = h.button('BTCUSDT HUNTER SAT sinyalini incele');
  assert.equal(action.type, 'button');
  assert.equal(action.onKeyDown, undefined, 'Enter/Space activation uses native button behavior');
  action.onClick();
  h.render();
  assert.equal(h.inspector.selectedSymbol, 'BTCUSDT');
  assert.equal(h.inspector.selectedMarketType, 'Kripto');
  assert.equal(h.button('BTCUSDT HUNTER SAT sinyalini incele')['aria-pressed'], true);
  assert.equal(h.button('THYAO COMBO AL sinyalini incele')['aria-pressed'], false);
  h.setQuery({ data: [signal] });
  h.render();
  assert.equal(h.inspector.selectedSymbol, 'THYAO');
});

test('all page controls allow 44px targets and long search text can wrap without a fixed minimum width', () => {
  const h = harness();
  h.search('VERY-LONG-QUERY-'.repeat(15));
  const html = h.render();
  assert.match(h.input.className, /h-\[44px\]/);
  assert.match(h.input.className, /text-\[16px\]/);
  assert.equal(h.input.style.fontSize, 16, 'Inline font size survives the global input font shorthand');
  assert.ok(h.buttons.every(button => /min-h-\[44px\]/.test(button.className)));
  assert.match(html, /flex-wrap/);
  assert.match(html, /min-w-0 break-all/);
  assert.doesNotMatch(html, /min-w-\[220px\]/);
  assert.match(html, /tabloyu yana kaydırabilirsiniz/);
  assert.match(html, /aria-label="Sinyal kayıtları"/);
  assert.match(html, /role="region"[^>]*aria-label="Sinyal tablosu"[^>]*tabindex="0"/);
  assert.match(html, /overflow-x-auto/);
});
