import '../scripts/next-eslint-glob-compat.mjs';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { ESLint } from 'eslint';

const require = createRequire(import.meta.url);
const pluginPackage = require.resolve('@next/eslint-plugin-next/package.json');
const pluginRequire = createRequire(pluginPackage);
const { getRootDirs } = pluginRequire('./dist/utils/get-root-dirs.js');
const plugin = pluginRequire('./dist/index.js');
const posix = (value) => value.replaceAll('\\', '/');
const frontend = fileURLToPath(new URL('..', import.meta.url));

function fixture(t) {
  const root = mkdtempSync(path.join(tmpdir(), 'rapot-next-lint-roots-'));
  for (const directory of ['apps/admin/pages', 'apps/web/pages', 'apps/web/nested', 'empty']) {
    mkdirSync(path.join(root, directory), { recursive: true });
  }
  writeFileSync(path.join(root, 'apps/web/pages/about.js'), 'export default function About() {}');
  writeFileSync(path.join(root, 'apps/admin/pages/dashboard.js'), 'export default function Dashboard() {}');
  assert.equal(path.dirname(root), path.resolve(tmpdir()));
  assert.ok(path.basename(root).startsWith('rapot-next-lint-roots-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  return posix(root);
}

test('actual Next root discovery preserves direct, brace, glob, array and absent-root results', (t) => {
  const root = fixture(t);
  const cases = [
    [undefined, [root]],
    [`${root}/apps/web`, [`${root}/apps/web`]],
    [`${root}/apps/web/`, [`${root}/apps/web/`]],
    [`${root}/apps/*`, [`${root}/apps/admin`, `${root}/apps/web`]],
    [`${root}/apps/{admin,web}`, [`${root}/apps/admin`, `${root}/apps/web`]],
    [[`${root}/apps/web`, `${root}/apps/admin`, 17], [`${root}/apps/web`, `${root}/apps/admin`]],
    [`${root}/missing`, []],
    [`${root}/apps/web/pages/about.js`, []],
    [[], []],
    [root, [root]],
    [process.cwd(), [process.cwd().replaceAll('\\', '/')]],
    ['.', ['.']],
    ['./src', ['./src']],
    ['src/', ['src/']],
  ];
  for (const [rootDir, expected] of cases) {
    const actual = getRootDirs({ cwd: root, settings: { next: { rootDir } } });
    assert.deepEqual([...actual].sort(), [...expected].sort(), JSON.stringify(rootDir));
  }
  if (process.platform === 'win32') {
    assert.deepEqual(getRootDirs({ cwd: root, settings: { next: { rootDir: `${root}/apps/web`.replaceAll('/', '\\') } } }), [`${root}/apps/web`]);
  }
});

test('compatibility layer leaves shared tinyglobby behavior intact and rejects unreviewed calls', (t) => {
  const root = fixture(t);
  const scoped = pluginRequire('fast-glob');
  const shared = require('tinyglobby');
  assert.notEqual(pluginRequire.resolve('fast-glob'), require.resolve('tinyglobby'));
  assert.deepEqual(scoped.globSync(`${root}/apps/web`, { onlyDirectories: true }), [`${root}/apps/web`]);
  assert.ok(shared.globSync(`${root}/apps/web`, { onlyDirectories: true }).length > 1);
  assert.throws(() => scoped.globSync(root, { onlyFiles: true }), /Unreviewed/);
  assert.throws(() => scoped.globSync('', { onlyDirectories: true }), /Unreviewed/);
  assert.throws(() => scoped.globSync(root, { onlyDirectories: true, dot: true }), /Unreviewed/);
});

test('pinned plugin has exactly the reviewed fast-glob consumer and the vulnerable graph is absent', () => {
  const directory = path.join(path.dirname(pluginPackage), 'dist');
  const uses = [];
  const visit = (current) => {
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const file = path.join(current, entry.name);
      if (entry.isDirectory()) visit(file);
      else if (entry.name.endsWith('.js') && readFileSync(file, 'utf8').includes('"fast-glob"')) uses.push(file);
    }
  };
  visit(directory);
  assert.deepEqual(uses, [path.join(directory, 'utils/get-root-dirs.js')]);
  const lock = JSON.parse(readFileSync(path.join(frontend, 'package-lock.json'), 'utf8'));
  for (const name of Object.keys(lock.packages)) {
    assert.ok(!/(?:^|\/)(?:braces|micromatch)$/.test(name), name);
  }
  const alias = lock.packages['node_modules/@next/eslint-plugin-next/node_modules/fast-glob'];
  assert.equal(alias.name, 'tinyglobby');
  assert.equal(alias.version, '0.2.15');
  assert.match(alias.resolved, /^https:\/\/registry\.npmjs\.org\/tinyglobby\//);
  assert.ok(alias.integrity);
});

test('real no-html-link-for-pages rule still finds routes across direct, glob, brace and array roots', async (t) => {
  const root = fixture(t);
  for (const rootDir of [`${root}/apps/web`, `${root}/apps/*`, `${root}/apps/{admin,web}`, [`${root}/apps/admin`, `${root}/apps/web`]]) {
    const eslint = new ESLint({ cwd: root, overrideConfigFile: true, overrideConfig: [{
      files: ['**/*.jsx'],
      languageOptions: { parserOptions: { ecmaVersion: 2022, sourceType: 'module', ecmaFeatures: { jsx: true } } },
      plugins: { '@next/next': plugin },
      settings: { next: { rootDir } },
      rules: { '@next/next/no-html-link-for-pages': 'error' },
    }] });
    const [bad] = await eslint.lintText('export default function Example() { return <a href="/about">About</a>; }', { filePath: `${root}/example.jsx` });
    assert.equal(bad.errorCount, 1, JSON.stringify(rootDir));
    assert.equal(bad.messages[0].ruleId, '@next/next/no-html-link-for-pages');
    const [external] = await eslint.lintText('export default function Example() { return <a href="https://example.com/about">About</a>; }', { filePath: `${root}/example.jsx` });
    assert.equal(external.errorCount, 0);
  }
});

test('shipped flat config retains every recommended Next and Core Web Vitals rule', async () => {
  const eslint = new ESLint({ cwd: frontend });
  const config = await eslint.calculateConfigForFile(path.join(frontend, 'src/app/research/page.tsx'));
  const expected = { ...plugin.configs.recommended.rules, ...plugin.configs['core-web-vitals'].rules };
  const severity = { off: 0, warn: 1, error: 2 };
  for (const [name, value] of Object.entries(expected)) {
    const level = Array.isArray(value) ? value[0] : value;
    assert.equal(config.rules[name][0], typeof level === 'number' ? level : severity[level], name);
  }
  assert.equal(config.rules['react-hooks/rules-of-hooks'][0], 2);
});
