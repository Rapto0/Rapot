"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { fetchServerWatchlists } from "@/lib/api/advanced-alarms-api"
import { fetchBistSymbols, fetchCryptoSymbols, fetchRsiSnapshot } from "@/lib/api/ops-api"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"
import { useMarketSnapshot } from "@/lib/hooks/use-market-snapshot"
import { useBinanceTickerFeed } from "@/lib/hooks/use-binance-ticker"
import {
    ALL_RSI_COLUMNS, RSI_PRESETS, RSI_TIMEFRAMES, TRACKER_PAGE_SIZE, TRACKER_REFRESH_MS, RSI_COLUMNS_STORAGE_KEY,
    buildTrackerCsv, parseTrackerUrlState, serializeTrackerUrlState, storedRsiColumns, summarizeRsiCells,
    trackerAlarmHref, trackerChartHref, trackerNumber, trackerPage, trackerPollInterval, trackerQuoteFresh, trackerResultRows,
    rsiDisplayStatus, rsiDisplayValue, rsiSourceTime, toggleRsiColumn,
    type RsiPreset, type RsiSnapshot, type RsiTimeframe, type TrackerMarket, type RsiFilter, type RsiSort,
} from "@/lib/rsi-tracker"
import { cn } from "@/lib/utils"

const control = "inline-flex min-h-11 items-center justify-center rounded border border-border px-3 text-xs transition-colors hover:bg-raised disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground"
const refreshPolicy = { refetchInterval: TRACKER_REFRESH_MS, staleTime: TRACKER_REFRESH_MS, retry: false }
const clock = new Intl.DateTimeFormat("tr-TR", { timeZone: "Europe/Istanbul", timeStyle: "medium" })
const timingMilestones = ["first-response", "first-price", "first-numeric-rsi", "first-usable-table"] as const

function useTrackerTiming(scope: string, response: boolean, price: boolean, hasRows: boolean, numeric: number, total: number) {
    useEffect(() => {
        const timeline = window.performance
        if (!timeline) return
        for (const milestone of timingMilestones) {
            timeline.clearMarks(`rapot.rsi.${milestone}`)
            timeline.clearMeasures(`rapot.rsi.${milestone}`)
        }
        timeline.clearMarks("rapot.rsi.scope")
        timeline.clearMarks("rapot.rsi.coverage")
        timeline.mark("rapot.rsi.scope")
    }, [scope])
    useEffect(() => {
        const timeline = window.performance
        if (!timeline || !total) return
        const record = () => {
            const reached = [response, price, hasRows && numeric > 0, price && numeric > 0]
            for (const [index, milestone] of timingMilestones.entries()) {
                const name = `rapot.rsi.${milestone}`
                if (reached[index] && !timeline.getEntriesByName(name, "mark").length) {
                    timeline.mark(name)
                    timeline.measure(name, "rapot.rsi.scope", name)
                }
            }
            timeline.clearMarks("rapot.rsi.coverage")
            timeline.mark("rapot.rsi.coverage", { detail: { numeric, total } })
        }
        const frame = window.requestAnimationFrame(record)
        return () => window.cancelAnimationFrame(frame)
    }, [scope, response, price, hasRows, numeric, total])
}

function useRsiClock(snapshot: RsiSnapshot | undefined, updatedAt: number) {
    const [clock, setClock] = useState({ updatedAt: 0, time: 0 })
    useEffect(() => {
        if (!snapshot?.observed_at || !updatedAt) return
        const observedAt = snapshot.observed_at
        const deadlines = Object.values(snapshot.rows).flatMap(row => row.source_time != null &&
            Object.values(row.cells).some(cell => cell.status === "ready") ? [row.source_time + 30.001] : [])
        if (!deadlines.length) return
        let timer: number
        const advance = () => {
            const now = observedAt + Math.max(0, Date.now() - updatedAt) / 1000
            setClock({ updatedAt, time: now })
            const next = Math.min(...deadlines.filter(at => at > now))
            if (Number.isFinite(next)) timer = window.setTimeout(advance, Math.ceil((next - now) * 1000))
        }
        const first = Math.min(...deadlines)
        timer = window.setTimeout(advance, Math.max(0, Math.ceil((first - observedAt) * 1000) - (Date.now() - updatedAt)))
        return () => window.clearTimeout(timer)
    }, [snapshot, updatedAt])
    return clock.updatedAt === updatedAt && updatedAt > 0 ? clock.time : snapshot?.observed_at ?? 0
}

export function RsiTracker() {
    const { allowed, sessionKey } = usePrivateMarket()
    const [market, setMarket] = useState<TrackerMarket>("BIST")
    const [search, setSearch] = useState("")
    const [descending, setDescending] = useState(false)
    const [page, setPage] = useState(0)
    const [columns, setColumns] = useState<RsiTimeframe[]>(() => [...ALL_RSI_COLUMNS])
    const [showColumns, setShowColumns] = useState(false)
    const [expiredRsiAt, setExpiredRsiAt] = useState(0)
    const [listId, setListId] = useState("")
    const [filters, setFilters] = useState<RsiFilter[]>([])
    const [sort, setSort] = useState<RsiSort | null>(null)
    const [preferencesLoaded, setPreferencesLoaded] = useState(false)
    const [view] = useState(() => typeof window === "undefined" ? "" : window.crypto.randomUUID())
    const [preparation] = useState(() => ({ scope: "", startedAt: 0 }))
    const symbolQuery = search.trim().toUpperCase()
    const symbols = useQuery({
        queryKey: ["rsi-tracker-symbols", sessionKey, market],
        queryFn: ({ signal }) => market === "BIST" ? fetchBistSymbols(signal) : fetchCryptoSymbols(signal),
        enabled: allowed, staleTime: 300_000, retry: false,
    })
    const watchlists = useQuery({
        queryKey: ["rsi-tracker-watchlists", sessionKey], queryFn: ({ signal }) => fetchServerWatchlists(signal),
        enabled: allowed, ...refreshPolicy,
    })
    const selectedList = watchlists.data?.watchlists.find(list => list.id === listId)
    const universe = useMemo(() => {
        if (!allowed) return []
        const available = symbols.data?.symbols ?? []
        if (!listId) return available
        const members = new Set(selectedList?.symbols.filter(item => item.market_type === market).map(item => item.symbol))
        return available.filter(symbol => members.has(symbol))
    }, [allowed, symbols.data, listId, selectedList, market])
    const visible = useMemo(() => trackerPage(universe, symbolQuery, descending, page),
        [universe, symbolQuery, descending, page])
    const tracked = visible.rows
    const bistSymbols = useMemo(() => allowed && market === "BIST" ? visible.rows.map(symbol => `${symbol}.IS`) : [], [allowed, market, visible.rows])
    const cryptoSymbols = useMemo(() => allowed && market === "Kripto" ? visible.rows : [], [allowed, market, visible.rows])
    const quotes = useMarketSnapshot(bistSymbols, TRACKER_REFRESH_MS)
    const crypto = useBinanceTickerFeed(cryptoSymbols, {
        paused: !allowed || market !== "Kripto", flushIntervalMs: TRACKER_REFRESH_MS, firstFlushMs: 800,
    })
    const shownColumns = RSI_TIMEFRAMES.filter(item => columns.includes(item.id))
    const columnGroups = [...new Set(shownColumns.map(item => item.group))]
    const rsiScope = JSON.stringify([market, tracked, columns])
    const rsi = useQuery({
        queryKey: ["rsi-tracker-values", sessionKey, view, market, tracked, columns],
        queryFn: ({ signal }) => {
            if (preparation.scope !== rsiScope) {
                preparation.scope = rsiScope
                preparation.startedAt = Date.now()
            }
            return fetchRsiSnapshot(view, market, tracked, columns, signal)
        },
        enabled: allowed && Boolean(view) && preferencesLoaded && !!symbols.data && (!listId || !!watchlists.data),
        refetchInterval: query => query.state.status === "error" ? TRACKER_REFRESH_MS
            : trackerPollInterval(query.state.data, preparation.startedAt, Date.now()),
        refetchIntervalInBackground: false, retry: false, staleTime: 0, gcTime: 20_000,
        // The view has one server lease. Returning to a cached page must register it again.
        refetchOnWindowFocus: query => query.state.dataUpdatedAt + TRACKER_REFRESH_MS <= Date.now(),
        refetchOnReconnect: true,
    })

    useEffect(() => {
        let initialColumns = [...ALL_RSI_COLUMNS]
        try { initialColumns = storedRsiColumns(window.localStorage.getItem(RSI_COLUMNS_STORAGE_KEY)) } catch { /* Storage may be disabled. */ }
        let urlState: Partial<ReturnType<typeof parseTrackerUrlState>> = {}
        try {
            if (typeof window.location?.search === "string" && window.location.search) {
                urlState = parseTrackerUrlState(window.location.search)
            }
        } catch { /* Ignore unavailable location search in non-browser harnesses. */ }
        if (urlState.market) setMarket(urlState.market)
        if (urlState.search !== undefined) setSearch(urlState.search)
        if (urlState.descending) setDescending(true)
        if (urlState.page !== undefined) setPage(urlState.page)
        if (urlState.listId !== undefined) setListId(urlState.listId)
        if (urlState.filters?.length) {
            const needed = new Set<RsiTimeframe>(initialColumns)
            for (const filter of urlState.filters) needed.add(filter.period)
            initialColumns = RSI_TIMEFRAMES.filter(item => needed.has(item.id)).map(item => item.id)
            setFilters(urlState.filters)
        }
        if (urlState.sort) {
            const needed = new Set<RsiTimeframe>(initialColumns)
            needed.add(urlState.sort.period)
            initialColumns = RSI_TIMEFRAMES.filter(item => needed.has(item.id)).map(item => item.id)
            setSort(urlState.sort)
        }
        setColumns(initialColumns)
        setPreferencesLoaded(true)
    }, [])
    useEffect(() => {
        if (!preferencesLoaded) return
        try {
            if (typeof window.history?.replaceState === "function" && typeof window.location?.pathname === "string") {
                const query = serializeTrackerUrlState({ market, search, descending, page, listId, filters, sort })
                const nextUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname
                const currentUrl = `${window.location.pathname}${window.location.search ?? ""}`
                if (nextUrl !== currentUrl) window.history.replaceState(null, "", nextUrl)
            }
        } catch { /* History synchronization is best-effort. */ }
    }, [preferencesLoaded, market, search, descending, page, listId, filters, sort])
    useEffect(() => {
        const updatedAt = rsi.dataUpdatedAt
        if (!updatedAt) return
        const deadline = updatedAt + TRACKER_REFRESH_MS + 15_000
        const timer = window.setTimeout(() => setExpiredRsiAt(updatedAt), Math.max(0, deadline - Date.now()))
        return () => window.clearTimeout(timer)
    }, [rsi.dataUpdatedAt])
    useEffect(() => {
        if (preferencesLoaded) {
            try { window.localStorage.setItem(RSI_COLUMNS_STORAGE_KEY, JSON.stringify(columns)) } catch { /* The current view still works. */ }
        }
    }, [columns, preferencesLoaded])

    const rsiStale = rsi.isError || rsi.isPaused || (expiredRsiAt > 0 && expiredRsiAt === rsi.dataUpdatedAt)
    const rsiTimedOut = rsi.error && "status" in rsi.error && rsi.error.status === 408
    const observedAt = useRsiClock(rsi.data, rsi.dataUpdatedAt)
    const resultRows = useMemo(() => trackerResultRows(tracked, rsi.data, filters, sort, !rsiStale, observedAt),
        [tracked, rsi.data, filters, sort, rsiStale, observedAt])
    const readiness = useMemo(() => summarizeRsiCells(tracked, rsi.data, columns, !rsiStale, observedAt), [tracked, rsi.data, columns, rsiStale, observedAt])
    const sessionEnded = market === "BIST" && tracked.length > 0 && tracked.every(symbol => rsi.data?.rows[symbol]?.session_ended)
    const hasPrice = resultRows.some(symbol => (market === "BIST" ? quotes.data?.[`${symbol}.IS`]?.value : crypto.prices[symbol]?.price) != null
        || rsi.data?.rows[symbol]?.last_price != null)
    useTrackerTiming(JSON.stringify([sessionKey, market, listId, symbolQuery, descending, page, columns]),
        rsi.isFetchedAfterMount && rsi.isSuccess, hasPrice, resultRows.length > 0, readiness.numeric, readiness.total)
    const filtering = filters.some(filter => filter.min.trim() || filter.max.trim())
    const skippedMembers = selectedList?.symbols.filter(item => item.market_type === market && !universe.includes(item.symbol)).length ?? 0
    const fetching = symbols.isFetching || watchlists.isFetching || rsi.isFetching || (market === "BIST" && quotes.isFetching)
    const lastUpdated = rsi.dataUpdatedAt > 0 && tracked.length > 0 ? clock.format(rsi.dataUpdatedAt) : null

    if (!allowed) return <p className="p-4 text-sm">Takipçi için yönetici girişi gerekir.</p>

    const switchMarket = (value: TrackerMarket) => {
        if (value === market) return
        setMarket(value); setSearch(""); setPage(0)
    }
    const resetView = () => { setSearch(""); setDescending(false); setPage(0); setColumns([...ALL_RSI_COLUMNS]); setFilters([]); setSort(null) }
    const chooseColumns = (next: RsiTimeframe[]) => {
        setColumns(next)
        setFilters(previous => previous.filter(filter => next.includes(filter.period)))
        setSort(previous => previous && next.includes(previous.period) ? previous : null)
    }
    const updateFilter = (index: number, change: Partial<RsiFilter>) => {
        setFilters(previous => previous.map((filter, position) => position === index ? { ...filter, ...change } : filter))
    }
    const applyPreset = (preset: RsiPreset) => {
        const needed = new Set<RsiTimeframe>(columns)
        for (const filter of preset.filters) needed.add(filter.period)
        needed.add(preset.sort.period)
        const nextColumns = RSI_TIMEFRAMES.filter(item => needed.has(item.id)).map(item => item.id)
        if (nextColumns.length !== columns.length) setColumns(nextColumns)
        setFilters(preset.filters.map(item => ({ ...item })))
        setSort({ ...preset.sort })
    }
    const exportCsv = () => {
        const pricesBySymbol: Record<string, { price?: number | null; change?: number | null }> = {}
        for (const symbol of resultRows) {
            const lastPrice = rsi.data?.rows[symbol]?.last_price?.value
            if (market === "BIST") {
                const quote = quotes.data?.[`${symbol}.IS`]
                pricesBySymbol[symbol] = { price: quote?.value ?? lastPrice, change: quote?.value != null ? quote.change : null }
            } else {
                const tick = crypto.prices[symbol]
                pricesBySymbol[symbol] = { price: tick?.price ?? lastPrice, change: tick?.change }
            }
        }
        const csv = buildTrackerCsv(resultRows, market, pricesBySymbol, rsi.data, columns, rsiStale, observedAt)
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement("a")
        anchor.href = url
        anchor.download = `rapot-rsi-${market.toLowerCase()}-s${visible.page + 1}.csv`
        anchor.click()
        URL.revokeObjectURL(url)
    }
    const sourceLabel = market === "BIST" ? "Borsa İstanbul · TRY" : "Binance Spot · USDT"
    const refresh = () => {
        void symbols.refetch()
        void watchlists.refetch()
        if (view && preferencesLoaded && symbols.data && (!listId || watchlists.data)) void rsi.refetch()
        if (market === "BIST" && bistSymbols.length) void quotes.refetch()
        if (market === "Kripto") crypto.flush()
    }

    return <section aria-label="RSI takipçisi" className="min-w-0 overflow-hidden rounded border border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-raised/35 px-4 py-3">
            <div className="flex rounded border border-border bg-background p-1" role="group" aria-label="Takip edilecek piyasa">
                {(["BIST", "Kripto"] as const).map(value => <button key={value} type="button" aria-pressed={market === value} onClick={() => switchMarket(value)} className={cn("min-h-11 rounded px-5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-foreground", market === value ? "bg-foreground text-background" : "text-muted-foreground hover:bg-raised")}>{value === "BIST" ? "Hisseler" : "Kripto"}</button>)}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="font-medium text-foreground">{sourceLabel}</span>
                <span>RSI (14) · Kapanış</span>
                {sessionEnded && <span className="text-neutral">BIST seansı kapalı</span>}
                <span>Normal yenileme · {TRACKER_REFRESH_MS / 1000} sn</span>
                {tracked.length > 0 && <span className="tabular-nums" title="Son RSI yanıtının ekran alım saati">{lastUpdated ? `Son yenileme ${lastUpdated} TSİ` : "İlk RSI verisi bekleniyor"}</span>}
            </div>
        </div>

        <div className="flex flex-wrap items-end gap-3 border-b border-border bg-background/40 p-4">
            <label className="min-w-32 flex-1 space-y-1 text-xs sm:max-w-80"><span className="text-muted-foreground">Sembol ara</span><input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(0) }} placeholder={market === "BIST" ? "Örn. THYAO" : "Örn. BTCUSDT"} className="min-h-11 w-full rounded border border-border bg-background px-3 text-base outline-offset-2 sm:text-sm" /></label>
            <label className="min-w-0 space-y-1 text-xs"><span className="block text-muted-foreground">İzleme listesi</span><select aria-label="İzleme listesi" value={listId} onChange={event => { setListId(event.target.value); setPage(0) }} className="min-h-11 w-full max-w-56 rounded border border-border bg-background px-3 text-base sm:text-xs"><option value="">Tüm semboller</option>{watchlists.data?.watchlists.map(list => <option key={list.id} value={list.id}>{list.name}</option>)}</select></label>
            <button type="button" className={control} aria-label={`Sembol sıralaması: ${descending ? "Z–A" : "A–Z"}`} onClick={() => { setDescending(value => !value); setPage(0) }}>Sembol {descending ? "↓ Z–A" : "↑ A–Z"}</button>
            <button type="button" className={cn(control, showColumns && "bg-raised")} aria-expanded={showColumns} aria-controls="rsi-column-picker" onClick={() => setShowColumns(value => !value)}>RSI sütunları <span className="ml-2 rounded bg-raised px-1.5 py-0.5 font-mono">{columns.length}/16</span></button>
            <button type="button" className={control} disabled={!resultRows.length} onClick={exportCsv}>CSV indir</button>
            <button type="button" className={cn(control, "bg-foreground/5 font-semibold")} disabled={fetching} onClick={refresh}>{fetching ? "Yenileniyor…" : "Yenile"}</button>
        </div>

        {showColumns && <div id="rsi-column-picker" className="border-b border-border bg-raised/30 p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><p className="text-xs text-muted-foreground">Görmek istediğiniz zaman dilimlerini seçin. En az bir sütun açık kalır.</p><div className="flex gap-2"><button type="button" className={control} onClick={() => setColumns([...ALL_RSI_COLUMNS])}>Tüm sütunlar</button><button type="button" className={control} onClick={resetView}>Görünümü sıfırla</button></div></div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
                {["Dakika", "Saat", "Gün", "Hafta", "Ay"].map(group => <fieldset key={group} className="min-w-0"><legend className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</legend><div className="flex flex-wrap gap-2">{RSI_TIMEFRAMES.filter(item => item.group === group).map(item => <label key={item.id} className={cn("inline-flex min-h-11 cursor-pointer items-center gap-2 rounded border px-3 text-xs", columns.includes(item.id) ? "border-foreground/30 bg-raised" : "border-border text-muted-foreground")}><input type="checkbox" checked={columns.includes(item.id)} disabled={columns.length === 1 && columns.includes(item.id)} onChange={() => chooseColumns(toggleRsiColumn(columns, item.id))} aria-label={`RSI ${item.label} sütunu`} className="accent-foreground" /><span>{item.label}</span></label>)}</div></fieldset>)}
            </div>
        </div>}

        {(watchlists.isError || (listId && !selectedList && !watchlists.isPending) || skippedMembers > 0 || rsiStale) && <div className="space-y-2 border-b border-border bg-neutral/5 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
            {watchlists.isError && <p role="alert">İzleme listeleri yenilenemedi. {selectedList ? "Son alınan liste kullanılıyor." : "Liste seçimi için yeniden deneyin."}</p>}
            {listId && !selectedList && !watchlists.isPending && <p role="status">Seçilen izleme listesi bulunamadı.</p>}
            {skippedMembers > 0 && <p>{skippedMembers} liste üyesi bu piyasanın desteklenen sembol listesinde bulunmuyor.</p>}
            {rsiStale && <p role="status">{rsiTimedOut ? "RSI isteği zaman aşımına uğradı." : "RSI yenilemesi bekleniyor."} Varsa son alınan değerler tabloda gösteriliyor.</p>}
        </div>}

        <div className="space-y-3 border-b border-border px-4 py-3 text-xs" aria-label="Sayfadaki RSI koşulları">
            <div className="flex flex-wrap items-center gap-2">
                <button type="button" className={control} disabled={filters.length >= columns.length} onClick={() => {
                    const period = columns.find(item => !filters.some(filter => filter.period === item))
                    if (period) setFilters(previous => [...previous, { period, min: "", max: "" }])
                }}>RSI koşulu ekle</button>
                {RSI_PRESETS.map(preset => <button key={preset.id} type="button" className={control} onClick={() => applyPreset(preset)}>{preset.label}</button>)}
                {(filters.length > 0 || sort) && <button type="button" className={control} onClick={() => { setFilters([]); setSort(null) }}>RSI koşullarını temizle</button>}
                <span className="text-muted-foreground">Koşul ve RSI sıralaması bu sayfaya uygulanır.</span>
            </div>
            {filters.map((filter, index) => <div key={index} className="flex flex-wrap items-end gap-2">
                <label className="space-y-1"><span className="block">Zaman dilimi</span><select aria-label={`RSI koşulu ${index + 1} zaman dilimi`} className={cn(control, "bg-background")} value={filter.period} onChange={event => updateFilter(index, { period: event.target.value as RsiTimeframe })}>{shownColumns.filter(item => item.id === filter.period || !filters.some(other => other.period === item.id)).map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>
                <label className="space-y-1"><span className="block">En az</span><input aria-label={`RSI koşulu ${index + 1} en az`} className="min-h-11 w-24 rounded border border-border bg-background px-3 text-base sm:text-xs" type="number" min="0" max="100" step="any" value={filter.min} onChange={event => updateFilter(index, { min: event.target.value })} placeholder="0" /></label>
                <label className="space-y-1"><span className="block">En çok</span><input aria-label={`RSI koşulu ${index + 1} en çok`} className="min-h-11 w-24 rounded border border-border bg-background px-3 text-base sm:text-xs" type="number" min="0" max="100" step="any" value={filter.max} onChange={event => updateFilter(index, { max: event.target.value })} placeholder="100" /></label>
                <button type="button" className={control} aria-label={`RSI koşulu ${index + 1} kaldır`} onClick={() => setFilters(previous => previous.filter((_, position) => position !== index))}>Kaldır</button>
            </div>)}
            {filtering && <p role="status">{resultRows.length} / {tracked.length} sembol bütün RSI koşullarını karşılıyor. Diğer sayfalar değerlendirilmedi.</p>}
        </div>

        {readiness.total > 0 && <div className="space-y-1.5 border-b border-border bg-background/30 px-4 py-2.5 text-xs" aria-label="RSI hazırlık özeti">
            <div className="flex flex-wrap items-center justify-between gap-2 text-muted-foreground">
                <span className="tabular-nums">
                    <strong className="text-foreground">{readiness.numeric} / {readiness.total}</strong> hücre sayısal
                    {readiness.ready > 0 ? ` (${readiness.ready} güncel)` : ""}
                    {readiness.retained > 0 ? ` · ${readiness.retained} son kayıt` : ""}
                    {readiness.stale > 0 ? ` · ${readiness.stale} güncelliğini yitirmiş` : ""}
                    {readiness.waiting > 0 ? ` · ${readiness.waiting} hazırlanıyor` : ""}
                    {readiness.insufficient > 0 ? ` · ${readiness.insufficient} yetersiz geçmiş` : ""}
                </span>
                <span className="mono-numbers text-[11px]">{readiness.percent}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised" role="progressbar" aria-label="Sayfa RSI hazırlık oranı" aria-valuenow={readiness.percent} aria-valuemin={0} aria-valuemax={100}>
                <div className={cn("h-full transition-all", readiness.waiting === 0 ? "bg-profit" : "bg-neutral")} style={{ width: `${readiness.percent}%` }} />
            </div>
        </div>}

        {symbols.isError && <div role="alert" className="border-b border-border px-4 py-3 text-xs text-neutral">Sembol listesi alınamadı. {visible.total ? "Son alınan liste gösteriliyor; güncel olmayabilir." : "Yenile düğmesiyle tekrar deneyebilirsiniz."}</div>}
        {market === "BIST" && quotes.isError && visible.rows.length > 0 && <p role="alert" className="border-b border-border px-4 py-3 text-xs text-neutral">Fiyatlar yenilenemedi. Son alınan kayıtlar güncel olmayabilir.</p>}

        <div className="relative max-h-[min(64vh,42rem)] min-h-48 overflow-auto overscroll-contain focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-foreground" role="region" aria-label="Semboller ve RSI zaman dilimleri tablosu" tabIndex={0}>
            <table className="w-full border-separate border-spacing-0 text-xs">
                <caption className="sr-only">{market === "BIST" ? "BIST hisseleri" : "Binance USDT çiftleri"}. Fiyat ve {shownColumns.length} RSI zaman dilimi.</caption>
                <colgroup span={3} />
                {columnGroups.map(group => <colgroup key={group} span={shownColumns.filter(item => item.group === group).length} />)}
                <thead className="sticky top-0 z-20 bg-raised">
                    <tr>
                        <th rowSpan={2} scope="col" aria-sort={!sort ? descending ? "descending" : "ascending" : undefined} className="sticky left-0 z-30 min-w-32 border-b border-r border-border bg-raised px-3 text-left font-medium sm:min-w-36">Sembol</th>
                        <th rowSpan={2} scope="col" className="min-w-28 border-b border-border px-3 text-right font-medium">Son fiyat <span className="block text-[10px] font-normal text-muted-foreground">{market === "BIST" ? "TRY" : "USDT"}</span></th>
                        <th rowSpan={2} scope="col" className="min-w-24 border-b border-border px-3 text-right font-medium">Değişim <span className="block text-[10px] font-normal text-muted-foreground">{market === "BIST" ? "Günlük" : "24 saat"}</span></th>
                        {columnGroups.map(group => <th key={group} scope="colgroup" colSpan={shownColumns.filter(item => item.group === group).length} className="border-b border-l border-border bg-background/40 px-2 py-1.5 text-center text-[10px] font-medium tracking-wide text-muted-foreground">{group}</th>)}
                    </tr>
                    <tr>
                        {shownColumns.map(item => <th key={item.id} scope="col" aria-label={`RSI ${item.label}`} aria-sort={sort?.period === item.id ? sort.descending ? "descending" : "ascending" : undefined} title={`RSI · ${item.label}`} className={cn("min-w-20 border-b border-l border-border px-2 text-right font-medium", sort?.period === item.id && "bg-foreground/8")}><button type="button" className="min-h-9 w-full whitespace-nowrap text-right focus-visible:outline-foreground" aria-label={`Bu sayfayı RSI ${item.label} değerine göre sırala`} onClick={() => setSort(previous => ({ period: item.id, descending: previous?.period === item.id ? !previous.descending : false }))}>{item.short}{sort?.period === item.id && (sort.descending ? " ↓" : " ↑")}</button></th>)}
                    </tr>
                </thead>
                <tbody>
                    {!visible.rows.length && <tr><td colSpan={3 + shownColumns.length} className="h-44 px-5 py-8 text-center text-muted-foreground"><p className="text-sm font-medium">{symbols.isPending ? "Semboller yükleniyor…" : symbols.isError ? "Sembol listesine erişilemiyor" : search ? "Aramanızla eşleşen sembol yok" : "Bu piyasa için sembol listesi alınamadı"}</p><p className="mt-2 text-xs">{search && !symbols.isError ? "Başka bir sembol arayın veya aramayı temizleyin." : !symbols.isPending && !symbols.isError ? "Kaynak boş bir liste döndürdü. Daha sonra yenileyebilirsiniz." : ""}</p></td></tr>}
                    {visible.rows.length > 0 && !resultRows.length && <tr><td colSpan={3 + shownColumns.length} className="h-32 px-5 py-8 text-center text-muted-foreground">Bu sayfada güncel RSI koşullarını karşılayan sembol yok. Hazırlanan değerler geldikçe sonuç güncellenir.</td></tr>}
                    {resultRows.map(symbol => {
                        const quote = quotes.data?.[`${symbol}.IS`]
                        const tick = crypto.prices[symbol]
                        const bist = market === "BIST"
                        const rsiRow = rsi.data?.rows[symbol]
                        const lastPrice = rsiRow?.last_price
                        const marketPrice = bist ? quote?.value : tick?.price
                        const price = marketPrice ?? lastPrice?.value
                        const change = marketPrice == null ? null : bist ? quote?.change : tick?.change
                        const received = crypto.receivedAtBySymbol[symbol]
                        const stale = marketPrice == null || (bist ? quotes.isError || quotes.isPaused || (quote?.state !== undefined && quote.state !== "ok")
                            : crypto.status !== "connected" || !received)
                        const rsiPriceTime = rsiSourceTime(rsiRow?.source_time)
                        const lastRsi = rsiStale || !trackerQuoteFresh(rsiRow?.source_time, observedAt)
                        const priceTime = marketPrice == null ? [rsiSourceTime(lastPrice?.source_time), lastPrice?.source].filter(Boolean).join(" · ")
                            : bist ? [quote?.provider_time, quote?.message].filter(Boolean).join(" · ")
                            : received ? `Akış alımı ${clock.format(received)} TSİ` : undefined
                        return <tr key={`${market}:${symbol}`} className="group even:bg-raised/30 hover:bg-raised/70">
                            <th scope="row" className="sticky left-0 z-10 border-b border-r border-border bg-surface px-3 text-left group-hover:bg-raised">
                                <div className="flex items-center justify-between gap-2">
                                    <Link href={trackerChartHref(symbol, market)} className="inline-flex min-h-10 items-center gap-1.5 font-semibold underline-offset-4 hover:underline focus-visible:underline" aria-label={`${symbol} grafiğini aç`}>{symbol}<span aria-hidden="true" className="text-muted-foreground">↗</span></Link>
                                    <Link href={trackerAlarmHref(symbol, market)} className="inline-flex min-h-9 items-center rounded border border-border/70 px-1.5 text-[10px] font-normal text-muted-foreground hover:bg-background hover:text-foreground" aria-label={`${symbol} için alarm taslağı oluştur`} title="Sunucu alarmı taslağı">Alarm</Link>
                                </div>
                            </th>
                            <td className="border-b border-border px-3 py-2 text-right" title={priceTime || undefined}><span className="block font-mono text-sm tabular-nums">{trackerNumber(price)}</span>{price != null && stale && <span className="block text-[10px] text-neutral">{marketPrice == null && lastPrice?.kind === "closed" ? "Son kapanış" : "Son kayıt"}</span>}</td>
                            <td className={cn("border-b border-border px-4 py-3 text-right font-mono tabular-nums", change == null || !Number.isFinite(change) ? "text-muted-foreground" : change >= 0 ? "text-profit" : "text-loss")}>{trackerNumber(change)}{change != null && Number.isFinite(change) ? "%" : ""}</td>
                            {shownColumns.map(item => {
                                const cell = rsiRow?.cells[item.id]
                                const cellStatus = rsiDisplayStatus(cell, lastRsi)
                                const timestamp = cell?.last ? rsiSourceTime(cell.last.bar_end ?? cell.last.bar_time)
                                    : cell?.status === "ready" || cell?.status === "stale" ? rsiPriceTime : rsiSourceTime(cell?.bar_time)
                                const acquired = rsiSourceTime(cell?.last?.received_at ?? cell?.received_at)
                                const cellSource = cell?.last?.source ?? cell?.closed_source
                                const value = rsiDisplayValue(cell)?.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) ?? "—"
                                const priceLabel = (cell?.status === "ready" || cell?.status === "stale") && rsiRow?.price != null
                                    ? `Hesaplanan fiyat ${trackerNumber(rsiRow.price)}` : null
                                const tint = cell?.status === "ready" && !lastRsi && cell.value != null
                                    ? cell.value <= 30 ? "bg-sky-500/12 text-sky-200" : cell.value >= 70 ? "bg-amber-500/12 text-amber-200" : "text-foreground"
                                    : "text-muted-foreground"
                                return <td key={item.id} className={cn("border-b border-l border-border/60 px-3 py-2 text-right", tint)} title={[cellStatus, timestamp && `Veri ${timestamp} TSİ`, acquired && `Alım ${acquired} TSİ`, cellSource && `Kaynak ${cellSource}`, priceLabel].filter(Boolean).join(" · ")}>
                                    <span className="block font-mono text-sm tabular-nums">{value}</span>
                                    <span className={cell?.status === "ready" && !lastRsi ? "sr-only" : "block text-[10px] leading-tight"}>{cellStatus}</span>
                                </td>
                            })}
                        </tr>
                    })}
                </tbody>
            </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border p-4"><p className="text-[11px] text-muted-foreground">{visible.matched ? `${visible.page * TRACKER_PAGE_SIZE + 1}–${Math.min((visible.page + 1) * TRACKER_PAGE_SIZE, visible.matched)} / ${visible.matched}` : "0 sembol"} · Sayfa başına {TRACKER_PAGE_SIZE} sembol</p><nav aria-label="Takipçi sayfaları" className="flex items-center gap-3"><button type="button" className={control} disabled={visible.page === 0} onClick={() => setPage(visible.page - 1)}>Önceki</button><span className="font-mono text-xs">{visible.page + 1} / {visible.pages}</span><button type="button" className={control} disabled={visible.page + 1 >= visible.pages} onClick={() => setPage(visible.page + 1)}>Sonraki</button></nav></div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
            <span>RSI kaynağı · {market === "BIST" ? "Borsapy / BIST" : "TradingView / Binance"}</span>
            {rsi.data?.closed_source && <span>Kapanış kaynağı · {rsi.data.closed_source}</span>}
            <span className="text-sky-300">RSI ≤ 30</span><span className="text-amber-300">RSI ≥ 70</span>
        </div>
    </section>
}
