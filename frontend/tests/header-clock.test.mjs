import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import * as icons from 'lucide-react';
import ts from 'typescript';

const compiled = ts.transpileModule(
  readFileSync(new URL('../src/components/layout/header.tsx', import.meta.url), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  },
).outputText;

function loadHeader(hooks, globals) {
  const imports = {
    react: hooks, 'react/jsx-runtime': jsxRuntime, 'lucide-react': icons,
    'next/link': { default: ({ children, ...props }) => React.createElement('a', props, children) },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
    '@/lib/hooks/use-signals': { useSpecialNotificationSignals: () => ({ data: undefined }) },
    '@/lib/hooks/use-health': { useBotHealth: () => ({ apiState: 'loading' }) },
    '@/components/auth/session-controls': { SessionControls: () => null },
  };
  const context = vm.createContext({ exports: {}, ...globals, require(name) {
    assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
    return imports[name];
  } });
  vm.runInContext(compiled, context);
  return context.exports.Header;
}

const clockText = html => html.match(/<div class="mono-numbers text-xs text-muted-foreground">(.*?)<\/div>/s)?.[1]
  .replace(/<[^>]+>/g, '');
const render = Header => renderToStaticMarkup(React.createElement(Header));

test('real Header server and first client render share placeholders across clock and timezone differences', () => {
  function renderAt(timestamp, timeZone, client) {
    class Clock extends Date {
      constructor(...args) { super(...(args.length ? args : [timestamp])); }
      toLocaleDateString(locale, options) { return super.toLocaleDateString(locale, { ...options, timeZone }); }
      toLocaleTimeString(locale, options) { return super.toLocaleTimeString(locale, { ...options, timeZone }); }
    }
    return render(loadHeader(React, {
      Date: Clock,
      ...(client ? { window: { localStorage: { getItem: () => null } } } : {}),
    }));
  }
  // Model UTC SSR and a Turkish browser arriving later on the next local calendar day.
  const server = renderAt('2026-09-10T20:59:59Z', 'UTC', false);
  const client = renderAt('2026-09-10T21:00:02Z', 'Europe/Istanbul', true);
  assert.equal(clockText(server), '--|--');
  assert.equal(clockText(client), '--|--');
  assert.equal(server, client);
});

test('mounted Header initializes both date/time immediately, ticks each second and clears its timer', () => {
  const slots = [];
  let position = 0;
  let effects = [];
  let stateUpdates = 0;
  let now = '2026-09-10T20:59:59Z';
  const timers = new Map();
  const listeners = new Map();
  const memo = (factory, deps) => {
    const index = position++;
    if (!slots[index] || deps.some((value, i) => !Object.is(value, slots[index].deps[i]))) {
      slots[index] = { value: factory(), deps };
    }
    return slots[index].value;
  };
  const hooks = {
    ...React,
    useState(initial) {
      const index = position++;
      if (!slots[index]) slots[index] = { value: typeof initial === 'function' ? initial() : initial };
      return [slots[index].value, next => {
        stateUpdates++;
        slots[index].value = typeof next === 'function' ? next(slots[index].value) : next;
      }];
    },
    useMemo: memo,
    useRef: initial => memo(() => ({ current: initial }), []),
    useEffect(effect, deps) {
      const index = position++;
      if (!slots[index] || deps.some((value, i) => !Object.is(value, slots[index].deps[i]))) {
        slots[index] = { deps };
        effects.push(() => { slots[index].cleanup = effect(); });
      }
    },
  };
  class Clock extends Date {
    constructor(...args) { super(...(args.length ? args : [now])); }
  }
  const Header = loadHeader(hooks, {
    Date: Clock, window: { localStorage: { getItem: () => null } },
    document: {
      addEventListener: (name, callback) => listeners.set(name, callback),
      removeEventListener: name => listeners.delete(name),
    },
    setInterval: (callback, delay) => { timers.set(1, { callback, delay }); return 1; },
    clearInterval: id => timers.delete(id),
  });
  const rerender = () => { position = 0; return render(Header); };
  assert.equal(clockText(rerender()), '--|--');
  effects.forEach(effect => effect());
  effects = [];
  function expectedClock() {
    const date = new Date(now);
    return `${date.toLocaleDateString('tr-TR', { day: '2-digit', month: 'short', year: 'numeric' })}|${
      date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
  }
  assert.equal(clockText(rerender()), expectedClock());
  assert.equal(timers.size, 1);
  assert.equal(timers.get(1).delay, 1_000);
  now = '2026-09-11T00:00:03Z';
  timers.get(1).callback();
  assert.equal(clockText(rerender()), expectedClock());
  const updates = stateUpdates;
  slots.forEach(slot => slot.cleanup?.());
  assert.equal(timers.size, 0);
  assert.equal(listeners.size, 0);
  for (const { callback } of timers.values()) callback();
  assert.equal(stateUpdates, updates);
});
