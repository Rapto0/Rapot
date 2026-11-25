export type TrackerMarket = "BIST" | "Kripto"

export const RSI_TIMEFRAMES = [
    { id: "15m", label: "15 dakika", short: "15 dk", group: "Dakika" },
    { id: "30m", label: "30 dakika", short: "30 dk", group: "Dakika" },
    { id: "1h", label: "1 saat", short: "1 sa", group: "Saat" },
    { id: "2h", label: "2 saat", short: "2 sa", group: "Saat" },
    { id: "4h", label: "4 saat", short: "4 sa", group: "Saat" },
    { id: "1D", label: "1 gün", short: "1G", group: "Gün" },
    { id: "2D", label: "2 gün", short: "2G", group: "Gün" },
    { id: "3D", label: "3 gün", short: "3G", group: "Gün" },
    { id: "4D", label: "4 gün", short: "4G", group: "Gün" },
    { id: "5D", label: "5 gün", short: "5G", group: "Gün" },
    { id: "6D", label: "6 gün", short: "6G", group: "Gün" },
    { id: "1W", label: "1 hafta", short: "1H", group: "Hafta" },
    { id: "2W", label: "2 hafta", short: "2H", group: "Hafta" },
    { id: "3W", label: "3 hafta", short: "3H", group: "Hafta" },
    { id: "1M", label: "1 ay", short: "1A", group: "Ay" },
    { id: "2M", label: "2 ay", short: "2A", group: "Ay" },
] as const

export type RsiTimeframe = typeof RSI_TIMEFRAMES[number]["id"]
export const TRACKER_PAGE_SIZE = 25
export const TRACKER_REFRESH_MS = 120_000
export const TRACKER_SYMBOL_LIMIT = TRACKER_PAGE_SIZE
export const ALL_RSI_COLUMNS: RsiTimeframe[] = RSI_TIMEFRAMES.map(item => item.id)
export const RSI_COLUMNS_STORAGE_KEY = "rapot.rsi-tracker.columns.v1"
const sourceTimeFormat = new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Europe/Istanbul", dateStyle: "short", timeStyle: "medium",
})

export function storedRsiColumns(raw: string | null): RsiTimeframe[] {
    try {
        const value: unknown = JSON.parse(raw ?? "null")
        if (Array.isArray(value)) {
            const selected = ALL_RSI_COLUMNS.filter(period => value.includes(period))
            if (selected.length) return selected
        }
    } catch { /* Invalid preferences fall back to all columns. */ }
    return [...ALL_RSI_COLUMNS]
}

export interface RsiFilter { period: RsiTimeframe; min: string; max: string }
export interface RsiSort { period: RsiTimeframe; descending: boolean }

/** Filter only the fixed subscribed page; incomplete or stale values never match. */
export function trackerResultRows(symbols: readonly string[], snapshot: RsiSnapshot | undefined,
    filters: readonly RsiFilter[], sort: RsiSort | null, fresh: boolean, observedAt: number) {
    const value = (symbol: string, period: RsiTimeframe): number | null => {
        const row = snapshot?.rows[symbol], cell = row?.cells[period]
        if (!fresh || cell?.status !== "ready" || cell.value == null || !Number.isFinite(cell.value)
            || row?.source_time == null || (observedAt > 0 && (observedAt - row.source_time > 30 || row.source_time - observedAt > 5))) return null
        return cell.value
    }
    const active = filters.filter(filter => filter.min.trim() || filter.max.trim())
    const rows = symbols.filter(symbol => active.every(filter => {
        const number = value(symbol, filter.period)
        const min = filter.min.trim() ? Number(filter.min) : 0
        const max = filter.max.trim() ? Number(filter.max) : 100
        return number !== null && Number.isFinite(min) && Number.isFinite(max)
            && min >= 0 && max <= 100 && min <= max && number >= min && number <= max
    }))
    if (sort) rows.sort((a, b) => {
        const left = value(a, sort.period), right = value(b, sort.period)
        if (left === null || right === null) return left === right ? 0 : left === null ? 1 : -1
        return (left - right) * (sort.descending ? -1 : 1)
    })
    return rows
}

type RsiCellStatus = "ready" | "stale" | "candle" | "waiting" | "insufficient" | "capacity" | "paused" | "unavailable"

export interface RsiSnapshot {
    source: "borsapy_tradingview" | "tradingview_binance"
    length: number
    observed_at: number
    rows: Record<string, {
        source_time: number | null
        price: number | null
        cells: Partial<Record<RsiTimeframe, {
            status: RsiCellStatus
            value: number | null
            bar_time: number | null
        }>>
    }>
}

export const RSI_CELL_STATUS: Record<RsiCellStatus, string> = {
    ready: "Güncel fiyatla hesaplandı",
    stale: "Eski fiyat",
    candle: "Son mum kaydı",
    waiting: "Veri hazırlanıyor",
    insufficient: "Yetersiz mum geçmişi",
    capacity: "Takip kapasitesi dolu",
    paused: "Veri erişimi duraklatıldı",
    unavailable: "Periyot verisi alınamadı",
}

export function rsiSourceTime(epoch: number | null | undefined): string | null {
    if (typeof epoch !== "number" || !Number.isFinite(epoch)) return null
    return sourceTimeFormat.format(epoch * 1000)
}

export function toggleRsiColumn(selected: readonly RsiTimeframe[], id: RsiTimeframe): RsiTimeframe[] {
    const next = new Set(selected)
    if (next.has(id)) {
        if (next.size <= 1) return [...selected]
        next.delete(id)
    } else next.add(id)
    return RSI_TIMEFRAMES.filter(item => next.has(item.id)).map(item => item.id)
}

export function trackerPage(payload: readonly string[] | undefined, search: string, descending: boolean, requestedPage: number) {
    const source: unknown[] = Array.isArray(payload) ? payload : []
    const symbols = [...new Set(source.filter((symbol): symbol is string => typeof symbol === "string")
        .map(symbol => symbol.trim().toUpperCase()).filter(symbol => /^[A-Z0-9]{1,32}$/.test(symbol)))]
        .sort((a, b) => a.localeCompare(b, "en"))
    const query = search.trim().toUpperCase()
    const filtered = symbols.filter(symbol => symbol.includes(query))
    if (descending) filtered.reverse()
    const pages = Math.max(1, Math.ceil(filtered.length / TRACKER_PAGE_SIZE))
    const page = Math.min(pages - 1, Math.max(0, Number.isFinite(requestedPage) ? Math.floor(requestedPage) : 0))
    return { total: symbols.length, matched: filtered.length, pages, page,
        rows: filtered.slice(page * TRACKER_PAGE_SIZE, (page + 1) * TRACKER_PAGE_SIZE) }
}

export function trackerChartHref(symbol: string, market: TrackerMarket) {
    return `/chart?${new URLSearchParams({ symbol, market })}`
}

export function trackerAlarmHref(symbol: string, market: TrackerMarket) {
    return `/alarms?${new URLSearchParams({ symbol, market })}`
}

export function trackerNumber(value: number | undefined | null): string {
    return typeof value === "number" && Number.isFinite(value)
        ? value.toLocaleString("tr-TR", { maximumFractionDigits: 5 }) : "—"
}

export interface TrackerUrlState {
    market: TrackerMarket
    search: string
    descending: boolean
    page: number
    listId: string
    filters: RsiFilter[]
    sort: RsiSort | null
}

const VALID_PERIODS = new Set<string>(ALL_RSI_COLUMNS)

function isValidRsiBound(raw: string): boolean {
    if (!raw) return true
    if (!/^\d{1,3}(?:\.\d{1,2})?$/.test(raw)) return false
    const num = Number(raw)
    return Number.isFinite(num) && num >= 0 && num <= 100
}

export function parseTrackerUrlState(searchString: string): Partial<TrackerUrlState> {
    const params = new URLSearchParams(searchString)
    const state: Partial<TrackerUrlState> = {}
    const rawMarket = params.get("market")
    if (rawMarket === "BIST" || rawMarket === "Kripto") state.market = rawMarket
    const rawSearch = params.get("q")
    if (rawSearch !== null) state.search = rawSearch.slice(0, 32)
    if (params.get("desc") === "1") state.descending = true
    const rawPage = params.get("page")
    if (rawPage !== null && /^\d+$/.test(rawPage)) {
        const parsedPage = Number.parseInt(rawPage, 10)
        if (Number.isSafeInteger(parsedPage) && parsedPage >= 0 && parsedPage < 10_000) state.page = parsedPage
    }
    const rawList = params.get("list")
    if (rawList !== null) state.listId = rawList.slice(0, 128)
    const rawSort = params.get("sort")
    if (rawSort) {
        const [period, dir] = rawSort.split(":")
        if (VALID_PERIODS.has(period) && (dir === "asc" || dir === "desc")) {
            state.sort = { period: period as RsiTimeframe, descending: dir === "desc" }
        }
    }
    const rawFilters = params.get("filters")
    if (rawFilters) {
        const parsed: RsiFilter[] = []
        const seen = new Set<string>()
        for (const chunk of rawFilters.split(",").slice(0, 16)) {
            const [period, min = "", max = ""] = chunk.split(":")
            if (!VALID_PERIODS.has(period) || seen.has(period)) continue
            if (!isValidRsiBound(min) || !isValidRsiBound(max)) continue
            seen.add(period)
            parsed.push({ period: period as RsiTimeframe, min, max })
        }
        if (parsed.length) state.filters = parsed
    }
    return state
}

export function serializeTrackerUrlState(state: TrackerUrlState): string {
    const params = new URLSearchParams()
    if (state.market !== "BIST") params.set("market", state.market)
    if (state.search.trim()) params.set("q", state.search.trim().slice(0, 32))
    if (state.descending) params.set("desc", "1")
    if (state.page > 0) params.set("page", String(state.page))
    if (state.listId) params.set("list", state.listId)
    if (state.sort) params.set("sort", `${state.sort.period}:${state.sort.descending ? "desc" : "asc"}`)
    const activeFilters = state.filters.filter(filter => filter.min.trim() || filter.max.trim())
    if (activeFilters.length) {
        params.set("filters", activeFilters.map(filter => `${filter.period}:${filter.min.trim()}:${filter.max.trim()}`).join(","))
    }
    return params.toString()
}

export interface RsiReadinessSummary {
    total: number
    numeric: number
    ready: number
    stale: number
    candle: number
    waiting: number
    insufficient: number
    other: number
    percent: number
}

export function summarizeRsiCells(
    symbols: readonly string[],
    snapshot: RsiSnapshot | undefined,
    periods: readonly RsiTimeframe[],
): RsiReadinessSummary {
    const total = symbols.length * periods.length
    let numeric = 0
    let ready = 0
    let stale = 0
    let candle = 0
    let waiting = 0
    let insufficient = 0
    let other = 0
    for (const symbol of symbols) {
        const cells = snapshot?.rows[symbol]?.cells
        for (const period of periods) {
            const cell = cells?.[period]
            const status = cell?.status ?? "waiting"
            if (cell?.value != null && Number.isFinite(cell.value)) numeric++
            if (status === "ready") ready++
            else if (status === "stale") stale++
            else if (status === "candle") candle++
            else if (status === "waiting") waiting++
            else if (status === "insufficient") insufficient++
            else other++
        }
    }
    const percent = total > 0 ? Math.round(((numeric + insufficient) / total) * 100) : 0
    return { total, numeric, ready, stale, candle, waiting, insufficient, other, percent }
}

export interface RsiPreset {
    id: string
    label: string
    filters: readonly RsiFilter[]
    sort: RsiSort
}

export const RSI_PRESETS: readonly RsiPreset[] = [
    { id: "oversold-1d", label: "Aşırı satım (1G ≤ 30)", filters: [{ period: "1D", min: "", max: "30" }], sort: { period: "1D", descending: false } },
    { id: "overbought-1d", label: "Aşırı alım (1G ≥ 70)", filters: [{ period: "1D", min: "70", max: "" }], sort: { period: "1D", descending: true } },
    { id: "multi-dip", label: "Çoklu dip (15dk & 1G ≤ 30)", filters: [{ period: "15m", min: "", max: "30" }, { period: "1D", min: "", max: "30" }], sort: { period: "15m", descending: false } },
]

function csvEscape(value: string): string {
    const safe = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value
    return /[",\n\r]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe
}

export function buildTrackerCsv(
    symbols: readonly string[],
    market: TrackerMarket,
    pricesBySymbol: Record<string, { price?: number | null; change?: number | null }>,
    snapshot: RsiSnapshot | undefined,
    periods: readonly RsiTimeframe[],
): string {
    const headers = [
        "Sembol",
        "Piyasa",
        market === "BIST" ? "Son Fiyat (TRY)" : "Son Fiyat (USDT)",
        "Değişim (%)",
        ...periods.map(period => `RSI ${period}`),
    ]
    const lines = [headers.map(csvEscape).join(",")]
    for (const symbol of symbols) {
        const quote = pricesBySymbol[symbol]
        const rsiRow = snapshot?.rows[symbol]
        const cells = [
            symbol,
            market,
            typeof quote?.price === "number" && Number.isFinite(quote.price) ? String(quote.price) : "",
            typeof quote?.change === "number" && Number.isFinite(quote.change) ? quote.change.toFixed(2) : "",
            ...periods.map(period => {
                const val = rsiRow?.cells[period]?.value
                return typeof val === "number" && Number.isFinite(val) ? val.toFixed(2) : ""
            }),
        ]
        lines.push(cells.map(csvEscape).join(","))
    }
    return `\uFEFF${lines.join("\r\n")}`
}
