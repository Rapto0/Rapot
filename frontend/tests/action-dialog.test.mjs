import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import * as React from 'react';
import * as jsxRuntime from 'react/jsx-runtime';
import { renderToStaticMarkup } from 'react-dom/server';
import ts from 'typescript';

const compiled = ts.transpileModule(
  readFileSync(new URL('../src/components/ui/action-dialog.tsx', import.meta.url), 'utf8'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } },
).outputText;

function load(hooks, globals = {}) {
  const imports = {
    react: hooks,
    'react/jsx-runtime': jsxRuntime,
    'lucide-react': { AlertTriangle: () => null },
    '@/components/ui/button': { Button: 'button' },
    '@/components/ui/input': { Input: 'input' },
    '@/lib/utils': { cn: (...values) => values.filter(Boolean).join(' ') },
  };
  const context = vm.createContext({
    exports: {}, ...globals,
    require(name) {
      assert.ok(Object.hasOwn(imports, name), `Unexpected import: ${name}`);
      return imports[name];
    },
  });
  vm.runInContext(compiled, context);
  return context.exports.ActionDialog;
}

function descendants(element) {
  if (!React.isValidElement(element)) return [];
  return [element, ...React.Children.toArray(element.props.children).flatMap(descendants)];
}

function event() {
  return { prevented: 0, preventDefault() { this.prevented++; } };
}

function harness(initial = {}) {
  const slots = [];
  const document = { activeElement: null };
  let cursor = 0, effects = [], tree, props;
  const calls = { confirm: 0, cancel: 0, values: [] };
  class Element {
    constructor(name) { this.name = name; this.isConnected = true; this.focusCount = 0; }
    focus() { this.focusCount++; document.activeElement = this; }
  }
  const trigger = new Element('trigger');
  document.activeElement = trigger;
  const controls = { input: new Element('input'), cancel: new Element('cancel'), submit: new Element('submit') };
  const dialog = {
    open: false, shows: 0, closes: 0, ownerDocument: document,
    showModal() { assert.equal(this.open, false); this.open = true; this.shows++; },
    close() { assert.equal(this.open, true); this.open = false; this.closes++; },
    querySelector(selector) {
      return this.querySelectorAll(selector)[0] ?? null;
    },
    querySelectorAll(selector) {
      assert.equal(selector, 'input:not(:disabled), button:not(:disabled)');
      return descendants(tree).filter(node => ['input', 'button'].includes(node.type) && !node.props.disabled)
        .map(node => node.type === 'input' ? controls.input : controls[node.props.type === 'submit' ? 'submit' : 'cancel']);
    },
  };
  const hooks = {
    useRef(value) { const index = cursor++; return slots[index] ??= { current: value }; },
    useId() { cursor++; return 'dialog-test'; },
    useEffect(effect, deps) {
      const index = cursor++;
      const previous = slots[index];
      if (!previous || deps.some((value, i) => !Object.is(value, previous.deps[i]))) {
        slots[index] = { deps, effect, cleanup: previous?.cleanup };
        effects.push(() => { previous?.cleanup?.(); slots[index].cleanup = effect(); });
      }
    },
  };
  const Dialog = load(hooks, { document, HTMLElement: Element });
  props = {
    open: false, title: 'Filtreyi düzenle', description: 'Bir değer girin.', mode: 'prompt', value: '',
    onConfirm() { calls.confirm++; }, onCancel() { calls.cancel++; }, onValueChange(value) { calls.values.push(value); },
    ...initial,
  };
  const render = (patch = {}) => {
    props = { ...props, ...patch };
    cursor = 0;
    tree = Dialog(props);
    // React attaches host refs before running passive effects.
    slots[0].current = tree ? dialog : null;
    const scheduled = effects;
    effects = [];
    scheduled.forEach(effect => effect());
    return tree;
  };
  return {
    render, calls, document, dialog, controls, trigger,
    get tree() { return tree; },
    node(type) { return descendants(tree).find(node => node.type === type); },
    button(type) { return descendants(tree).find(node => node.type === 'button' && node.props.type === type); },
    replayEffects() {
      for (const slot of slots) {
        if (slot?.effect) { slot.cleanup?.(); slot.cleanup = slot.effect(); }
      }
    },
    unmount() { for (const slot of slots) slot?.cleanup?.(); slots[0].current = null; },
  };
}

test('closed dialogs render nothing and never open a modal or move focus', () => {
  const h = harness();
  assert.equal(h.render(), null);
  assert.equal(h.dialog.shows, 0);
  assert.equal(h.document.activeElement, h.trigger);
  assert.equal(h.trigger.focusCount, 0);
  h.unmount();
  assert.equal(h.dialog.closes, 0);
});

test('native modal and prompt share a unique accessible title and description', () => {
  const Dialog = load(React);
  const props = { open: true, title: 'Yeni liste', description: 'Liste adını yazın.', mode: 'prompt', onCancel() {}, onConfirm() {} };
  const html = renderToStaticMarkup(React.createElement(React.Fragment, null,
    React.createElement(Dialog, props), React.createElement(Dialog, props)));
  const labelledBy = [...html.matchAll(/<dialog[^>]*aria-labelledby="([^"]+)"/g)].map(match => match[1]);
  assert.equal(new Set(labelledBy).size, 2, 'Separate dialog instances must not share label ids');
  for (const id of labelledBy) {
    assert.ok(html.includes(`<h2 id="${id}"`));
    assert.ok(html.includes(`aria-labelledby="${id}"`));
  }
  const h = harness();
  const tree = h.render({ open: true });
  assert.equal(tree.type, 'dialog');
  assert.equal(tree.props.open, undefined, 'The open attribute would show a non-modal dialog');
  assert.equal(h.dialog.shows, 1, 'showModal activates the native inert background and focus boundary');
  assert.equal(h.node('input').props['aria-labelledby'], tree.props['aria-labelledby']);
  assert.equal(h.node('input').props['aria-describedby'], tree.props['aria-describedby']);
  assert.equal(h.document.activeElement, h.controls.input);
  h.render({ description: undefined });
  assert.equal(h.tree.props['aria-describedby'], undefined);
  assert.equal(h.node('input').props['aria-describedby'], undefined);
});

test('confirmation initially focuses cancel, and controlled updates do not steal focus', () => {
  const h = harness({ mode: 'confirm', variant: 'danger' });
  h.render({ open: true });
  assert.equal(h.node('input'), undefined);
  assert.equal(h.document.activeElement, h.controls.cancel);
  h.controls.submit.focus();
  h.render({ title: 'Liste silinecek', onCancel() { h.calls.cancel++; } });
  assert.equal(h.dialog.shows, 1);
  assert.equal(h.dialog.closes, 0);
  assert.equal(h.document.activeElement, h.controls.submit);
  assert.equal(h.button('submit').props.variant, 'destructive');
});

test('native cancel requests one controlled dismissal without silently closing', () => {
  const h = harness();
  h.render({ open: true });
  const escape = event();
  h.tree.props.onCancel(escape);
  assert.equal(escape.prevented, 1);
  assert.equal(h.calls.cancel, 1);
  assert.equal(h.dialog.open, true, 'The owner closes the controlled dialog');
  h.render({ open: false });
  assert.equal(h.dialog.closes, 1);
  assert.equal(h.calls.cancel, 1, 'Cleanup must not deliver another cancellation');
  assert.equal(h.document.activeElement, h.trigger);
});

test('prompt uses native form submission once and retains the controlled value contract', () => {
  const h = harness();
  h.render({ open: true, value: '>=7' });
  const input = h.node('input');
  assert.equal(input.props.value, '>=7');
  assert.equal(input.props.style.fontSize, 16, 'Avoid inherited 13px input text and mobile zoom');
  assert.ok(input.props.className.includes('h-[44px]'), 'Touch size must not depend on the 13px root rem');
  assert.ok(input.props.className.includes('text-foreground'), 'text-base is a background-color token here');
  for (const type of ['button', 'submit']) assert.ok(h.button(type).props.className.includes('min-h-[44px]'));
  assert.equal(input.props.onKeyDown, undefined, 'Enter is handled by the form, not a second key handler');
  assert.equal(h.button('submit').props.onClick, undefined);
  input.props.onChange({ target: { value: '20..40' } });
  assert.deepEqual(h.calls.values, ['20..40']);
  assert.equal(h.node('input').props.value, '>=7', 'Only the parent updates a controlled value');
  const submit = event();
  h.node('form').props.onSubmit(submit);
  assert.equal(submit.prevented, 1);
  assert.equal(h.calls.confirm, 1);
  h.button('button').props.onClick();
  assert.equal(h.calls.cancel, 1);
  assert.equal(h.calls.confirm, 1);
});

test('pending work blocks cancellation and confirmation including native Escape and submit', () => {
  const h = harness();
  h.render({ open: true, pending: true });
  assert.equal(h.tree.props['aria-busy'], true);
  for (const node of descendants(h.tree).filter(node => ['input', 'button'].includes(node.type))) {
    assert.equal(node.props.disabled, true);
  }
  const escape = event(), submit = event();
  h.tree.props.onCancel(escape);
  h.node('form').props.onSubmit(submit);
  h.button('button').props.onClick();
  assert.equal(escape.prevented, 1);
  assert.equal(submit.prevented, 1);
  assert.equal(h.calls.confirm, 0);
  assert.equal(h.calls.cancel, 0);
  assert.equal(h.dialog.open, true);
  h.render({ pending: false });
  h.node('form').props.onSubmit(event());
  assert.equal(h.calls.confirm, 1);
});

test('unmount closes the modal and restores only a still-connected trigger', () => {
  for (const isConnected of [true, false]) {
    const h = harness();
    h.render({ open: true });
    h.trigger.isConnected = isConnected;
    h.unmount();
    assert.equal(h.dialog.open, false);
    assert.equal(h.dialog.closes, 1);
    assert.equal(h.trigger.focusCount, isConnected ? 1 : 0);
    assert.equal(h.calls.cancel, 0);
  }
});

test('Tab wraps only at enabled control boundaries instead of escaping into browser chrome', () => {
  for (const mode of ['prompt', 'confirm']) {
    const h = harness({ mode });
    h.render({ open: true });
    const first = mode === 'prompt' ? h.controls.input : h.controls.cancel;
    const send = (shiftKey, key = 'Tab') => {
      const e = { ...event(), key, shiftKey, currentTarget: h.dialog };
      h.tree.props.onKeyDown(e);
      return e.prevented;
    };
    first.focus();
    assert.equal(send(true), 1);
    assert.equal(h.document.activeElement, h.controls.submit);
    assert.equal(send(false), 1);
    assert.equal(h.document.activeElement, first);
    assert.equal(send(false), 0, 'Normal movement between controls stays native');
    h.controls.submit.focus();
    assert.equal(send(true), 0);
    assert.equal(send(false, 'Enter'), 0, 'Submit must not be consumed by focus trapping');
    h.render({ pending: true });
    assert.equal(send(false), 1, 'A pending dialog must not let Tab reach the background');
  }
});

test('Strict Mode effect replay reopens one modal without issuing actions or losing the trigger', () => {
  const h = harness();
  h.render({ open: true });
  h.replayEffects();
  assert.equal(h.dialog.shows, 2);
  assert.equal(h.dialog.closes, 1);
  assert.equal(h.dialog.open, true);
  assert.equal(h.document.activeElement, h.controls.input);
  h.render({ open: false });
  assert.equal(h.document.activeElement, h.trigger);
  assert.equal(h.dialog.closes, 2);
  assert.equal(h.calls.cancel, 0);
  assert.equal(h.calls.confirm, 0);
});
