import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { clearCaches, parseForESLint } from '@typescript-eslint/parser';

const require = createRequire(import.meta.url);
const consumerRequire = createRequire(require.resolve('@typescript-eslint/typescript-estree/package.json'));
const { minimatch } = consumerRequire('minimatch');

test('patched minimatch keeps the exact typescript-estree CommonJS matching contract', () => {
  const packageInfo = consumerRequire('minimatch/package.json');
  assert.equal(packageInfo.version, '11.0.1');
  assert.equal(packageInfo.engines.node, '18 || 20 || >=22');
  const source = readFileSync(consumerRequire.resolve('./dist/useProgramFromProjectService.js'), 'utf8');
  assert.match(source, /minimatch_1\.minimatch\)\(filePath, pattern, \{ dot: true \}\)/);
  const cases = [
    ['config.ts', '*.ts', true],
    ['.config.ts', '*.ts', true],
    ['config.js', '*.ts', false],
    ['config.ts', '{config,build}.ts', true],
    ['build.ts', '{config,build}.ts', true],
    ['other.ts', '{config,build}.ts', false],
    ['scripts/build.ts', 'scripts/*.ts', true],
    ['scripts/nested/build.ts', 'scripts/*.ts', false],
  ];
  for (const [file, pattern, expected] of cases) {
    assert.equal(minimatch(file, pattern, { dot: true }), expected, `${file} / ${pattern}`);
  }
  // ESLint's separate minimatch v3 consumers retain their callable API.
  assert.equal(typeof require('minimatch'), 'function');
});

test('real parser project service accepts configured default-project matches and rejects outsiders', (t) => {
  const root = mkdtempSync(path.join(tmpdir(), 'rapot-ts-eslint-minimatch-'));
  assert.equal(path.dirname(root), path.resolve(tmpdir()));
  assert.ok(path.basename(root).startsWith('rapot-ts-eslint-minimatch-'));
  t.after(() => { clearCaches(); rmSync(root, { recursive: true, force: true }); });
  mkdirSync(path.join(root, 'src'));
  writeFileSync(path.join(root, 'tsconfig.json'), JSON.stringify({ compilerOptions: { strict: true }, include: ['src/*.ts'] }));
  writeFileSync(path.join(root, 'src', 'included.ts'), 'export const included = 1;');
  const input = 'export const value: number = 1;';
  for (const file of ['config.ts', '.config.ts', 'build.ts', 'outsider.ts']) writeFileSync(path.join(root, file), input);
  for (const [file, pattern] of [['config.ts', '*.ts'], ['.config.ts', '*.ts'], ['build.ts', '{config,build}.ts']]) {
    clearCaches();
    const result = parseForESLint(input, {
      filePath: path.join(root, file), tsconfigRootDir: root,
      projectService: { allowDefaultProject: [pattern] },
    });
    assert.equal(result.ast.type, 'Program');
    assert.ok(result.services.program, `${file} should have project type information`);
  }
  clearCaches();
  assert.throws(() => parseForESLint(input, {
    filePath: path.join(root, 'outsider.ts'), tsconfigRootDir: root,
    projectService: { allowDefaultProject: ['{config,build}.ts'] },
  }), /not found by the project service|allowDefaultProject/);
});
