"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { fetchServerWatchlists } from "@/lib/api/advanced-alarms-api"
import { fetchGlobalIndices } from "@/lib/api/client"
import { useBinanceTickerFeed } from "@/lib/hooks/use-binance-ticker"
import { useSession } from "@/lib/hooks/use-session"
import { serverWatchlistHref, serverWatchlistPage } from "@/lib/server-watchlists"
import { cn } from "@/lib/utils"

const numberLabel = (value: number | null | undefined) => typeof value === "number" && Number.isFinite(value)
    ? value.toLocaleString("tr-TR", { maximumFractionDigits: 5 }) : "—"

export function ServerWatchlistPanel({ symbol, market, onSelect }: {
    symbol: string
    market: "BIST" | "Kripto"
    onSelect: (symbol: string, market: "BIST" | "Kripto") => void
}) {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const identity = [session?.user.username, session?.expiresAt]
    const [selectedId, setSelectedId] = useState("")
    const [page, setPage] = useState(0)
    const [now, setNow] = useState(() => Date.now())
    const lists = useQuery({ queryKey: ["advanced-alarm-watchlists", ...identity],
        queryFn: ({ signal }) => fetchServerWatchlists(signal), enabled: allowed,
        refetchInterval: 30_000, staleTime: 10_000, retry: false })
    useEffect(() => {
        setSelectedId(new URLSearchParams(window.location.search).get("serverList") ?? "")
    }, [])
    useEffect(() => {
        const timer = window.setInterval(() => setNow(Date.now()), 10_000)
        return () => window.clearInterval(timer)
    }, [])
    const selected = selectedId ? lists.data?.watchlists.find(list => list.id === selectedId) : lists.data?.watchlists[0]
    const visible = useMemo(() => serverWatchlistPage(selected?.symbols ?? [], page), [selected, page])
    const bist = useQuery({ queryKey: ["server-watchlist-quotes", ...identity, ...visible.bist],
        queryFn: ({ signal }) => fetchGlobalIndices(visible.bist, { signal }),
        enabled: allowed && visible.bist.length > 0, refetchInterval: 10_000, staleTime: 10_000,
        gcTime: 60_000, retry: false })
    const crypto = useBinanceTickerFeed(visible.crypto, { paused: !allowed, flushIntervalMs: 500 })
    const bistQuotes = useMemo(() => new Map((bist.data ?? []).map(quote => [quote.symbol.replace(/\.IS$/, ""), quote])), [bist.data])

    if (!allowed) return <div className="p-4 text-sm"><p>Sunucu listeleri için yönetici girişi gerekir.</p><Link href="/login?next=%2Fchart" className="mt-3 inline-flex min-h-11 items-center text-primary underline">Giriş yap</Link></div>
    return <section className="flex min-h-0 min-w-0 flex-1 flex-col" aria-label="Sunucu izleme listesi">
        <div className="space-y-3 border-b border-border p-3">
            <label className="block space-y-1 text-xs"><span className="text-muted-foreground">Sunucudaki liste</span>
                <select aria-label="Sunucu listesi seç" value={selected?.id ?? ""} onChange={e => { setSelectedId(e.target.value); setPage(0) }} className="min-h-11 w-full min-w-0 rounded border border-border bg-background px-2 text-sm text-foreground">
                    <option value="" disabled>{lists.isLoading ? "Listeler yükleniyor…" : "Liste seç"}</option>
                    {lists.data?.watchlists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.symbols.length})</option>)}
                </select>
            </label>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs"><Link className="inline-flex min-h-10 items-center text-primary underline" href="/alarms?manage=watchlists#watchlists">Liste oluştur / yönet</Link><button type="button" className="min-h-10 text-muted-foreground underline" onClick={() => { void lists.refetch(); if (visible.bist.length) void bist.refetch(); crypto.reconnect() }}>Yenile</button></div>
            {lists.isError && <p role="alert" className="text-xs text-warning">Listeler yenilenemedi. Görünen son kayıtlar güncel olmayabilir.</p>}
            {!lists.isLoading && !lists.isError && !selected && <p role="status" className="text-xs text-muted-foreground">{selectedId ? "Seçilen liste bulunamadı. Başka bir liste seçin." : "Henüz sunucu listesi yok. BIST hisseleri ve Binance USDT çiftlerini aynı listeye ekleyebilirsiniz."}</p>}
            {selected && <><p className="text-xs text-muted-foreground">{selected.symbols.length} sembol · üyeler sunucuda saklanır</p><div className="flex flex-wrap gap-2"><Link href={serverWatchlistHref(selected.id)} className="inline-flex min-h-11 items-center rounded border border-primary/40 px-3 text-xs text-primary">Bu listeye alarm ekle</Link><Link href={serverWatchlistHref(selected.id, "detail")} className="inline-flex min-h-11 items-center rounded border border-border px-3 text-xs">Liste ve alarmları</Link></div></>}
        </div>
        {selected && <>
            <div className="grid grid-cols-[1.2fr_1fr_0.8fr] gap-2 border-b border-border px-3 py-2 text-[11px] text-muted-foreground"><span>Sembol</span><span className="text-right">Son fiyat</span><span className="text-right">Değişim</span></div>
            <div className="max-h-[32rem] min-h-0 flex-1 overflow-y-auto">
                {!visible.rows.length && <p className="p-4 text-xs text-muted-foreground">Liste boş. Üye eklemek için listeyi yönetin.</p>}
                {visible.rows.map(row => {
                    const quote = bistQuotes.get(row.symbol)
                    const tick = crypto.prices[row.symbol]
                    const isBist = row.market_type === "BIST"
                    const price = isBist ? quote?.regularMarketPrice : tick?.price
                    const change = isBist ? quote?.regularMarketChangePercent : tick?.change
                    const received = crypto.receivedAtBySymbol[row.symbol]
                    const stale = isBist ? bist.isError || (quote?.state != null && quote.state !== "ok") || (bist.dataUpdatedAt > 0 && now - bist.dataUpdatedAt > 30_000)
                        : crypto.status !== "connected" || !received || now - received > 60_000
                    const description = isBist ? quote?.message || "Borsapy · veri bekleniyor" : stale ? "Binance · güncel veri bekleniyor" : "Binance · USDT"
                    return <button type="button" key={`${row.market_type}:${row.symbol}`} onClick={() => onSelect(row.symbol, row.market_type)} aria-pressed={symbol === row.symbol && market === row.market_type}
                        title={`${row.symbol} · ${description}${isBist && quote?.provider_time ? ` · ${quote.provider_time}` : ""}`}
                        className={cn("grid min-h-14 w-full grid-cols-[1.2fr_1fr_0.8fr] items-center gap-2 border-b border-border/30 px-3 py-2 text-left hover:bg-raised", symbol === row.symbol && market === row.market_type && "bg-raised")}>
                        <span className="min-w-0"><span className="block truncate text-xs font-semibold">{row.symbol}</span><span className="block truncate text-[10px] text-muted-foreground">{description}</span>{stale && price != null && <span className="block text-[10px] text-warning">Son kayıt · güncel olmayabilir</span>}</span>
                        <span className="min-w-0 break-all text-right font-mono text-xs tabular-nums">{numberLabel(price)}</span><span className={cn("text-right font-mono text-xs tabular-nums", change == null || !Number.isFinite(change) ? "text-muted-foreground" : change >= 0 ? "text-profit" : "text-loss")}>{numberLabel(change)}{change != null && Number.isFinite(change) ? "%" : ""}</span>
                    </button>
                })}
            </div>
            {visible.pages > 1 && <nav aria-label="Liste sayfaları" className="flex items-center justify-between gap-2 border-t border-border p-2 text-xs"><button className="min-h-11 rounded border border-border px-2 disabled:opacity-40" disabled={visible.page === 0} onClick={() => setPage(visible.page - 1)}>Önceki</button><span>{visible.page + 1} / {visible.pages}</span><button className="min-h-11 rounded border border-border px-2 disabled:opacity-40" disabled={visible.page + 1 >= visible.pages} onClick={() => setPage(visible.page + 1)}>Sonraki</button></nav>}
        </>}
        <p className="border-t border-border p-3 text-[11px] leading-relaxed text-muted-foreground">Sayfada en fazla 50 sembolün fiyatı izlenir. Kaydettiğiniz etkin liste alarmları, tarayıcı kapalıyken de listenin tüm üyelerini sunucunun veri ve kapasite sınırları içinde kontrol eder.</p>
        <Link href="/alarms?manage=watchlists#watchlists" className="px-3 pb-3 text-xs text-primary underline">Eski tarayıcı listesini elle kopyala</Link>
    </section>
}
