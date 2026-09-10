import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function loadTsx(relativePath, imports) {
  const compiled = ts.transpileModule(readFileSync(new URL(relativePath, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {},
    require(specifier) {
      assert.ok(Object.hasOwn(imports, specifier), `Unexpected import: ${specifier}`);
      return imports[specifier];
    },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

function renderHistory(scans) {
  const status = loadTsx('../src/components/scanner/scan-status.tsx', { 'react/jsx-runtime': jsxRuntime });
  const page = loadTsx('../src/app/health/page.tsx', {
    react: React,
    'react/jsx-runtime': jsxRuntime,
    '@tanstack/react-query': {
      useQuery: ({ queryKey }) => ({
        data: queryKey[0] === 'scanHistory' ? scans : [],
        isLoading: false,
        isError: false,
      }),
    },
    '@/lib/api/client': {},
    '@/lib/hooks/use-health': { useBotHealth: () => ({ isRunning: true, scanCount: scans.length }) },
    '@/lib/utils': { cn: (...classes) => classes.filter(Boolean).join(' ') },
    '@/components/ui/page-shell': { PageShell: ({ children }) => React.createElement('main', null, children) },
    '@/components/ui/kpi-ribbon': { KpiRibbon: () => null },
    '@/components/ui/button': { Button: 'button' },
    '@/components/scanner/scan-status': status,
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

const scan = {
  id: 1, scan_type: 'BIST', mode: 'sync', symbols_scanned: 25,
  signals_found: 3, errors_count: 0, duration_seconds: 1.2,
  created_at: '2026-09-10T10:00:00+00:00',
};

test('incomplete scan history displays its outcome even when signals were saved', () => {
  const html = renderHistory([
    { ...scan, id: 1, status: 'failed', errors_count: 2 },
    { ...scan, id: 2, status: 'partial', errors_count: 1 },
    { ...scan, id: 3, status: 'cancelled', errors_count: 0 },
  ]);
  for (const label of ['Başarısız', 'Kısmen tamamlandı', 'İptal edildi', '2 hata', '1 hata', 'yeni sinyal']) {
    assert.ok(html.includes(label), label);
  }
  assert.ok(!html.includes('text-profit'), 'Saved signals must not imply scan success');
});

test('legacy and missing outcomes remain unknown instead of implying a successful zero-error scan', () => {
  for (const status of ['unknown', undefined]) {
    const html = renderHistory([{ ...scan, status, mode: 'unknown', errors_count: null }]);
    assert.ok(html.includes('Sonuç bilinmiyor'));
    assert.ok(html.includes('Hata sayısı bilinmiyor'));
    assert.ok(!html.includes('0 hata'));
    assert.ok(!html.includes('text-profit'));
    assert.ok(!html.includes('yeni sinyal'));
  }
});

test('successful zero-signal scan is a completed scan, not a failed or missing result', () => {
  const html = renderHistory([{ ...scan, status: 'success', signals_found: 0 }]);
  assert.ok(html.includes('Tamamlandı'));
  assert.ok(html.includes('0 hata'));
  assert.ok(html.includes('yeni sinyal'));
  assert.ok(!html.includes('Sonuç bilinmiyor'));
});
