import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

function load(relativePath, imports = {}, globals = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(relativePath, import.meta.url), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX,
    },
  }).outputText;
  const context = vm.createContext({
    exports: {}, ...globals,
    require(specifier) {
      assert.ok(Object.hasOwn(imports, specifier), `Unexpected import: ${specifier}`);
      return imports[specifier];
    },
    console: { log() { assert.fail('No storage contents may be logged'); }, error() { assert.fail('No browser errors may be logged'); } },
    fetch() { assert.fail('Settings cleanup must never use the network'); },
  });
  vm.runInContext(compiled, context);
  return context.exports;
}

function fakeStorage(initial = {}) {
  const data = new Map(Object.entries(initial));
  const calls = [];
  return {
    data, calls,
    getItem(key) { calls.push(['get', key]); return data.get(key) ?? null; },
    setItem(key, value) { calls.push(['set', key]); data.set(key, value); },
    removeItem(key) { calls.push(['remove', key]); data.delete(key); },
    clear() { assert.fail('Other browser preferences must never be cleared'); },
    key() { assert.fail('Only the two known legacy keys may be inspected'); },
  };
}

const { cleanupLegacyBrowserSettings } = load('../src/lib/browser-preferences.ts');
const unsafeValues = {
  telegramChatId: 'private-chat', telegramToken: 'private-telegram',
  binanceApiKey: 'private-key', binanceSecretKey: 'private-secret',
  unexpected: { accessToken: 'private-extra' },
};
const safeValues = { rsiOversold: 30, rsiOverbought: 70, hunterMinScore: 10, scanInterval: 30, notifications: false };

test('both legacy formats retain only inert numeric/boolean values; secrets and unknown fields disappear', () => {
  const storage = fakeStorage({
    'rapot.settings.v1': JSON.stringify({ ...unsafeValues, ...safeValues }),
    'rapot-settings': JSON.stringify({ state: { ...unsafeValues, ...safeValues }, version: 0, extraToken: 'private-outer' }),
    'rapot-dashboard': 'unrelated-dashboard',
    'rapot.scanner.watchlists.v2': 'unrelated-watchlists',
  });
  assert.equal(cleanupLegacyBrowserSettings(storage).status, 'complete');
  assert.deepEqual(JSON.parse(storage.data.get('rapot.settings.v1')), safeValues);
  assert.deepEqual(JSON.parse(storage.data.get('rapot-settings')), { state: safeValues, version: 0 });
  assert.equal(storage.data.get('rapot-dashboard'), 'unrelated-dashboard');
  assert.equal(storage.data.get('rapot.scanner.watchlists.v2'), 'unrelated-watchlists');
  assert.ok([...storage.data.values()].every((value) => !value.includes('private-')));
  assert.ok(storage.calls.every(([, key]) => ['rapot.settings.v1', 'rapot-settings'].includes(key)));
  storage.calls.length = 0;
  cleanupLegacyBrowserSettings(storage);
  assert.ok(storage.calls.every(([operation]) => operation === 'get'), 'Cleanup must be idempotent');
});

test('malformed JSON, null, arrays, primitive values and empty archives remove only their known keys', () => {
  for (const raw of ['broken private-secret', 'null', '[]', '["private-secret"]', '12', '"private-secret"', '{}']) {
    const storage = fakeStorage({ 'rapot.settings.v1': raw, 'rapot-settings': raw, unrelated: 'keep' });
    assert.equal(cleanupLegacyBrowserSettings(storage).status, 'complete');
    assert.deepEqual([...storage.data], [['unrelated', 'keep']]);
  }
});

test('nested objects, numeric strings, infinity and extra fields never pass the allowlist', () => {
  const storage = fakeStorage({
    'rapot.settings.v1': '{"rsiOversold":{"secret":"private"},"rsiOverbought":"70","scanInterval":1e400,"notifications":"false","hunterMinScore":12,"__proto__":{"secret":"private"}}',
    'rapot-settings': '{"state":{"scanInterval":20,"notifications":true,"unknown":"private"},"version":"private"}',
  });
  cleanupLegacyBrowserSettings(storage);
  assert.deepEqual(JSON.parse(storage.data.get('rapot.settings.v1')), { hunterMinScore: 12 });
  assert.deepEqual(JSON.parse(storage.data.get('rapot-settings')), { state: { scanInterval: 20, notifications: true }, version: 0 });
});

test('storage failures are isolated per key and never expose exception messages or claim success', () => {
  for (const operation of ['getItem', 'setItem', 'removeItem']) {
    const storage = fakeStorage({
      'rapot.settings.v1': JSON.stringify(operation === 'removeItem' ? unsafeValues : { ...unsafeValues, ...safeValues }),
      'rapot-settings': JSON.stringify({ state: unsafeValues }),
    });
    const original = storage[operation];
    storage[operation] = (key, value) => {
      if (key === 'rapot.settings.v1') throw new Error('private-sensitive-browser-error');
      return original(key, value);
    };
    const result = cleanupLegacyBrowserSettings(storage);
    assert.equal(result.status, 'blocked');
    assert.deepEqual([...result.failedKeys], ['rapot.settings.v1']);
    assert.ok(!JSON.stringify(result).includes('private-'));
    assert.ok(!storage.data.has('rapot-settings'), 'Failure of one key must not leave the other unsanitized');
  }
  const blockedWindow = {};
  Object.defineProperty(blockedWindow, 'localStorage', { get() { throw new Error('private-getter-error'); } });
  const browserModule = load('../src/lib/browser-preferences.ts', {}, { window: blockedWindow });
  const result = browserModule.cleanupLegacyBrowserSettings();
  assert.equal(result.status, 'blocked');
  assert.equal(result.failedKeys.length, 2);
  assert.ok(!JSON.stringify(result).includes('private-'));
});

test('global Providers startup cleans old settings even when the settings page is never opened', () => {
  const storage = fakeStorage({ 'rapot.settings.v1': JSON.stringify(unsafeValues), 'rapot-settings': JSON.stringify({ state: unsafeValues }) });
  const browserModule = load('../src/lib/browser-preferences.ts', {}, { window: { localStorage: storage } });
  const effects = [];
  const provider = load('../src/components/providers.tsx', {
    'react/jsx-runtime': jsxRuntime,
    react: { useEffect: (callback) => effects.push(callback), useState: React.useState },
    '@tanstack/react-query': {},
    '@/components/ui/toast': {}, '@/components/layout/sidebar-context': {},
    '@/lib/hooks/use-session': { useSession: () => null }, '@/lib/api/core': {},
    '@/components/realtime-bridge': {}, '@/lib/browser-preferences': browserModule,
  });
  provider.Providers({ children: null });
  effects.forEach((effect) => effect());
  assert.equal(storage.data.size, 0);
});

function renderSettings(cleanupResult = null) {
  const page = load('../src/app/settings/page.tsx', {
    'react/jsx-runtime': jsxRuntime,
    react: { useEffect() {}, useState: () => [cleanupResult, () => {}] },
    'next/link': { default: ({ children, ...props }) => React.createElement('a', props, children) },
    '@/components/ui/page-shell': { PageShell: ({ children, title, description }) => React.createElement('main', null,
      React.createElement('h1', null, title), React.createElement('p', null, description), children) },
    '@/lib/browser-preferences': { cleanupLegacyBrowserSettings },
  });
  return renderToStaticMarkup(React.createElement(page.default));
}

test('settings page is honest about server-managed configuration and links actual browser preferences', () => {
  const html = renderSettings({ status: 'complete', failedKeys: [] });
  assert.ok(html.includes('Bu sayfa bot ayarlarını değiştirmez'));
  assert.ok(html.includes('sunucu yapılandırmasından gelir'));
  assert.ok(html.includes('etkisiz geçmiş kayıtları'));
  assert.ok(html.includes('href="/scanner"'));
  assert.ok(!/<input|<button|role="switch"/.test(html), 'No fake controls or credential inputs');
  assert.ok(!html.includes('Kaydet'));
  assert.ok(!html.includes('role="alert"'));
  const blocked = renderSettings({ status: 'blocked', failedKeys: ['rapot-settings'] });
  assert.ok(blocked.includes('role="alert"'));
  assert.ok(blocked.includes('temizliği tamamlanamadı'));
});
