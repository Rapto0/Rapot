import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

function loadSource(path, imports = {}) {
  const compiled = ts.transpileModule(readFileSync(new URL(path, import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const context = vm.createContext({ exports: {}, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(compiled, context);
  return context.exports;
}

const normalizers = loadSource('../src/lib/api/normalizers.ts');
function notificationQuery(fetchSignals, limit = 100) {
  const hooks = loadSource('../src/lib/hooks/use-signals.ts', {
    '@tanstack/react-query': { useQuery: options => options },
    '@/lib/api/client': { ...normalizers, fetchSignals },
  });
  return hooks.useSpecialNotificationSignals(limit);
}

function signal(id, strategy = 'COMBO', special_tag = 'BELES') {
  return {
    id, symbol: 'TEST', strategy, special_tag, signal_type: 'AL', market_type: 'BIST',
    timeframe: '1D', price: 100, score: '+4/-0',
    created_at: `2026-09-10T10:${String(id).padStart(2, '0')}:00Z`,
  };
}

test('notifications reject unknown raw strategies before the real normalizer defaults them to COMBO', async () => {
  const rows = [signal(1), signal(2, 'HUNTER'), signal(3, 'LEGACY'), signal(4, null)];
  assert.equal(normalizers.transformSignal(rows[2]).strategy, 'COMBO');
  const query = notificationQuery(async ({ special_tag }) => special_tag === 'BELES' ? rows : []);
  const result = await query.queryFn();
  assert.deepEqual(Array.from(result, row => row.id), [2, 1]);
});

test('two tag queries start concurrently and merge both strategies, deduplicate and sort newest first', async () => {
  const requests = [];
  const resolve = [];
  const query = notificationQuery(params => {
    requests.push({ ...params });
    return new Promise(done => resolve.push(done));
  }, 3);
  const pending = query.queryFn();
  assert.deepEqual(requests, [
    { special_tag: 'BELES', limit: 2 }, { special_tag: 'COK_UCUZ', limit: 2 },
  ]);
  resolve[0]([signal(1), signal(4, 'HUNTER'), signal(4, 'HUNTER')]);
  resolve[1]([signal(2, 'HUNTER', 'COK_UCUZ'), signal(3, 'COMBO', 'COK_UCUZ')]);
  assert.deepEqual(Array.from(await pending, row => row.id), [4, 3, 2]);
  assert.deepEqual(Array.from(query.queryKey), ['signals', 'special-notifications', 3]);
  assert.equal(query.refetchInterval, 45000);
  assert.equal(query.staleTime, 15000);
});

test('unexpected expensive or missing tags never become special notifications', async () => {
  const query = notificationQuery(async () => [
    signal(1, 'COMBO', 'PAHALI'), signal(2, 'HUNTER', 'FAHIS_FIYAT'),
    signal(3, 'COMBO', null), signal(4, 'COMBO', 'UNKNOWN'),
  ]);
  assert.equal((await query.queryFn()).length, 0);
});

test('an unavailable tag query rejects the result instead of caching an incomplete success', async () => {
  const query = notificationQuery(async ({ special_tag }) => {
    if (special_tag === 'COK_UCUZ') throw new Error('synthetic API failure');
    return [signal(1)];
  });
  await assert.rejects(query.queryFn(), /synthetic API failure/);
});
