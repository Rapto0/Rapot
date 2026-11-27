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
export const TRACKER_PREPARATION_POLL_MS = 10_000
export const TRACKER_PREPARATION_WINDOW_MS = 60_000
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
            || !trackerQuoteFresh(row?.source_time, observedAt)) return null
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

export interface RsiCell {
    status: RsiCellStatus
    value: number | null
    bar_time: number | null
    received_at?: number
    last?: { value: number; bar_time: number; bar_end?: number; received_at: number; kind: "closed" | "candle"; source?: string }
    closed_status?: "insufficient"
    closed_source?: string
}

export interface RsiSnapshot {
    snapshot_version?: number
    closed_source?: string
    source: "borsapy_tradingview" | "tradingview_binance"
    length: number
    observed_at: number
    rows: Record<string, {
        source_time: number | null
        price: number | null
        session_ended?: boolean
        last_price?: { value: number; source_time: number; received_at: number; source?: string; kind?: "closed" }
        cells: Partial<Record<RsiTimeframe, RsiCell>>
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

export function rsiDisplayValue(cell?: RsiCell): number | null {
    const value = cell?.value ?? cell?.last?.value
    return value != null && Number.isFinite(value) ? value : null
}

export function trackerQuoteFresh(sourceTime: number | null | undefined, observedAt: number) {
    return sourceTime != null && Number.isFinite(sourceTime) &&
        (observedAt <= 0 || (observedAt - sourceTime <= 30 && sourceTime - observedAt <= 5))
}

export function rsiDisplayStatus(cell: RsiCell | undefined, expired: boolean): string {
    const status = cell?.status ?? "waiting"
    if (cell?.last) {
        const label = cell.last.kind === "closed" ? "Son kapanış" : "Son mum kaydı"
        return `${label} · ${RSI_CELL_STATUS[status]}`
    }
    if (cell?.closed_status === "insufficient" && status === "waiting") return "Kapanış geçmişi yetersiz · Veri hazırlanıyor"
    return expired && status === "ready" ? "Son alınan RSI" : RSI_CELL_STATUS[status]
}

export function trackerPollInterval(snapshot: RsiSnapshot | undefined, startedAt: number, now: number) {
    if (startedAt > 0 && now + TRACKER_PREPARATION_POLL_MS - startedAt <= TRACKER_PREPARATION_WINDOW_MS &&
        Object.values(snapshot?.rows ?? {}).some(row => Object.values(row.cells).some(cell => cell.status === "waiting"))) {
        return TRACKER_PREPARATION_POLL_MS
    }
    return TRACKER_REFRESH_MS
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
    retained: number
    waiting: number
    insufficient: number
    other: number
    percent: number
}

export function summarizeRsiCells(
    symbols: readonly string[],
    snapshot: RsiSnapshot | undefined,
    periods: readonly RsiTimeframe[],
    fresh = true,
    observedAt = snapshot?.observed_at ?? 0,
): RsiReadinessSummary {
    const total = symbols.length * periods.length
    let numeric = 0
    let ready = 0
    let stale = 0
    let candle = 0
    let retained = 0
    let waiting = 0
    let insufficient = 0
    let other = 0
    for (const symbol of symbols) {
        const row = snapshot?.rows[symbol]
        const quoteFresh = fresh && trackerQuoteFresh(row?.source_time, observedAt)
        for (const period of periods) {
            const cell = row?.cells[period]
            const status = cell?.status ?? "waiting"
            if (rsiDisplayValue(cell) != null) numeric++
            if (cell?.last && cell.value == null) retained++
            if (status === "ready" && quoteFresh) ready++
            else if (status === "stale" || status === "ready") stale++
            else if (status === "candle") candle++
            else if (status === "waiting") waiting++
            else if (status === "insufficient") insufficient++
            else other++
        }
    }
    const percent = total > 0 ? Math.round(((numeric - retained + insufficient) / total) * 100) : 0
    return { total, numeric, ready, stale, candle, retained, waiting, insufficient, other, percent }
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
    expired = false,
    observedAt = snapshot?.observed_at ?? 0,
): string {
    const headers = [
        "Sembol",
        "Piyasa",
        market === "BIST" ? "Son Fiyat (TRY)" : "Son Fiyat (USDT)",
        "Değişim (%)",
        ...periods.map(period => `RSI ${period}`),
        ...periods.flatMap(period => [`RSI ${period} Durum`, `RSI ${period} Veri Zamanı`, `RSI ${period} Kaynak`]),
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
                return rsiDisplayValue(rsiRow?.cells[period])?.toFixed(2) ?? ""
            }),
            ...periods.flatMap(period => {
                const cell = rsiRow?.cells[period]
                const timestamp = cell?.last?.bar_end ?? cell?.last?.bar_time ?? (cell?.status === "ready" || cell?.status === "stale"
                    ? rsiRow?.source_time : cell?.bar_time)
                return [rsiDisplayStatus(cell, expired || !trackerQuoteFresh(rsiRow?.source_time, observedAt)),
                    rsiSourceTime(timestamp) ?? "", cell?.last?.source ?? cell?.closed_source ?? snapshot?.source ?? ""]
            }),
        ]
        lines.push(cells.map(csvEscape).join(","))
    }
    return `\uFEFF${lines.join("\r\n")}`
}
