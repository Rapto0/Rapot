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

export function trackerNumber(value: number | undefined | null): string {
    return typeof value === "number" && Number.isFinite(value)
        ? value.toLocaleString("tr-TR", { maximumFractionDigits: 5 }) : "—"
}
