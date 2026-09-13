import { createHash } from 'node:crypto';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const severities = ['info', 'low', 'moderate', 'high', 'critical'];
const dependencyKinds = ['prod', 'dev', 'optional', 'peer', 'peerOptional', 'total'];
export const auditArguments = Object.freeze([
  'audit', '--package-lock-only', '--ignore-scripts', '--json', '--audit-level=info',
  '--include=prod', '--include=dev', '--include=optional', '--include=peer',
  '--workspaces=false', '--offline=false', '--registry=https://registry.npmjs.org/',
]);

function object(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function count(value) {
  return Number.isSafeInteger(value) && value >= 0;
}

export function lockedPackages(lock) {
  if (!object(lock) || lock.lockfileVersion !== 3 || !object(lock.packages)
      || !object(lock.packages['']) || lock.packages[''].workspaces) {
    throw new Error('Expected a complete, non-workspace npm v3 lockfile');
  }
  const packages = Object.entries(lock.packages).filter(([name]) => name !== '');
  if (!packages.length) throw new Error('The dependency audit scope is empty');
  for (const [name, entry] of packages) {
    const parentIndex = name.lastIndexOf('/node_modules/');
    const parent = parentIndex < 0 ? undefined : lock.packages[name.slice(0, parentIndex)];
    const bundledName = name.slice(parentIndex + '/node_modules/'.length);
    const bundled = object(entry) && entry.inBundle === true && entry.resolved === undefined
      && Array.isArray(parent?.bundleDependencies) && parent.bundleDependencies.includes(bundledName);
    const registry = object(entry) && typeof entry.resolved === 'string'
      && entry.resolved.startsWith('https://registry.npmjs.org/');
    if (!name.startsWith('node_modules/') || !object(entry) || entry.link
        || typeof entry.version !== 'string' || !entry.version
        || (!registry && !bundled)) {
      throw new Error('Unsupported or incomplete locked package; audit coverage is unknown');
    }
  }
  return new Set(packages.map(([name]) => name));
}

export function validateAudit(report, packages, exitCode) {
  if (!object(report) || Object.hasOwn(report, 'error') || report.auditReportVersion !== 2
      || !object(report.vulnerabilities) || !object(report.metadata)
      || !object(report.metadata.vulnerabilities) || !object(report.metadata.dependencies)) {
    throw new Error('Invalid npm audit report or registry/tool error');
  }
  const counts = report.metadata.vulnerabilities;
  const dependencies = report.metadata.dependencies;
  if (![...severities, 'total'].every((key) => count(counts[key]))
      || !dependencyKinds.every((key) => count(dependencies[key]))
      || dependencies.total !== packages.size) {
    throw new Error('Missing audit counts or dependency coverage differs from the lockfile');
  }
  const actual = Object.fromEntries(severities.map((severity) => [severity, 0]));
  for (const [name, finding] of Object.entries(report.vulnerabilities)) {
    if (!object(finding) || finding.name !== name || !severities.includes(finding.severity)
        || typeof finding.isDirect !== 'boolean' || typeof finding.range !== 'string'
        || !Array.isArray(finding.via) || finding.via.length === 0
        || !Array.isArray(finding.nodes) || finding.nodes.length === 0
        || !finding.nodes.every((node) => typeof node === 'string' && packages.has(node))) {
      throw new Error('Invalid npm vulnerability or affected package outside the lockfile');
    }
    actual[finding.severity]++;
  }
  const total = Object.keys(report.vulnerabilities).length;
  if (counts.total !== total || severities.some((severity) => counts[severity] !== actual[severity])) {
    throw new Error('Vulnerability counts disagree with the report findings');
  }
  if (exitCode !== (total ? 1 : 0)) {
    throw new Error('npm audit exit code disagrees with its validated report');
  }
  return { packages: packages.size, findings: total, severities: actual };
}

export function runAudit({
  cwd, directory, npmCli = process.env.npm_execpath, execute = spawnSync,
}) {
  mkdirSync(directory, { recursive: true });
  const output = (name, text) => writeFileSync(path.join(directory, name), text, 'utf8');
  // Clear the per-run outputs first, so failure never leaves an earlier clean report.
  output('npm-audit.json', '');
  output('npm-audit.stderr.log', '');
  const summary = { status: 'error', scope: 'all locked prod/dev/optional/peer dependencies' };
  try {
    const lockBytes = readFileSync(path.join(cwd, 'package-lock.json'));
    const packages = lockedPackages(JSON.parse(lockBytes.toString('utf8')));
    output('manifest.json', `${JSON.stringify({
      lock_sha256: createHash('sha256').update(lockBytes).digest('hex'),
      packages: [...packages].sort(), arguments: auditArguments,
    }, null, 2)}\n`);
    if (typeof npmCli !== 'string' || path.basename(npmCli) !== 'npm-cli.js') {
      throw new Error('Run this check through npm run audit:dependencies with the selected npm');
    }
    const result = execute(process.execPath, [npmCli, ...auditArguments], {
      cwd, encoding: 'utf8', shell: false, timeout: 180_000, maxBuffer: 16 * 1024 * 1024,
    });
    output('npm-audit.json', result.stdout ?? '');
    output('npm-audit.stderr.log', result.stderr ?? '');
    if (result.error || result.signal || !Number.isInteger(result.status)) {
      throw new Error('npm audit could not complete; inspect the preserved tool output');
    }
    if (!readFileSync(path.join(cwd, 'package-lock.json')).equals(lockBytes)) {
      throw new Error('The lockfile changed during the audit');
    }
    Object.assign(summary, validateAudit(JSON.parse(result.stdout), packages, result.status));
    summary.status = summary.findings ? 'findings' : 'passed';
  } catch (error) {
    summary.error = error instanceof Error ? error.message : 'Unknown dependency audit failure';
  }
  output('summary.json', `${JSON.stringify(summary, null, 2)}\n`);
  return summary;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const cwd = fileURLToPath(new URL('..', import.meta.url));
  const directory = process.env.NPM_AUDIT_REPORT_DIR
    ? path.resolve(process.env.NPM_AUDIT_REPORT_DIR)
    : path.resolve(cwd, '../security-reports/npm');
  const summary = runAudit({ cwd, directory });
  console.log(JSON.stringify(summary));
  if (summary.status !== 'passed') process.exitCode = 1;
}
