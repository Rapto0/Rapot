import type { AlarmSymbol } from "./api/advanced-alarms-api"

export const WATCHLIST_PAGE_SIZE = 50

/** A named server list is a live membership reference, never a copied alarm scope. */
export function serverWatchlistHref(id: string, view: "alarm" | "detail" | "chart" = "alarm") {
    const query = `serverList=${encodeURIComponent(id)}`
    return view === "chart" ? `/chart?${query}` : `/alarms?${query}${view === "alarm" ? "&action=new" : ""}`
}

export function serverWatchlistPage(symbols: readonly AlarmSymbol[], requestedPage: number) {
    const pages = Math.max(1, Math.ceil(symbols.length / WATCHLIST_PAGE_SIZE))
    const page = Math.min(pages - 1, Math.max(0, Number.isFinite(requestedPage) ? Math.floor(requestedPage) : 0))
    const rows = symbols.slice(page * WATCHLIST_PAGE_SIZE, (page + 1) * WATCHLIST_PAGE_SIZE)
    return {
        page, pages, rows,
        bist: rows.filter(row => row.market_type === "BIST").map(row => `${row.symbol}.IS`),
        crypto: rows.filter(row => row.market_type === "Kripto").map(row => row.symbol),
    }
}
