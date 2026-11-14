"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { fetchBistSymbols, fetchCryptoSymbols, fetchRsiSnapshot } from "@/lib/api/ops-api"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"
import { useMarketSnapshot } from "@/lib/hooks/use-market-snapshot"
import { useBinanceTickerFeed } from "@/lib/hooks/use-binance-ticker"
import { ALL_RSI_COLUMNS, RSI_CELL_STATUS, RSI_TIMEFRAMES, TRACKER_PAGE_SIZE, TRACKER_SYMBOL_LIMIT, rsiSourceTime, toggleRsiColumn,
    trackerChartHref, trackerNumber, trackerPage, type RsiTimeframe, type TrackerMarket } from "@/lib/rsi-tracker"
import { cn } from "@/lib/utils"

const control = "inline-flex min-h-11 items-center justify-center rounded border border-border px-3 text-xs transition-colors hover:bg-raised disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-foreground"

export function RsiTracker() {
    const { allowed, sessionKey } = usePrivateMarket()
    const [market, setMarket] = useState<TrackerMarket>("BIST")
    const [search, setSearch] = useState("")
    const [descending, setDescending] = useState(false)
    const [page, setPage] = useState(0)
    const [columns, setColumns] = useState<RsiTimeframe[]>(() => [...ALL_RSI_COLUMNS])
    const [showColumns, setShowColumns] = useState(false)
    const [now, setNow] = useState(0)
    const [tracked, setTracked] = useState<string[]>([])
    const [view, setView] = useState("")
    const symbols = useQuery({
        queryKey: ["rsi-tracker-symbols", sessionKey, market],
        queryFn: ({ signal }) => market === "BIST" ? fetchBistSymbols(signal) : fetchCryptoSymbols(signal),
        enabled: allowed, staleTime: 300_000, retry: false,
    })
    const visible = useMemo(() => trackerPage(allowed ? symbols.data?.symbols : [], search, descending, page),
        [allowed, symbols.data, search, descending, page])
    const bistSymbols = useMemo(() => allowed && market === "BIST" ? visible.rows.map(symbol => `${symbol}.IS`) : [], [allowed, market, visible.rows])
    const cryptoSymbols = useMemo(() => allowed && market === "Kripto" ? visible.rows : [], [allowed, market, visible.rows])
    const quotes = useMarketSnapshot(bistSymbols)
    const crypto = useBinanceTickerFeed(cryptoSymbols, { paused: !allowed || market !== "Kripto", flushIntervalMs: 500 })
    const shownColumns = RSI_TIMEFRAMES.filter(item => columns.includes(item.id))
    const rsi = useQuery({
        queryKey: ["rsi-tracker-values", sessionKey, view, market, tracked, columns],
        queryFn: ({ signal }) => fetchRsiSnapshot(view, market, tracked, columns, signal),
        enabled: allowed && Boolean(view) && tracked.length > 0,
        refetchInterval: 3_000, retry: false, gcTime: 20_000,
        refetchOnWindowFocus: true, refetchOnReconnect: true,
    })

    useEffect(() => {
        const timer = window.setInterval(() => setNow(Date.now()), 3_000)
        return () => window.clearInterval(timer)
    }, [])

    if (!allowed) return <p className="p-4 text-sm">Takipçi için yönetici girişi gerekir.</p>

    const switchMarket = (value: TrackerMarket) => {
        if (value === market) return
        setMarket(value); setSearch(""); setPage(0); setTracked([])
    }
    const toggleSymbol = (symbol: string) => {
        if (!view) setView(window.crypto.randomUUID())
        setTracked(previous => previous.includes(symbol) ? previous.filter(item => item !== symbol)
            : previous.length < TRACKER_SYMBOL_LIMIT ? [...previous, symbol] : previous)
    }
    const resetView = () => { setSearch(""); setDescending(false); setPage(0); setColumns([...ALL_RSI_COLUMNS]) }
    const sourceLabel = market === "BIST" ? "Borsa İstanbul · TRY" : "Binance Spot · USDT"

    return <section aria-label="RSI takipçisi" className="min-w-0 overflow-hidden rounded border border-border bg-surface">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4">
            <div className="space-y-2">
                <div className="flex flex-wrap items-center gap-3"><h2 className="text-lg font-semibold tracking-tight">RSI takipçisi</h2><span className="rounded border border-border px-2 py-1 text-[10px] text-muted-foreground">{sourceLabel}</span></div>
                <p className="text-xs text-muted-foreground">Bir sembol, tüm zaman dilimleri.</p>
            </div>
            <div className="flex rounded border border-border bg-background p-1" role="group" aria-label="Takip edilecek piyasa">
                {(["BIST", "Kripto"] as const).map(value => <button key={value} type="button" aria-pressed={market === value} onClick={() => switchMarket(value)} className={cn("min-h-11 rounded px-5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-foreground", market === value ? "bg-foreground text-background" : "text-muted-foreground hover:bg-raised")}>{value === "BIST" ? "Hisseler" : "Kripto"}</button>)}
            </div>
        </div>

        <div className="flex flex-wrap items-end gap-3 border-b border-border bg-background/40 p-4">
            <label className="min-w-0 flex-1 space-y-1 text-xs sm:max-w-80"><span className="text-muted-foreground">Sembol ara</span><input type="search" value={search} onChange={event => { setSearch(event.target.value); setPage(0) }} placeholder={market === "BIST" ? "Örn. THYAO" : "Örn. BTCUSDT"} className="min-h-11 w-full rounded border border-border bg-background px-3 text-sm outline-offset-2" /></label>
            {search && <button type="button" className={control} onClick={() => { setSearch(""); setPage(0) }}>Aramayı temizle</button>}
            <button type="button" className={control} aria-label={`Sembol sıralaması: ${descending ? "Z–A" : "A–Z"}`} onClick={() => { setDescending(value => !value); setPage(0) }}>Sembol {descending ? "↓ Z–A" : "↑ A–Z"}</button>
            <button type="button" className={cn(control, showColumns && "bg-raised")} aria-expanded={showColumns} aria-controls="rsi-column-picker" onClick={() => setShowColumns(value => !value)}>RSI sütunları <span className="ml-2 rounded bg-raised px-1.5 py-0.5 font-mono">{columns.length}/16</span></button>
            <button type="button" className={control} disabled={symbols.isFetching} onClick={() => { void symbols.refetch(); if (market === "BIST" && bistSymbols.length) void quotes.refetch(); else if (market === "Kripto") crypto.reconnect() }}>{symbols.isFetching ? "Yükleniyor…" : "Yenile"}</button>
        </div>

        {showColumns && <div id="rsi-column-picker" className="border-b border-border bg-raised/30 p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2"><p className="text-xs text-muted-foreground">Görmek istediğiniz zaman dilimlerini seçin. En az bir sütun açık kalır.</p><div className="flex gap-2"><button type="button" className={control} onClick={() => setColumns([...ALL_RSI_COLUMNS])}>Tüm sütunlar</button><button type="button" className={control} onClick={resetView}>Görünümü sıfırla</button></div></div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
                {["Dakika", "Saat", "Gün", "Hafta", "Ay"].map(group => <fieldset key={group} className="min-w-0"><legend className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</legend><div className="flex flex-wrap gap-2">{RSI_TIMEFRAMES.filter(item => item.group === group).map(item => <label key={item.id} className={cn("inline-flex min-h-11 cursor-pointer items-center gap-2 rounded border px-3 text-xs", columns.includes(item.id) ? "border-foreground/30 bg-raised" : "border-border text-muted-foreground")}><input type="checkbox" checked={columns.includes(item.id)} disabled={columns.length === 1 && columns.includes(item.id)} onChange={() => setColumns(value => toggleRsiColumn(value, item.id))} aria-label={`RSI ${item.label} sütunu`} className="accent-foreground" /><span>{item.label}</span></label>)}</div></fieldset>)}
            </div>
        </div>}

        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3 text-xs"><p><span className="font-semibold">{visible.matched.toLocaleString("tr-TR")}</span> <span className="text-muted-foreground">{search ? `/ ${visible.total.toLocaleString("tr-TR")} sembol eşleşti` : "sembol"}</span></p><span className="text-muted-foreground">RSI · {shownColumns.length} zaman dilimi</span></div>
        <div className="space-y-2 border-b border-border bg-neutral/5 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
            <p><span className="font-medium text-foreground">RSI (14) · Kapanış</span> · İki sembole kadar RSI takibi açabilirsin. {market === "BIST" ? "Kaynak: Borsapy / BIST." : "RSI kaynağı: TradingView / Binance Spot."}</p>
            {tracked.length > 0 && <div className="flex flex-wrap gap-2" aria-label="RSI takibi açık semboller">
                {tracked.map(symbol => <button key={symbol} type="button" className={control} aria-label={`${symbol} RSI takibini kapat`} onClick={() => toggleSymbol(symbol)}>{symbol} ×</button>)}
            </div>}
            {rsi.isError && <p role="alert">RSI verisi yenilenemedi. Akış yeniden deneniyor.</p>}
        </div>

        {symbols.isError && <div role="alert" className="border-b border-border px-4 py-3 text-xs text-neutral">Sembol listesi alınamadı. {visible.total ? "Son alınan liste gösteriliyor; güncel olmayabilir." : "Yenile düğmesiyle tekrar deneyebilirsiniz."}</div>}
        {market === "BIST" && quotes.isError && visible.rows.length > 0 && <p role="alert" className="border-b border-border px-4 py-3 text-xs text-neutral">Fiyatlar yenilenemedi. Son alınan kayıtlar güncel olmayabilir.</p>}

        <div className="max-h-[38rem] overflow-auto overscroll-contain" role="region" aria-label="Semboller ve RSI zaman dilimleri tablosu" tabIndex={0}>
            <table className="w-full border-separate border-spacing-0 text-xs">
                <caption className="sr-only">{market === "BIST" ? "BIST hisseleri" : "Binance USDT çiftleri"}. Fiyat ve {shownColumns.length} RSI zaman dilimi.</caption>
                <thead className="sticky top-0 z-20 bg-raised"><tr>
                    <th scope="col" aria-sort={descending ? "descending" : "ascending"} className="sticky left-0 z-30 min-w-36 border-b border-r border-border bg-raised px-4 py-3 text-left font-medium">Sembol</th>
                    <th scope="col" className="min-w-36 border-b border-border px-4 py-3 text-right font-medium">Son fiyat <span className="block text-[10px] font-normal text-muted-foreground">{market === "BIST" ? "TRY" : "USDT"}</span></th>
                    <th scope="col" className="min-w-28 border-b border-border px-4 py-3 text-right font-medium">Değişim <span className="block text-[10px] font-normal text-muted-foreground">{market === "BIST" ? "Günlük" : "24 saat"}</span></th>
                    {shownColumns.map(item => <th key={item.id} scope="col" aria-label={`RSI ${item.label}`} title={`RSI · ${item.label}`} className="min-w-24 border-b border-l border-border px-3 py-3 text-right font-medium"><span className="block text-[9px] font-normal tracking-wide text-muted-foreground">RSI</span>{item.short}</th>)}
                </tr></thead>
                <tbody>
                    {!visible.rows.length && <tr><td colSpan={3 + shownColumns.length} className="h-44 px-5 py-8 text-center text-muted-foreground"><p className="text-sm font-medium">{symbols.isPending ? "Semboller yükleniyor…" : symbols.isError ? "Sembol listesine erişilemiyor" : search ? "Aramanızla eşleşen sembol yok" : "Bu piyasa için sembol listesi alınamadı"}</p><p className="mt-2 text-xs">{search && !symbols.isError ? "Başka bir sembol arayın veya aramayı temizleyin." : !symbols.isPending && !symbols.isError ? "Kaynak boş bir liste döndürdü. Daha sonra yenileyebilirsiniz." : ""}</p></td></tr>}
                    {visible.rows.map(symbol => {
                        const quote = quotes.data?.[`${symbol}.IS`]
                        const tick = crypto.prices[symbol]
                        const bist = market === "BIST"
                        const price = bist ? quote?.value : tick?.price
                        const change = bist ? quote?.change : tick?.change
                        const received = crypto.receivedAtBySymbol[symbol]
                        const stale = bist ? quotes.isError || (quote?.state !== undefined && quote.state !== "ok") || (now > 0 && quotes.dataUpdatedAt > 0 && now - quotes.dataUpdatedAt >= 30_000)
                            : crypto.status !== "connected" || !received || (now > 0 && now - received >= 30_000)
                        const available = typeof price === "number" && Number.isFinite(price)
                        const status = !available ? "Fiyat bekleniyor" : stale ? "Son kayıt · güncel olmayabilir" : bist ? "Son alınan fiyat" : "Akış alınıyor"
                        const follows = tracked.includes(symbol)
                        const rsiRow = follows ? rsi.data?.rows[symbol] : undefined
                        const rsiPriceTime = rsiSourceTime(rsiRow?.source_time)
                        const rsiStale = rsi.isError || (now > 0 && rsi.dataUpdatedAt > 0 && now - rsi.dataUpdatedAt > 10_000)
                        return <tr key={`${market}:${symbol}`} className="group hover:bg-raised/50">
                            <th scope="row" className="sticky left-0 z-10 border-b border-r border-border bg-surface px-4 py-3 text-left group-hover:bg-raised"><Link href={trackerChartHref(symbol, market)} className="inline-flex min-h-8 items-center gap-2 font-semibold underline-offset-4 hover:underline focus-visible:underline" aria-label={`${symbol} grafiğini aç`}>{symbol}<span aria-hidden="true" className="text-muted-foreground">↗</span></Link><button type="button" className="block min-h-7 text-[11px] font-normal underline underline-offset-2 disabled:opacity-40" onClick={() => toggleSymbol(symbol)} aria-label={`${symbol} RSI takibini ${follows ? "kapat" : "aç"}`} aria-pressed={follows} disabled={!follows && tracked.length >= TRACKER_SYMBOL_LIMIT}>{follows ? "RSI açık" : "RSI aç"}</button></th>
                            <td className="border-b border-border px-4 py-3 text-right" title={bist ? quote?.message || quote?.provider_time || undefined : undefined}><span className="block font-mono text-sm tabular-nums">{trackerNumber(price)}</span><span className={cn("mt-1 block whitespace-nowrap text-[9px]", available && stale ? "text-neutral" : "text-muted-foreground")}>{status}</span></td>
                            <td className={cn("border-b border-border px-4 py-3 text-right font-mono tabular-nums", change == null || !Number.isFinite(change) ? "text-muted-foreground" : change >= 0 ? "text-profit" : "text-loss")}>{trackerNumber(change)}{change != null && Number.isFinite(change) ? "%" : ""}</td>
                            {shownColumns.map(item => {
                                const cell = rsiRow?.cells[item.id]
                                const cellStatus = !follows ? "RSI takibi kapalı" : rsiStale ? "RSI yenilenemedi"
                                    : RSI_CELL_STATUS[cell?.status ?? "waiting"]
                                const timestamp = cell?.status === "ready" || cell?.status === "stale" ? rsiPriceTime : rsiSourceTime(cell?.bar_time)
                                const value = cell?.value == null ? "—" : cell.value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })
                                const priceLabel = (cell?.status === "ready" || cell?.status === "stale") && rsiRow?.price != null
                                    ? `Hesaplanan fiyat ${trackerNumber(rsiRow.price)}` : null
                                return <td key={item.id} className="border-b border-l border-border/60 px-3 py-3 text-right" title={[cellStatus, timestamp && `${timestamp} TSİ`, priceLabel].filter(Boolean).join(" · ")}>
                                    <span className={cn("block font-mono tabular-nums", cell?.status === "ready" && !rsiStale ? "text-foreground" : "text-muted-foreground")}>{value}</span>
                                    {follows && <span className="block text-[9px] text-muted-foreground">{cellStatus}</span>}
                                </td>
                            })}
                        </tr>
                    })}
                </tbody>
            </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border p-4"><p className="text-[11px] text-muted-foreground">{visible.matched ? `${visible.page * TRACKER_PAGE_SIZE + 1}–${Math.min((visible.page + 1) * TRACKER_PAGE_SIZE, visible.matched)} / ${visible.matched}` : "0 sembol"} · Sayfa başına {TRACKER_PAGE_SIZE} sembol</p><nav aria-label="Takipçi sayfaları" className="flex items-center gap-3"><button type="button" className={control} disabled={visible.page === 0} onClick={() => setPage(visible.page - 1)}>Önceki</button><span className="font-mono text-xs">{visible.page + 1} / {visible.pages}</span><button type="button" className={control} disabled={visible.page + 1 >= visible.pages} onClick={() => setPage(visible.page + 1)}>Sonraki</button></nav></div>
        <p className="border-t border-border px-4 py-3 text-[11px] leading-relaxed text-muted-foreground">{market === "BIST" ? "BIST fiyatları görünür sayfa için 10 saniyede bir kontrol edilir; veri gecikmeli veya seans dışına ait olabilir." : "Binance fiyat akışı yalnız görünür sayfadaki USDT çiftlerini izler."} Sembol bağlantısı grafiği açar.</p>
    </section>
}
