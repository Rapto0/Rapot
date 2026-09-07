import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import test from 'node:test';
import ts from 'typescript';

const sourceRoot = fileURLToPath(new URL('../src/lib/', import.meta.url));

// Run the real TS modules in memory with an offline fetch implementation.
function createClient(apiBase = '/api') {
    const modules = new Map();
    const calls = [];
    let now = 1_800_000_000_000;
    let handler = () => Response.json({});
    const timers = new Map();
    let timerId = 0;
    const context = vm.createContext({
        Headers, URL, Set, Number,
        Date: class extends Date { static now() { return now; } },
        window: {
            location: { origin: 'https://rapot.test' },
            localStorage: { setItem() { assert.fail('Credentials must not be persisted'); } },
            sessionStorage: { setItem() { assert.fail('Credentials must not be persisted'); } },
        },
        process: { env: { NEXT_PUBLIC_API_URL: apiBase } },
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
        calls,
        respond(fn) { handler = fn; },
        advance(ms) { now += ms; },
        expire() { for (const callback of timers.values()) callback(); },
        login(token = 'test-token') {
            session.setSession({
                accessToken: token, expiresAt: now + 60_000,
                user: { username: 'admin', is_admin: true, disabled: false },
            });
        },
    };
}

test('sign in verifies identity before storing a memory-only session', async () => {
    const client = createClient();
    client.respond((url, options) => {
        if (url.endsWith('/auth/token')) {
            assert.deepEqual(JSON.parse(options.body), { username: 'admin', password: 'test-password' });
            return Response.json({ access_token: 'issued-token', token_type: 'bearer', expires_in: 60 });
        }
        assert.equal(options.headers.get('Authorization'), 'Bearer issued-token');
        assert.equal(client.session.getSession(), null);
        return Response.json({ username: 'admin', is_admin: true, disabled: false });
    });
    await client.auth.signIn('admin', 'test-password');
    assert.equal(client.session.getSession().user.is_admin, true);
    assert.equal(client.session.getAccessToken(), 'issued-token');
    client.session.clearSession();
    assert.equal(client.session.getSession(), null);
});

for (const failureAt of ['token', 'me']) {
    test(`failed ${failureAt} response never installs a session`, async () => {
        const client = createClient();
        client.respond((url) => url.endsWith(`/auth/${failureAt}`)
            ? Response.json({ detail: 'denied' }, { status: 401 })
            : Response.json({ access_token: 'issued-token', token_type: 'bearer', expires_in: 60 }));
        await assert.rejects(client.auth.signIn('admin', 'wrong'), (error) => error.status === 401);
        assert.equal(client.session.getSession(), null);
    });
}

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

test('current 401 clears the session, while 403 preserves it', async () => {
    const client = createClient();
    client.login();
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

test('late 401 from an old token does not clear a new login', async () => {
    const client = createClient();
    client.login('old-token');
    let complete;
    client.respond(() => new Promise((resolve) => { complete = resolve; }));
    const pending = client.core.fetchApi('/api/logs');
    client.login('new-token');
    complete(Response.json({}, { status: 401 }));
    await assert.rejects(pending, (error) => error.status === 401);
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
