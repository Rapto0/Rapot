/** Offline characterization adapter. Executes the actual TS source; no indicator formulas here. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

assert.equal(process.versions.node.split('.')[0], '20', 'Use the project Node20 runtime');
assert.equal(process.argv.length, 2, 'Fixture/source paths are fixed; no arbitrary input modules');
const sourceUrl = new URL('../src/lib/indicators.ts', import.meta.url);
const fixtureUrl = new URL('../../tests/fixtures/strategy_ohlcv.json', import.meta.url);
const source = readFileSync(sourceUrl);
const fixtureBytes = readFileSync(fixtureUrl);
const fixture = JSON.parse(fixtureBytes);
assert.equal(fixture.schema, 'rapot-strategy-ohlcv-v1');
const context = vm.createContext({ exports: {}, require(name) {
  throw new Error(`Indicator module imports are forbidden: ${name}`);
} }, { codeGeneration: { strings: false, wasm: false } });
const compiled = ts.transpileModule(source.toString('utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;
vm.runInContext(compiled, context, { timeout: 1000, filename: 'actual-indicators.ts' });
const { calculateCombo, calculateHunter } = context.exports;
const profiles = {
  native: { combo: {}, hunter: {} },
  '1D': { combo: { minBuyScore: 4, minSellScore: 3 },
    hunter: { requiredDipScore: 7, requiredTopScore: 10, bopDipThreshold: -0.7, bopTopThreshold: 0.7 } },
  ME: { combo: { minBuyScore: 3, minSellScore: 3 },
    hunter: { requiredDipScore: 5, requiredTopScore: 10, bopDipThreshold: -0.7, bopTopThreshold: 0.7 } },
};
const components = {
  combo: { macd: 'macd', rsi: 'rsi', wr: 'wr', cci: 'cci' },
  hunter: { rsi: 'rsi', rsi_fast: 'rsiFast', cmo: 'cmo', bop: 'bop', macd: 'macd',
    wr: 'wr', cci: 'cci', ult: 'ultimate', bbp: 'bbPercent', roc: 'roc', dem: 'demarker',
    psy: 'psy', z: 'zscore', kpb: 'keltnerPercent', rsi2: 'rsi2' },
};
function metric(value) {
  if (value === undefined) return { state: 'not_computed', value: null };
  if (Number.isFinite(value)) return { state: 'finite', value };
  return { state: Number.isNaN(value) ? 'nan' : value > 0 ? 'positive_infinity' : 'negative_infinity', value: null };
}
function sample(row, strategy) {
  return {
    public_available: row !== undefined,
    public_signal: row?.signal ?? null,
    decisions: row ? { buy: row.signal === 'AL', sell: row.signal === 'SAT' } : null,
    scores: row ? { buy: row.buyScore ?? row.dipScore, sell: row.sellScore ?? row.topScore } : null,
    components: Object.fromEntries(Object.entries(components[strategy])
      .map(([key, field]) => [key, metric(row?.details[field])])),
  };
}
const rows = [];
const seedObservations = {};
let causalComparisons = 0;
for (const testCase of fixture.cases) {
  assert.equal(testCase.candles.length, 80);
  const original = JSON.stringify(testCase.candles);
  const ema20 = context.ema(testCase.candles.map(candle => candle.close), 20);
  seedObservations[testCase.id] = Object.fromEntries([0, 1, 12, 19, 20, 25, 79]
    .map(index => [index, metric(ema20[index])]));
  for (const [profile, parameters] of Object.entries(profiles)) {
    for (const [strategy, calculate] of [['combo', calculateCombo], ['hunter', calculateHunter]]) {
      const full = calculate(testCase.candles, parameters[strategy]);
      for (const prefix of fixture.prefixes) {
        const output = calculate(testCase.candles.slice(0, prefix), parameters[strategy]);
        const last = sample(output.at(-1), strategy);
        if (output.length) {
          assert.equal(output.length, prefix);
          assert.deepEqual(last, sample(full[prefix - 1], strategy), 'Future bars changed an earlier TS observation');
          causalComparisons++;
        }
        rows.push({ case: testCase.id, prefix, profile, strategy, ...last });
      }
    }
  }
  assert.equal(JSON.stringify(testCase.candles), original, 'Indicator calculation mutated input');
}
// Match canonical Git text across Windows autocrlf and Linux checkouts.
const sha256 = bytes => createHash('sha256').update(bytes.toString('utf8').replace(/\r\n/g, '\n')).digest('hex');
process.stdout.write(JSON.stringify({
  schema: 'rapot-ts-strategy-export-v1',
  hash_normalization: 'UTF-8 text with CRLF normalized to LF before SHA256',
  node: process.versions.node, typescript: ts.version,
  source_sha256: sha256(source), fixture_sha256: sha256(fixtureBytes),
  package_lock_sha256: sha256(readFileSync(new URL('../package-lock.json', import.meta.url))),
  profiles, prefix_causality_comparisons: causalComparisons,
  ema20_seed_observations: seedObservations, rows,
}));
