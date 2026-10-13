import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import ts from 'typescript';

export function load(relative, imports = {}, suffix = '') {
  const code = ts.transpileModule(readFileSync(new URL(relative, import.meta.url), 'utf8') + suffix, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const context = vm.createContext({ exports: {}, URLSearchParams, require(name) {
    const values = { 'react/jsx-runtime': jsxRuntime, ...imports };
    assert.ok(Object.hasOwn(values, name), `Unexpected import: ${name}`); return values[name];
  } });
  vm.runInContext(code, context); return context.exports;
}
export function hooks() {
  const values = []; let index = 0;
  return { reset: () => { index = 0; }, react: { ...React,
    useState(initial) { const i = index++; if (!(i in values)) values[i] = typeof initial === 'function' ? initial() : initial;
      return [values[i], value => { values[i] = typeof value === 'function' ? value(values[i]) : value; }]; },
    useMemo: fn => fn(), useEffect: () => {},
  } };
}
export function nodes(element) {
  if (Array.isArray(element)) return element.flatMap(nodes);
  if (!React.isValidElement(element)) return [];
  return [element, ...nodes(element.props.children)];
}
export function text(element) {
  if (Array.isArray(element)) return element.map(text).join('');
  if (React.isValidElement(element)) return text(element.props.children);
  return typeof element === 'string' || typeof element === 'number' ? String(element) : '';
}
export const primitives = {
  'next/link': { default: 'a' },
  '@/components/ui/page-shell': { PageShell: ({ children }) => React.createElement('main', null, children) },
  '@/components/ui/button': { Button: 'button' },
  '@/components/ui/input': { Input: 'input' },
  '@/components/ui/select': { Select: 'select' },
  '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' '), getTimeAgo: () => 'az önce' },
};
