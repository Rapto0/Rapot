import { createRequire } from 'node:module';
import { readFileSync, statSync } from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const pluginPackage = require.resolve('@next/eslint-plugin-next/package.json');
const pluginRequire = createRequire(pluginPackage);
const aliasEntry = pluginRequire.resolve('fast-glob');
const aliasPackage = pluginRequire('fast-glob/package.json');
const aliasDirectory = path.dirname(pluginRequire.resolve('fast-glob/package.json'));
const lock = JSON.parse(readFileSync(new URL('../package-lock.json', import.meta.url), 'utf8'));
const consumers = Object.entries(lock.packages)
  .filter(([, metadata]) => metadata.dependencies?.['fast-glob'])
  .map(([name]) => name);

// This compatibility layer belongs only to the pinned Next lint consumer. Its sole
// fast-glob call is globSync(rootDir, { onlyDirectories: true }). Recheck that call
// and remove this layer when Next ships a fixed upstream dependency path.
if (require(pluginPackage).version !== '16.4.2'
    || aliasPackage.name !== 'tinyglobby' || aliasPackage.version !== '0.2.15'
    || !aliasEntry.startsWith(`${aliasDirectory}${path.sep}`)
    || consumers.length !== 1 || consumers[0] !== 'node_modules/@next/eslint-plugin-next') {
  throw new Error('Next ESLint glob dependency changed; review the compatibility layer');
}

const implementation = pluginRequire('fast-glob');
const marker = Symbol.for('rapot.next-eslint-root-glob-compat');
if (!implementation[marker]) {
  const globSync = (patterns, options) => {
    if (typeof patterns !== 'string' || !patterns || !options || options.onlyDirectories !== true
        || Object.keys(options).length !== 1) {
      throw new Error('Unreviewed Next ESLint glob options');
    }
    // fast-glob preserves literal spellings (./, trailing slash, filesystem root).
    // tinyglobby normalizes these and cannot glob an absolute cwd with expansion off.
    if (!implementation.isDynamicPattern(patterns)) {
      return statSync(patterns, { throwIfNoEntry: false })?.isDirectory() ? [patterns] : [];
    }
    return implementation.globSync(patterns, {
      onlyDirectories: true, expandDirectories: false, absolute: path.isAbsolute(patterns),
    })
      .map((directory) => directory === '/' || /^[A-Za-z]:\/$/.test(directory)
        ? directory : directory.replace(/\/$/, ''));
  };
  // npm may hoist this alias, but the lock must prove Next is its only consumer.
  // Replace only that alias in the in-memory CJS cache.
  // The ordinary tinyglobby module and files on disk are never modified.
  require.cache[aliasEntry].exports = Object.freeze({ globSync, [marker]: true });
}
