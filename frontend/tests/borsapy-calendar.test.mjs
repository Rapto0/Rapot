import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../src/app/calendar/page.tsx', import.meta.url), 'utf8');
const compiled = ts.transpileModule(`${source}\nexports.testing = { mapCalendarEvents, formatMetric, istanbulDay, addDays };`, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
}).outputText;
let session = null;
const queries = [];
const requests = [];
const jsx = (type, props) => ({ type, props });
const context = vm.createContext({ exports: {}, Date, Intl, Number,
    require(name) {
        if (name === 'react/jsx-runtime') return { jsx, jsxs: jsx };
        if (name === 'react') return {
            useMemo: fn => fn(), useEffect: () => {},
            useState: value => [typeof value === 'function' ? value() : value, () => {}],
        };
        if (name === '@tanstack/react-query') return { useQuery: options => {
            queries.push(options);
            return { data: undefined, isLoading: false, isFetching: false, isError: false };
        } };
        if (name === '@/lib/hooks/use-session') return { useSession: () => session };
        if (name === '@/lib/api/client') return { fetchEconomicCalendar: (...args) => { requests.push(args); return Promise.resolve({ events: [] }); } };
        if (name === '@/lib/utils') return { cn: (...args) => args.join(' ') };
        if (name === 'next/link') return { default: 'a' };
        if (name === 'lucide-react') return { RefreshCw: 'svg' };
        if (name === '@/components/ui/button') return { Button: 'button' };
        if (name === '@/components/ui/page-shell') return { PageShell: ({ children }) => children };
        if (name === '@/components/ui/filter-chips') return { FilterChips: 'fieldset' };
        throw new Error(`Unexpected import ${name}`);
    },
});
vm.runInContext(compiled, context);
const page = context.exports;
const plain = value => JSON.parse(JSON.stringify(value));
function render(node) {
    if (Array.isArray(node)) return node.map(render);
    if (!node || typeof node !== 'object') return node;
    if (typeof node.type === 'function') return render(node.type(node.props));
    return { ...node, props: { ...node.props, children: render(node.props?.children) } };
}

const event = overrides => ({ id: 'sample', date: '2026-10-04', source_time: '09:30', time: null,
    timestamp: null, country: 'Türkiye', event: 'Enflasyon', impact: 'mid', actual: '64.77%',
    estimate: null, previous: 0, unit: null, currency: null, ...overrides });

test('calendar page does not mount a private query for guests, normal users or disabled admins', () => {
    queries.length = 0;
    for (const user of [null, { is_admin: false }, { is_admin: true, disabled: true }]) {
        session = user ? { user, expiresAt: 123 } : null;
        const tree = render(page.default());
        assert.match(JSON.stringify(tree), /yönetici/);
    }
    assert.equal(queries.length, 0);
});

test('admin query is session scoped, abortable and does not automatically retry', async () => {
    queries.length = 0;
    session = { user: { username: 'owner', is_admin: true }, expiresAt: 456 };
    render(page.default());
    assert.equal(queries.length, 1);
    const query = queries[0];
    assert.equal(query.queryKey[1], 'owner:456');
    assert.equal(query.retry, false);
    const signal = new AbortController().signal;
    await query.queryFn({ signal });
    assert.equal(requests.at(-1)[1].signal, signal);
    assert.equal(requests.at(-1)[0].from_date, query.queryKey[2]);
});

test('text, null and zero metrics and medium impact survive the real view mapping', () => {
    const rows = plain(page.testing.mapCalendarEvents([event()]));
    assert.equal(rows[0].actual, '64.77%');
    assert.equal(rows[0].forecast, '—');
    assert.equal(rows[0].previous, '0');
    assert.equal(rows[0].impact, 'Orta');
    assert.equal(page.testing.formatMetric('250K', '%'), '250K');
    assert.equal(page.testing.formatMetric(Number.NaN, null), '—');
});

test('unspecified event clock is retained without inventing midnight or an absolute timestamp', () => {
    const rows = plain(page.testing.mapCalendarEvents([
        event({ id: 'unknown', source_time: null }), event({ id: 'known', source_time: '10:00' }),
    ]));
    assert.deepEqual(rows.map(row => row.id), ['known', 'unknown']);
    assert.equal(rows[1].date, '2026-10-04');
    assert.equal(rows[1].time, 'Saat belirtilmedi');
    assert.equal(rows[0].time, '10:00');
});

test('the date window follows Istanbul midnight independently of browser timezone', () => {
    assert.equal(page.testing.istanbulDay(new Date('2026-10-04T21:01:00Z')), '2026-10-05');
    assert.equal(page.testing.addDays('2026-10-31', 14), '2026-11-14');
});
