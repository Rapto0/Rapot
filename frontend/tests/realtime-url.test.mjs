import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/lib/realtime/url.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const context = vm.createContext({ exports: {}, URL });
vm.runInContext(compiled, context);
const resolve = context.exports.resolveRealtimeWsBaseUrl;

test('relative API path keeps both TLS and public frontend port', () => {
  assert.equal(resolve('https://rapot.test', '/api'), 'wss://rapot.test/api/realtime/ws');
  assert.equal(resolve('http://localhost:3000', '/api/'), 'ws://localhost:3000/api/realtime/ws');
});

test('absolute API URL uses its own scheme, port and path', () => {
  assert.equal(
    resolve('https://rapot.test', 'http://localhost:8000'),
    'ws://localhost:8000/realtime/ws',
  );
  assert.equal(
    resolve('http://localhost:3000', 'https://api.rapot.test/v1'),
    'wss://api.rapot.test/v1/realtime/ws',
  );
});

test('explicit WebSocket URL remains supported and invalid API protocol falls back', () => {
  assert.equal(resolve('https://rapot.test', '/api', ' wss://ws.rapot.test/ '), 'wss://ws.rapot.test/realtime/ws');
  assert.equal(resolve('https://rapot.test', 'file:///etc/passwd'), 'wss://rapot.test/api/realtime/ws');
});
