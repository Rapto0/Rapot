import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';
import ts from 'typescript';

const sourceRoot = fileURLToPath(new URL('../src/lib/', import.meta.url));

test('private market and calendar requests stop before HTTP when the session is absent or expired', async () => {
    const client = createClient();
    for (const target of ['/api/borsapy/market/indices', '/api/borsapy/candles/THYAO', '/api/calendar?country=TR']) {
        await assert.rejects(client.core.fetchApi(target), error => error.status === 401);
    }
    assert.equal(client.calls.length, 0);
    client.loginCookie();
    await client.core.fetchApi('/api/borsapy/market/indices');
    assert.equal(client.calls[0].headers.get('Authorization'), null);
    assert.equal(client.calls[0].credentials, 'same-origin');
    client.advance(61_000);
    await assert.rejects(client.core.fetchApi('/api/calendar'), error => error.status === 401);
    assert.equal(client.calls.length, 1);
});

test('the request deadline covers a slow response body even when a caller supplies an abort signal', async () => {
    const client = createClient();
    const caller = new AbortController();
    let startBody;
    const bodyStarted = new Promise(resolve => { startBody = resolve; });
    client.respond((_url, { signal }) => ({
        ok: true, status: 200,
        json: () => new Promise((_resolve, reject) => {
            signal.addEventListener('abort', () => reject(signal.reason), { once: true });
            startBody();
        }),
    }));
    const request = client.core.fetchApi('/api/health', { signal: caller.signal });
    const rejected = assert.rejects(request, error => error.status === 408);
    await bodyStarted;
    client.expire();
    await rejected;
    assert.equal(caller.signal.aborted, false);
});

test('caller cancellation remains an abort and an unsuccessful session probe settles bootstrap', async () => {
    const client = createClient();
    const caller = new AbortController();
    client.respond((_url, { signal }) => new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => reject(signal.reason), { once: true });
    }));
    const pending = client.core.fetchApi('/api/health', { signal: caller.signal });
    caller.abort();
    await assert.rejects(pending, error => error.name === 'AbortError');
    assert.equal(client.session.getSessionChecked(), false);
    client.respond(() => Response.json({ authenticated: false }));
    assert.equal(await client.auth.hydrateSession(), false);
    assert.equal(client.session.getSessionChecked(), true);
    assert.equal(client.session.getSession(), null);
});

// Run the real TS modules in memory with an offline fetch implementation.
function createClient(apiBase = '/api', healthBase = '/health-api') {
    const modules = new Map();
    const calls = [];
    let now = 1_800_000_000_000;
    let handler = () => Response.json({});
    const timers = new Map();
    let timerId = 0;
    const documentObj = { cookie: '' };
    const context = vm.createContext({
        Headers, URL, Set, Number, AbortController,
        Date: class extends Date { static now() { return now; } },
        document: documentObj,
        window: {
            location: { origin: 'https://rapot.test' },
            localStorage: { setItem() { assert.fail('Credentials must not be persisted'); } },
            sessionStorage: { setItem() { assert.fail('Credentials must not be persisted'); } },
        },
        process: { env: { NEXT_PUBLIC_API_URL: apiBase, NEXT_PUBLIC_HEALTH_API_URL: healthBase } },
        setTimeout: (callback) => { timers.set(++timerId, callback); return timerId; },
        clearTimeout: (id) => timers.delete(id),
        fetch: async (url, options) => {
            calls.push({ url, ...options });
            return handler(url, options);
        },
    });
    function load(filename) {
        if (modules.has(filename)) return modules.get(filename).exports;
        const compiled = ts.transpileModule(readFileSync(filename, 'utf8'), {
            compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
        }).outputText;
        const loadedModule = { exports: {} };
        modules.set(filename, loadedModule);
        const execute = vm.runInContext(`(function(require,module,exports) { ${compiled}\n })`, context);
        execute((specifier) => {
            assert.ok(specifier.startsWith('.'), `Unexpected external import: ${specifier}`);
            return load(path.resolve(path.dirname(filename), `${specifier}.ts`));
        }, loadedModule, loadedModule.exports);
        return loadedModule.exports;
    }
    const session = load(path.join(sourceRoot, 'auth/session.ts'));
    return {
        session,
        core: load(path.join(sourceRoot, 'api/core.ts')),
        auth: load(path.join(sourceRoot, 'api/auth-api.ts')),
        ops: load(path.join(sourceRoot, 'api/ops-api.ts')),
        calls,
        document: documentObj,
        respond(fn) { handler = fn; },
        advance(ms) { now += ms; },
        expire() { for (const callback of timers.values()) callback(); },
        login(token = 'test-token') {
            session.setSession({
                accessToken: token, expiresAt: now + 60_000,
                user: { username: 'admin', is_admin: true, disabled: false },
            });
        },
        loginCookie() {
            session.setSession({
                expiresAt: now + 60_000,
                user: { username: 'admin', is_admin: true, disabled: false },
            });
        },
    };
}

test('sign in creates an HttpOnly cookie session without storing a JWT in JS memory', async () => {
    const client = createClient();
    client.respond((url, options) => {
        assert.equal(url, '/api/auth/session');
        assert.equal(options.method, 'POST');
        assert.equal(options.credentials, 'same-origin');
        assert.deepEqual(JSON.parse(options.body), { username: 'admin', password: 'test-password' });
        assert.equal(client.session.getSession(), null);
        return Response.json({
            authenticated: true,
            user: { username: 'admin', is_admin: true, disabled: false },
            expires_in: 60,
        });
    });
    await client.auth.signIn('admin', 'test-password');
    assert.equal(client.session.getSession().user.is_admin, true);
    assert.equal(client.session.getAccessToken(), null);
    assert.equal(client.session.hasActiveSession(), true);

    client.document.cookie = 'rapot_csrf=csrf-abc123';
    client.respond((url, options) => {
        assert.equal(url, '/api/auth/logout');
        assert.equal(options.method, 'POST');
        assert.equal(options.headers.get('X-CSRF-Token'), 'csrf-abc123');
        return Response.json({ logged_out: true });
    });
    await client.auth.signOut();
    assert.equal(client.session.getSession(), null);
});

test('hydrateSession restores HttpOnly session on reload without overwriting a newer login', async () => {
    const client = createClient();
    client.respond((url, options) => {
        assert.equal(url, '/api/auth/session');
        assert.equal(options.credentials, 'same-origin');
        return Response.json({
            authenticated: true,
            user: { username: 'admin', is_admin: true, disabled: false },
            expires_in: 120,
        });
    });
    assert.equal(await client.auth.hydrateSession(), true);
    assert.equal(client.session.getSession().user.username, 'admin');

    // A stale hydrate response must not overwrite a newer session established in-flight.
    let resolveHydrate;
    client.respond(() => new Promise((resolve) => { resolveHydrate = resolve; }));
    const pendingHydrate = client.auth.hydrateSession();
    client.session.setSession({
        expiresAt: 1_800_000_000_000 + 300_000,
        user: { username: 'fresh-admin', is_admin: true, disabled: false },
    });
    resolveHydrate(Response.json({
        authenticated: true,
        user: { username: 'stale-admin', is_admin: true, disabled: false },
        expires_in: 60,
    }));
    assert.equal(await pendingHydrate, false);
    assert.equal(client.session.getSession().user.username, 'fresh-admin');
});

test('failed signIn response never installs a session', async () => {
    const client = createClient();
    client.respond(() => Response.json({ detail: 'denied' }, { status: 401 }));
    await assert.rejects(client.auth.signIn('admin', 'wrong'), (error) => error.status === 401);
    assert.equal(client.session.getSession(), null);
});

test('CSRF header is attached only to mutating core API cookie requests and ws-ticket uses it', async () => {
    const client = createClient();
    client.loginCookie();
    client.document.cookie = 'other=1; rapot_csrf=csrf-xyz-789';
    client.respond((url) => {
        if (url.endsWith('/auth/ws-ticket')) return Response.json({ ticket: 'short-ws-ticket', expires_in: 30 });
        return Response.json({});
    });
    await client.core.fetchApi('/api/logs');
    await client.core.fetchApi('/api/alarms', { method: 'POST', body: '{}' });
    await client.core.fetchApi('https://external.invalid/api/alarms', { method: 'POST', body: '{}' });
    const ticket = await client.auth.fetchWsTicket();

    assert.equal(ticket, 'short-ws-ticket');
    assert.equal(client.calls[0].headers.get('X-CSRF-Token'), null);
    assert.equal(client.calls[1].headers.get('X-CSRF-Token'), 'csrf-xyz-789');
    assert.equal(client.calls[1].credentials, 'same-origin');
    assert.equal(client.calls[2].headers.get('X-CSRF-Token'), null);
    assert.equal(client.calls[2].credentials, undefined);
    assert.equal(client.calls[3].headers.get('X-CSRF-Token'), 'csrf-xyz-789');
});

test('bearer token is scoped to the configured API origin and path', async () => {
    const client = createClient();
    client.login();
    for (const url of ['/api/logs', 'https://rapot.test/api/auth/me', '/health-api/health',
        '/api-other/logs', 'https://external.invalid/api/logs']) {
        await client.core.fetchApi(url);
    }
    assert.deepEqual(client.calls.map((call) => call.headers.get('Authorization')),
        ['Bearer test-token', 'Bearer test-token', null, null, null]);
    assert.ok(client.calls.every((call) => call.cache === 'no-store'));
});

test('absolute configured API base and Headers overrides are supported', async () => {
    const client = createClient('https://backend.invalid/v1/');
    client.login();
    await client.core.fetchApi('https://backend.invalid/v1/logs');
    await client.core.fetchApi('/api/logs');
    await client.core.fetchApi('https://backend.invalid/v1/logs', {
        headers: new Headers({ Authorization: 'Bearer explicit', 'X-Request-ID': 'test-id' }),
    });
    assert.deepEqual(client.calls.map((call) => call.headers.get('Authorization')),
        ['Bearer test-token', null, 'Bearer explicit']);
    assert.equal(client.calls[2].headers.get('X-Request-ID'), 'test-id');
});

test('health uses the main API and ignores legacy health configuration', async () => {
    for (const healthBase of ['/health-api', 'https://external.invalid/health-api']) {
        const client = createClient('/api', healthBase);
        client.login();
        await client.ops.fetchHealth();
        assert.equal(client.calls[0].url, '/api/health');
        assert.equal(client.calls[0].headers.get('Authorization'), 'Bearer test-token');
        assert.equal(client.calls[0].cache, 'no-store');
        assert.equal(client.ops.fetchBotStatus, undefined);
        assert.equal(client.ops.analyzeSymbol, undefined);
    }
});

test('retired bot paths never receive credentials or clear a session', async () => {
    const client = createClient();
    client.login();
    client.respond(() => Response.json({}, { status: 401 }));
    for (const url of ['/health-api/status', '/health-api/health', 'https://external.invalid/health-api/status']) {
        await assert.rejects(client.core.fetchApi(url), error => error.status === 401);
    }
    assert.ok(client.calls.every(call => call.headers.get('Authorization') === null));
    assert.equal(client.session.getAccessToken(), 'test-token');
});

test('an unavailable API health response rejects instead of caching success and retains the session', async () => {
    const client = createClient();
    client.login();
    client.respond(() => Response.json({ status: 'unhealthy' }, { status: 503 }));
    await assert.rejects(client.ops.fetchHealth(), error => error.status === 503);
    assert.equal(client.session.getAccessToken(), 'test-token');
});

test('current 401 clears cookie and bearer sessions, while 403 preserves them', async () => {
    const client = createClient();
    client.loginCookie();
    client.respond(() => Response.json({}, { status: 403 }));
    await assert.rejects(client.core.fetchApi('/api/logs'), (error) => error.status === 403);
    assert.ok(client.session.getSession());
    let notifications = 0;
    const unsubscribe = client.session.subscribeSession(() => { notifications++; });
    client.respond(() => Response.json({}, { status: 401 }));
    await assert.rejects(client.core.fetchApi('/api/logs'), (error) => error.status === 401);
    assert.equal(client.session.getSession(), null);
    assert.equal(notifications, 1);
    unsubscribe();
});

test('late 401 from an old cookie or bearer session does not clear a new login', async () => {
    const client = createClient();
    client.loginCookie();
    let complete;
    client.respond(() => new Promise((resolve) => { complete = resolve; }));
    const pending = client.core.fetchApi('/api/logs');
    client.loginCookie();
    complete(Response.json({}, { status: 401 }));
    await assert.rejects(pending, (error) => error.status === 401);
    assert.ok(client.session.getSession());

    client.login('old-token');
    const pendingBearer = client.core.fetchApi('/api/logs');
    client.login('new-token');
    complete(Response.json({}, { status: 401 }));
    await assert.rejects(pendingBearer, (error) => error.status === 401);
    assert.equal(client.session.getAccessToken(), 'new-token');
});

test('expired sessions notify subscribers and never send a token', async () => {
    const client = createClient();
    client.login();
    let notifications = 0;
    client.session.subscribeSession(() => { notifications++; });
    client.advance(61_000);
    await client.core.fetchApi('/api/logs');
    assert.equal(client.calls[0].headers.get('Authorization'), null);
    assert.equal(client.session.getSession(), null);
    assert.equal(notifications, 1);
});

test('expiry timer signs out idle tabs without requiring a request', () => {
    const client = createClient();
    client.login();
    client.advance(61_000);
    client.expire();
    assert.equal(client.session.getSession(), null);
});

test('fetchApi surfaces single-line backend details on 4xx/5xx errors and aborts hung requests', async () => {
    const client = createClient();
    client.login();
    client.respond(() => Response.json({ detail: 'Sembol desteklenmiyor.' }, { status: 400 }));
    await assert.rejects(client.core.fetchApi('/api/symbols/check'),
        error => error.status === 400 && error.message === 'Sembol desteklenmiyor.');

    client.respond(() => Response.json({ detail: [{ msg: 'Value error, Eşik 0-100 arası olmalı.' }] }, { status: 422 }));
    await assert.rejects(client.core.fetchApi('/api/alarms'),
        error => error.status === 422 && error.message === 'Eşik 0-100 arası olmalı.');

    client.respond(() => Response.json({ detail: 'Traceback\nline 2' }, { status: 503, statusText: 'Service Unavailable' }));
    await assert.rejects(client.core.fetchApi('/api/health'),
        error => error.status === 503 && error.message === 'API error: Service Unavailable');

    client.respond((_url, options) => new Promise((_resolve, reject) => {
        options.signal.addEventListener('abort', () => reject(new Error('aborted')));
    }));
    const pending = client.core.fetchApi('/api/logs');
    client.expire();
    await assert.rejects(pending, error => error.status === 408 && /zaman aşımı/.test(error.message));
});
