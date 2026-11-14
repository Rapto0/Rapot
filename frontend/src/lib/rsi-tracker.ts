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
export const ALL_RSI_COLUMNS: RsiTimeframe[] = RSI_TIMEFRAMES.map(item => item.id)

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
