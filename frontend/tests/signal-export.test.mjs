import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

function load(path, imports = {}, globals = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {}, ...globals,
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
    fetch() { assert.fail('Export must not make a network request'); },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

const csv = load('../src/lib/signal-export.ts');
const signal = {
  id: 1, symbol: 'THYAO', marketType: 'BIST', strategy: 'HUNTER', signalType: 'AL',
  timeframe: '1d', score: '7/7', price: 123.45, specialTag: 'BELES',
  createdAt: '2026-09-10T13:00:00+03:00',
};

// Independent CSV reader: quoted delimiters, escaped quotes and embedded line breaks.
function parseCsv(text) {
  assert.equal(text[0], '\uFEFF');
  const rows = [];
  let row = [], cell = '', quoted = false;
  for (let index = 1; index < text.length; index++) {
    const char = text[index];
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { cell += '"'; index++; }
      else quoted = !quoted;
    } else if (!quoted && char === ';') {
      row.push(cell); cell = '';
    } else if (!quoted && char === '\r' && text[index + 1] === '\n') {
      row.push(cell); rows.push(row); row = []; cell = ''; index++;
    } else cell += char;
  }
  assert.equal(quoted, false);
  assert.equal(cell, '');
  assert.equal(row.length, 0);
  return rows;
}

test('CSV has Turkish headers, BOM, CRLF, visible order, translated tags and UTC dates', () => {
  const result = csv.buildSignalCsv([
    signal,
    { ...signal, id: 2, symbol: 'BTCUSDT', marketType: 'Kripto', specialTag: 'COK_UCUZ' },
  ]);
  const records = parseCsv(result);
  assert.deepEqual(records[0], ['Sembol', 'Piyasa', 'Strateji', 'Özel', 'Yön', 'Zaman Dilimi', 'Skor', 'Fiyat', 'Tarih (UTC)']);
  assert.deepEqual(records[1], ['THYAO', 'BIST', 'HUNTER', 'BELEŞ', 'AL', '1d', '7/7', '123,45', '2026-09-10T10:00:00.000Z']);
  assert.equal(records[2][0], 'BTCUSDT');
  assert.equal(records[2][3], 'ÇOK UCUZ');
  assert.deepEqual(parseCsv(csv.buildSignalCsv([])), [records[0]]);
});

test('CSV quoting preserves semicolons, commas, quotes and embedded CR/LF as one cell', () => {
  const text = 'ÇĞİÖŞÜ;"quoted",\r\nnext\nline';
  const records = parseCsv(csv.buildSignalCsv([{ ...signal, symbol: text, score: text }]));
  assert.equal(records.length, 2);
  assert.equal(records[1].length, 9);
  assert.equal(records[1][0], text);
  assert.equal(records[1][6], text);
});

test('formula-like text is protected even after whitespace/control characters; numeric negatives stay numeric', () => {
  for (const text of ['=1+1', '+4/-0', '-1+1', '@SUM(A1)', ' \t=HYPERLINK("x")', '\r\n+1', '\u0000-1', '\uFEFF@A1']) {
    const fields = parseCsv(csv.buildSignalCsv([{ ...signal, symbol: text, score: text, timeframe: text, price: -12.5 }]))[1];
    for (const index of [0, 5, 6]) assert.equal(fields[index], `'${text}`);
    assert.equal(fields[7], '-12,5');
  }
  assert.equal(parseCsv(csv.buildSignalCsv([{ ...signal, symbol: 'ABC-DEF' }]))[1][0], 'ABC-DEF');
});

test('only finite numeric values are exported as numbers; invalid dates remain empty', () => {
  for (const [price, expected] of [[0, '0'], [0.000001, '0,000001'], [1e-10, '1e-10'], [null, ''], [undefined, ''], ['12.5', ''], [NaN, ''], [Infinity, ''], [-Infinity, '']]) {
    const fields = parseCsv(csv.buildSignalCsv([{ ...signal, price, createdAt: 'invalid', specialTag: null }]))[1];
    assert.equal(fields[7], expected);
    assert.equal(fields[8], '');
    assert.equal(fields[3], '');
  }
});

function pageHarness(query = {}, initial = {}, failure = null) {
  const states = [initial.market ?? 'all', initial.strategy ?? 'all', initial.direction ?? 'all', initial.special ?? 'all', initial.search ?? '', null, null];
  let cursor = 0, buttons = [], options;
  const blobs = [], timers = [], revoked = [], links = [];
  const hooks = {
    useState(initialValue) {
      const index = cursor++;
      if (states[index] === undefined) states[index] = initialValue;
      return [states[index], value => { states[index] = value; }];
    },
    useMemo: callback => callback(),
  };
  const browser = {
    Blob,
    URL: {
      createObjectURL(blob) {
        if (failure === 'url') throw new Error('private browser error');
        blobs.push(blob);
        return `blob:export-${blobs.length}`;
      },
      revokeObjectURL(url) { revoked.push(url); },
    },
    document: {
      createElement(tag) {
        assert.equal(tag, 'a');
        const link = { clicked: false, attached: false, removed: false,
          click() { this.clicked = true; if (failure === 'click') throw new Error('private browser error'); },
          remove() { this.removed = true; },
        };
        links.push(link);
        return link;
      },
      body: { appendChild(link) { link.attached = true; } },
    },
    window: { setTimeout(callback, delay) { timers.push({ callback, delay }); return timers.length; } },
  };
  const page = load('../src/app/signals/page.tsx', {
    react: hooks, 'react/jsx-runtime': jsxRuntime, 'lucide-react': icons,
    '@/lib/signal-export': csv,
    '@/lib/hooks/use-signals': { useSignals(value) { options = value; return { data: [signal], isLoading: false, isFetching: false, isError: false, refetch() {}, ...query }; } },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), formatDate: value => value },
    '@/components/ui/badge': { Badge: ({ children }) => React.createElement('span', null, children) },
    '@/components/ui/button': { Button(props) { buttons.push(props); return React.createElement('button', { type: props.type, disabled: props.disabled, 'aria-describedby': props['aria-describedby'] }, props.children); } },
    '@/components/ui/input': { Input: props => React.createElement('input', props) },
    '@/components/ui/page-shell': { PageShell: ({ children, actions, title }) => React.createElement('main', null, React.createElement('h1', null, title), actions, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: () => null },
    '@/components/ui/filter-chips': { FilterChips: () => null },
    '@/components/ui/table': Object.fromEntries([['Table', 'table'], ['TableBody', 'tbody'], ['TableCell', 'td'], ['TableHead', 'th'], ['TableHeader', 'thead'], ['TableRow', 'tr']]),
    '@/components/shared/error-boundary': { EmptyState: ({ title }) => React.createElement('span', null, title) },
    '@/components/signals/strategy-inspector-panel': { StrategyInspectorPanel: () => null },
  }, browser);
  function render() { cursor = 0; buttons = []; return renderToStaticMarkup(React.createElement(page.default)); }
  return { render, get button() { return buttons[1]; }, get options() { return options; }, blobs, timers, revoked, links };
}

test('actual export button downloads exactly the hook-visible filtered/search rows and states the 300-record limit', async () => {
  const visible = [{ ...signal, symbol: 'THYAO' }, { ...signal, id: 7, symbol: 'THYAO.E' }];
  const page = pageHarness({ data: visible }, { market: 'BIST', strategy: 'HUNTER', direction: 'AL', special: 'BELES', search: 'THYA' });
  const html = page.render();
  assert.ok(html.includes('en fazla 300 kayıttan'));
  assert.ok(html.includes('aramaya uyan ve ekranda görünen'));
  assert.deepEqual({ ...page.options }, { marketType: 'BIST', strategy: 'HUNTER', direction: 'AL', specialTag: 'BELES', searchQuery: 'THYA', limit: 300 });
  assert.equal(page.button.disabled, false);
  assert.equal(page.button['aria-describedby'], 'signal-export-scope');
  page.button.onClick();
  assert.equal(page.blobs.length, 1);
  assert.equal(page.blobs[0].type, 'text/csv;charset=utf-8');
  const bytes = Buffer.from(await page.blobs[0].arrayBuffer());
  assert.deepEqual([...bytes.subarray(0, 3)], [239, 187, 191]);
  assert.deepEqual(parseCsv(bytes.toString('utf8')).slice(1).map(row => row[0]), visible.map(row => row.symbol));
  assert.match(page.links[0].download, /^rapot-sinyaller-\d{4}-\d{2}-\d{2}\.csv$/);
  assert.equal(page.links[0].href, 'blob:export-1');
  assert.ok(page.links[0].attached && page.links[0].clicked && page.links[0].removed);
  assert.equal(page.revoked.length, 0, 'Do not revoke before the browser consumes the click');
  assert.equal(page.timers[0].delay, 1000);
  page.timers[0].callback();
  assert.deepEqual(page.revoked, ['blob:export-1']);
});

test('empty, loading, refreshing and error states disable export and guard direct handler invocation', () => {
  for (const state of [{ data: [] }, { data: undefined }, { isLoading: true }, { isFetching: true }, { isError: true }]) {
    const page = pageHarness(state);
    page.render();
    assert.equal(page.button.disabled, true);
    page.button.onClick();
    assert.equal(page.blobs.length, 0);
    assert.equal(page.links.length, 0);
    assert.equal(page.timers.length, 0);
  }
});

test('download failures show a generic error and release any URL already created', () => {
  for (const failure of ['click', 'url']) {
    const page = pageHarness({}, {}, failure);
    page.render();
    page.button.onClick();
    const html = page.render();
    assert.ok(html.includes('role="alert"'));
    assert.ok(html.includes('CSV dosyası indirilemedi'));
    assert.ok(!html.includes('private browser error'));
    if (failure === 'click') {
      assert.equal(page.links[0].removed, true);
      page.timers[0].callback();
      assert.deepEqual(page.revoked, ['blob:export-1']);
    } else assert.equal(page.timers.length, 0);
  }
});
