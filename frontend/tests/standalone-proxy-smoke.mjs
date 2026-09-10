// Run after a local build with the default localhost proxy targets. No real API/bot is used.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { cpSync, readFileSync } from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const root = fileURLToPath(new URL('../', import.meta.url));
const manifest = JSON.parse(readFileSync(path.join(root, '.next/routes-manifest.json'), 'utf8'));
const rewrites = Object.values(manifest.rewrites).flat();
const apiTarget = new URL(rewrites.find(r => r.source === '/api/:path*').destination);
const healthTarget = new URL(rewrites.find(r => r.source === '/health-api/:path*').destination);
for (const target of [apiTarget, healthTarget]) {
  assert.ok(['localhost', '127.0.0.1', '[::1]'].includes(target.hostname), 'Smoke test requires local build targets');
}

const sockets = new Set();
const servers = [];
let child;
let output = '';
function localFetch(url, options = {}) {
  return fetch(url, { ...options, signal: AbortSignal.timeout(5000) });
}
function listen(server, port, hostname) {
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, hostname, () => { server.off('error', reject); resolve(server.address().port); });
  });
}
function mockService(name) {
  const server = http.createServer((req, res) => {
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ service: name, path: req.url, authorization: req.headers.authorization }));
  });
  server.on('connection', socket => { sockets.add(socket); socket.on('close', () => sockets.delete(socket)); });
  servers.push(server);
  return server;
}

try {
  const api = mockService('api');
  api.on('upgrade', (req, socket) => {
    assert.equal(req.url, '/realtime/ws/signals');
    const accept = createHash('sha1').update(req.headers['sec-websocket-key'] + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
    socket.write(`HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ${accept}\r\n\r\n`);
  });
  await listen(api, Number(apiTarget.port), apiTarget.hostname);
  await listen(mockService('bot-health'), Number(healthTarget.port), healthTarget.hostname);
  const reservation = net.createServer();
  const frontendPort = await listen(reservation, 0, '127.0.0.1');
  await new Promise(resolve => reservation.close(resolve));
  cpSync(path.join(root, 'public'), path.join(root, '.next/standalone/public'), { recursive: true });
  cpSync(path.join(root, '.next/static'), path.join(root, '.next/standalone/.next/static'), { recursive: true });
  child = spawn(process.execPath, [path.join(root, '.next/standalone/server.js')], {
    cwd: path.join(root, '.next/standalone'),
    env: { ...process.env, PORT: String(frontendPort), HOSTNAME: '127.0.0.1', NODE_ENV: 'production' },
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  child.stdout.on('data', data => { output += data; });
  child.stderr.on('data', data => { output += data; });
  const origin = `http://127.0.0.1:${frontendPort}`;
  let page;
  for (let attempt = 0; attempt < 40; attempt++) {
    try {
      page = await localFetch(origin);
      if (page.ok) break;
      await page.body?.cancel();
    } catch { /* server starting */ }
    assert.equal(child.exitCode, null, output);
    await delay(250);
  }
  assert.ok(page?.ok, output);
  const html = await page.text();
  const asset = html.match(/src="(\/_next\/static\/[^" ]+\.js)"/);
  assert.ok(asset, 'Expected a standalone static asset');
  const staticAsset = await localFetch(origin + asset[1]);
  assert.equal(staticAsset.status, 200);
  assert.ok((await staticAsset.arrayBuffer()).byteLength > 0);
  const proxied = await localFetch(origin + '/api/auth/me?smoke=1', { headers: { Authorization: 'Bearer local-smoke' } });
  assert.deepEqual(await proxied.json(), { service: 'api', path: '/auth/me?smoke=1', authorization: 'Bearer local-smoke' });
  const health = await localFetch(origin + '/health-api/health');
  assert.deepEqual(await health.json(), { service: 'bot-health', path: '/health' });
  // Exercise Next's actual async searchParams contract, not just the page function.
  for (const [query, symbol, market] of [
    ['symbol=BTCUSDT&market=Kripto', 'BTCUSDT', 'Kripto'],
    ['symbol=%20asels%20&market=bist', 'ASELS', 'BIST'],
    ['symbol=ETHUSDT&symbol=THYAO&market=Kripto&market=BIST', 'ETHUSDT', 'Kripto'],
    ['symbol=..%2Finvalid&market=Kripto', 'BTCUSDT', 'Kripto'],
    ['', 'THYAO', 'BIST'],
  ]) {
    const chart = await localFetch(`${origin}/chart?${query}`);
    assert.equal(chart.status, 200);
    assert.ok((await chart.text()).includes(`aria-label="Sembol seç: ${symbol} (${market})"`), query);
  }
  const navigation = await localFetch(origin + '/chart?symbol=ETHUSDT&market=Kripto', { headers: { RSC: '1' } });
  assert.equal(navigation.status, 200);
  assert.match(navigation.headers.get('content-type'), /text\/x-component/);
  const flight = await navigation.text();
  assert.ok(flight.includes('"initialSymbol":"ETHUSDT"'));
  assert.ok(flight.includes('"initialMarket":"Kripto"'));
  await new Promise((resolve, reject) => {
    const socket = net.connect(frontendPort, '127.0.0.1');
    socket.setTimeout(5000, () => socket.destroy(new Error('WebSocket proxy timeout')));
    socket.once('error', reject);
    socket.once('connect', () => socket.write('GET /api/realtime/ws/signals HTTP/1.1\r\nHost: localhost\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Version: 13\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n\r\n'));
    socket.once('data', data => {
      try { assert.match(data.toString(), /^HTTP\/1\.1 101/); resolve(); } catch (error) { reject(error); }
      socket.destroy();
    });
  });
  console.log('Standalone HTML/static assets, chart URL/Flight props, authenticated API proxy, bot health proxy and WebSocket upgrade passed.');
} finally {
  // Close mock upstream sockets before waiting for Next's POSIX graceful shutdown.
  // Open upgraded connections can otherwise keep server.close() waiting forever.
  for (const socket of sockets) socket.destroy();
  await Promise.all(servers.map(server => new Promise(resolve => server.close(resolve))));
  if (child && child.exitCode === null && child.signalCode === null) {
    await new Promise(resolve => {
      const deadline = setTimeout(() => child.kill('SIGKILL'), 5000);
      child.once('exit', () => { clearTimeout(deadline); resolve(); });
      child.kill();
    });
  }
}
