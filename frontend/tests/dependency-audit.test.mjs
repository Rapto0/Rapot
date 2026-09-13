import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { auditArguments, lockedPackages, runAudit, validateAudit } from '../scripts/audit-dependencies.mjs';

function lock() {
  return { lockfileVersion: 3, packages: {
    '': { name: 'fixture' },
    'node_modules/example': {
      version: '1.0.0', resolved: 'https://registry.npmjs.org/example/-/example-1.0.0.tgz',
    },
  } };
}

function report() {
  return { auditReportVersion: 2, vulnerabilities: {}, metadata: {
    vulnerabilities: { info: 0, low: 0, moderate: 0, high: 0, critical: 0, total: 0 },
    dependencies: { prod: 2, dev: 0, optional: 0, peer: 0, peerOptional: 0, total: 1 },
  } };
}

function vulnerable(severity = 'low') {
  const value = report();
  value.vulnerabilities.example = {
    name: 'example', severity, isDirect: true, range: '<=1.0.0',
    via: [{ source: 123, name: 'example', severity }], nodes: ['node_modules/example'],
  };
  value.metadata.vulnerabilities[severity] = 1;
  value.metadata.vulnerabilities.total = 1;
  return value;
}

function fixture() {
  const cwd = mkdtempSync(path.join(tmpdir(), 'rapot-npm-audit-'));
  writeFileSync(path.join(cwd, 'package-lock.json'), JSON.stringify(lock()));
  return { cwd, directory: path.join(cwd, 'reports'), npmCli: path.join(cwd, 'npm-cli.js') };
}

test('complete zero-finding report passes and every severity is counted', () => {
  const packages = lockedPackages(lock());
  assert.equal(validateAudit(report(), packages, 0).findings, 0);
  for (const severity of ['info', 'low', 'moderate', 'high', 'critical']) {
    assert.equal(validateAudit(vulnerable(severity), packages, 1).severities[severity], 1);
  }
});

test('missing JSON structure, registry errors and incomplete dependency counts fail closed', () => {
  const packages = lockedPackages(lock());
  for (const invalid of [null, [], {}, { error: { code: 'ECONNRESET' } },
    { ...report(), auditReportVersion: 1 }, { ...report(), error: {} },
    { ...report(), metadata: { vulnerabilities: report().metadata.vulnerabilities } }]) {
    assert.throws(() => validateAudit(invalid, packages, 0));
  }
  for (const mutate of [
    (value) => { value.metadata.dependencies.total = 0; },
    (value) => { delete value.metadata.dependencies.dev; },
    (value) => { value.metadata.vulnerabilities.total = '0'; },
    (value) => { value.metadata.vulnerabilities.low = 1; },
  ]) {
    const invalid = report(); mutate(invalid);
    assert.throws(() => validateAudit(invalid, packages, 0));
  }
});

test('missing findings, unknown nodes and contradictory tool exit codes are errors', () => {
  const packages = lockedPackages(lock());
  for (const mutate of [
    (value) => { value.vulnerabilities = {}; },
    (value) => { value.vulnerabilities.example.nodes = ['node_modules/unlocked']; },
    (value) => { value.vulnerabilities.example.via = []; },
    (value) => { value.vulnerabilities.example.severity = 'unknown'; },
  ]) {
    const invalid = vulnerable(); mutate(invalid);
    assert.throws(() => validateAudit(invalid, packages, 1));
  }
  assert.throws(() => validateAudit(vulnerable(), packages, 0));
  for (const code of [null, 1, 2, -1]) assert.throws(() => validateAudit(report(), packages, code));
});

test('empty, versionless, linked, private and workspace dependency scopes are rejected', () => {
  for (const mutate of [
    (value) => { delete value.packages['node_modules/example']; },
    (value) => { delete value.packages['node_modules/example'].version; },
    (value) => { value.packages['node_modules/example'].link = true; },
    (value) => { value.packages['node_modules/example'].resolved = 'file:../example'; },
    (value) => { value.packages[''].workspaces = ['packages/*']; },
  ]) {
    const invalid = lock(); mutate(invalid);
    assert.throws(() => lockedPackages(invalid));
  }
});

test('versioned packages bundled inside a declared registry dependency remain in audit scope', () => {
  const value = lock();
  value.packages['node_modules/example'].bundleDependencies = ['bundled'];
  value.packages['node_modules/example/node_modules/bundled'] = { version: '1.0.0', inBundle: true };
  assert.equal(lockedPackages(value).size, 2);
  delete value.packages['node_modules/example'].bundleDependencies;
  assert.throws(() => lockedPackages(value));
});

test('runner forces all dependency kinds, bounded runtime and preserves raw JSON and manifest', () => {
  const options = fixture();
  const raw = `${JSON.stringify(report(), null, 2)}\n`;
  let calls = 0;
  const summary = runAudit({ ...options, execute(command, args, config) {
    calls++;
    assert.equal(command, process.execPath);
    assert.deepEqual(args, [options.npmCli, ...auditArguments]);
    for (const kind of ['prod', 'dev', 'optional', 'peer']) assert.ok(args.includes(`--include=${kind}`));
    assert.ok(args.includes('--audit-level=info'));
    assert.ok(args.includes('--package-lock-only'));
    assert.ok(args.includes('--ignore-scripts'));
    assert.ok(args.includes('--offline=false'), 'Offline npm can otherwise report a false zero');
    assert.ok(!args.includes('fix'));
    assert.equal(config.shell, false);
    assert.equal(config.timeout, 180_000);
    return { status: 0, stdout: raw, stderr: '' };
  } });
  assert.equal(calls, 1);
  assert.equal(summary.status, 'passed');
  assert.equal(readFileSync(path.join(options.directory, 'npm-audit.json'), 'utf8'), raw);
  const manifest = JSON.parse(readFileSync(path.join(options.directory, 'manifest.json'), 'utf8'));
  assert.match(manifest.lock_sha256, /^[a-f0-9]{64}$/);
  assert.deepEqual(manifest.packages, ['node_modules/example']);
});

test('runner fails on findings, invalid JSON, tool exit, signal, timeout and network errors', () => {
  for (const result of [
    { status: 1, stdout: JSON.stringify(vulnerable()) },
    { status: 0, stdout: 'not-json' },
    { status: 2, stdout: JSON.stringify(report()) },
    { status: null, signal: 'SIGTERM', stdout: '' },
    { status: null, error: { code: 'ETIMEDOUT' }, stdout: '' },
    { status: 1, stdout: JSON.stringify({ error: { code: 'ECONNRESET' } }) },
  ]) {
    const options = fixture();
    const summary = runAudit({ ...options, execute: () => ({ stderr: 'preserved', ...result }) });
    assert.notEqual(summary.status, 'passed');
    assert.equal(readFileSync(path.join(options.directory, 'npm-audit.json'), 'utf8'), result.stdout);
    assert.equal(readFileSync(path.join(options.directory, 'npm-audit.stderr.log'), 'utf8'), 'preserved');
    assert.equal(JSON.parse(readFileSync(path.join(options.directory, 'summary.json'), 'utf8')).status,
      summary.status);
  }
});

test('a changed lockfile or missing npm entry point cannot produce a clean result', () => {
  const options = fixture();
  assert.equal(runAudit({ ...options, execute() {
    writeFileSync(path.join(options.cwd, 'package-lock.json'), JSON.stringify({}));
    return { status: 0, stdout: JSON.stringify(report()), stderr: '' };
  } }).status, 'error');
  assert.equal(runAudit({ ...fixture(), npmCli: '', execute() {
    assert.fail('Missing npm must not execute a command');
  } }).status, 'error');
});
