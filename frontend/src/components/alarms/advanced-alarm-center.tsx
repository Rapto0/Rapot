"use client"

import { useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { Activity, Bell, List, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react"
import { ActionDialog } from "@/components/ui/action-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { Select } from "@/components/ui/select"
import { ConditionBuilder } from "@/components/alarms/condition-builder"
import { useSession } from "@/lib/hooks/use-session"
import { ApiError } from "@/lib/api/core"
import { fetchAdvancedAlarms, fetchAdvancedAlarmStatus, fetchAdvancedEvents, fetchServerWatchlists, removeAdvancedAlarm, removeServerWatchlist, saveAdvancedAlarm, saveServerWatchlist, type AdvancedAlarmRule, type AlarmCategory, type AlarmTimeframe, type ServerWatchlist } from "@/lib/api/advanced-alarms-api"
import { CATEGORY_LABELS, conditionLabel, draftFromAdvancedRule, emptyAdvancedDraft, parseAlarmSymbols, TIMEFRAME_LABELS, writeFromAdvancedDraft, type AdvancedDraft } from "@/lib/advanced-alarm-form"
import { loadStoredWatchlists, type StoredWatchlistModel } from "@/lib/watchlist-alarms"

const timeLabel = (value?: string | null) => value && Number.isFinite(Date.parse(value)) ? new Date(value).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" }) : "Henüz yok"
const deliveryLabels: Record<string, string> = { sent: "Telegram'a gönderildi", pending: "Telegram kuyruğunda", sending: "Gönderiliyor", failed: "Gönderim başarısız", not_requested: "Yalnız olay kaydı", cancelled: "Bildirim iptal edildi" }
const stateLabels: Record<string, string> = { active: "İzleniyor", partial: "Kısmen kontrol edildi", pending: "Veri bekleniyor", paused: "Duraklatıldı", error: "Kontrol sorunu", unknown: "Veri doğrulanamadı" }
const readableError = (error: unknown) => error instanceof ApiError && error.status === 409 ? "Kayıt başka bir işlemde değişmiş veya kapasite sınırına ulaşılmış olabilir. Listeyi yenileyip tekrar deneyin." : error instanceof Error ? error.message : "İşlem tamamlanamadı."
const statistic = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("tr-TR") : "—"
type WatchlistDraft = { name: string; bist: string; crypto: string; id?: string; revision?: number }

export function AdvancedAlarmCenter() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const identity = [session?.user.username, session?.expiresAt]
    const rules = useQuery({ queryKey: ["advanced-alarms", ...identity], queryFn: ({ signal }) => fetchAdvancedAlarms(signal), enabled: allowed, refetchInterval: 15_000, retry: false })
    const status = useQuery({ queryKey: ["advanced-alarm-status", ...identity], queryFn: ({ signal }) => fetchAdvancedAlarmStatus(signal), enabled: allowed, refetchInterval: 1000, retry: false })
    const events = useQuery({ queryKey: ["advanced-alarm-events", ...identity], queryFn: ({ signal }) => fetchAdvancedEvents(undefined, signal), enabled: allowed, refetchInterval: 1000, retry: false })
    const watchlists = useQuery({ queryKey: ["advanced-alarm-watchlists", ...identity], queryFn: ({ signal }) => fetchServerWatchlists(signal), enabled: allowed, refetchInterval: 15_000, retry: false })
    const [category, setCategory] = useState<AlarmCategory>("price")
    const [search, setSearch] = useState("")
    const [page, setPage] = useState(0)
    const [draft, setDraft] = useState<AdvancedDraft | null>(null)
    const [editing, setEditing] = useState<AdvancedAlarmRule | null>(null)
    const [watchlistDraft, setWatchlistDraft] = useState<WatchlistDraft | null>(null)
    const [localLists, setLocalLists] = useState<StoredWatchlistModel[]>([])
    const [deleting, setDeleting] = useState<{ kind: "rule" | "watchlist"; id: string; name: string } | null>(null)
    const [pending, setPending] = useState(false)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const pendingRef = useRef(false)
    const editorRef = useRef<HTMLHeadingElement>(null)
    const runtime = status.data ?? rules.data?.runtime
    const market = runtime?.market ?? {}
    const delayed = Boolean(runtime?.last_cycle_at && Date.now() - Date.parse(runtime.last_cycle_at) > 15_000)
    const serviceLabel = status.isError ? "Durum doğrulanamadı" : !runtime ? "Durum yükleniyor" : !runtime.running ? "Alarm motoru çalışmıyor" : runtime.last_error ? "Alarm motoru uyarı veriyor" : delayed ? "Son kontrol gecikti" : "Alarm motoru çalışıyor"

    useEffect(() => {
        setLocalLists(loadStoredWatchlists())
        const params = new URLSearchParams(window.location.search)
        const rawSymbol = params.get("symbol")
        if (rawSymbol) {
            const next = emptyAdvancedDraft("price")
            const rawMarket = params.get("market") === "Kripto" ? "Kripto" : "BIST"
            try {
                const parsed = parseAlarmSymbols(rawMarket === "BIST" ? rawSymbol : "", rawMarket === "Kripto" ? rawSymbol : "")
                next.bist = parsed.filter(x => x.market_type === "BIST").map(x => x.symbol).join(", ")
                next.crypto = parsed.filter(x => x.market_type === "Kripto").map(x => x.symbol).join(", ")
                setDraft(next)
            } catch { /* Invalid URL prefill cannot save or enable a rule. */ }
        }
        const localId = params.get("watchlist")
        if (localId) {
            const local = loadStoredWatchlists().find(list => list.id === localId)
            if (local) setWatchlistDraft({ name: local.name, bist: local.rows.filter(row => row.kind === "symbol" && row.marketType === "BIST").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", "), crypto: local.rows.filter(row => row.kind === "symbol" && row.marketType === "Kripto").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", ") })
        }
    }, [])
    const editorOpen = draft !== null
    useEffect(() => { if (editorOpen) editorRef.current?.focus() }, [editorOpen])

    const filtered = useMemo(() => (rules.data?.rules ?? []).filter(rule => rule.category === category && (!search.trim() || `${rule.name} ${rule.symbols.map(s => s.symbol).join(" ")}`.toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR")))), [rules.data, category, search])
    const safePage = Math.min(page, Math.max(0, Math.ceil(filtered.length / 30) - 1))
    const visible = filtered.slice(safePage * 30, (safePage + 1) * 30)

    async function mutate(action: () => Promise<void>) {
        if (!allowed || pendingRef.current) return
        pendingRef.current = true; setPending(true); setError(""); setNotice("")
        try { await action(); await Promise.all([rules.refetch(), status.refetch(), watchlists.refetch(), events.refetch()]) }
        catch (cause) { setError(readableError(cause)) }
        finally { pendingRef.current = false; setPending(false) }
    }
    function openEditor(rule?: AdvancedAlarmRule) {
        setEditing(rule ?? null); setDraft(rule ? draftFromAdvancedRule(rule) : emptyAdvancedDraft(category)); setError(""); setNotice("")
    }
    function change<K extends keyof AdvancedDraft>(key: K, value: AdvancedDraft[K]) { setDraft(current => current ? { ...current, [key]: value } : current) }
    async function save(event: FormEvent) {
        event.preventDefault()
        if (!draft) return
        await mutate(async () => {
            const saved = await saveAdvancedAlarm(writeFromAdvancedDraft(draft, editing?.revision), editing?.id)
            setCategory(saved.category); setDraft(null); setEditing(null)
            setNotice("Alarm süresiz olarak sunucuya kaydedildi. İzleme durumunu aşağıdan takip edebilirsiniz.")
        })
    }
    async function saveWatchlist(event: FormEvent) {
        event.preventDefault()
        if (!watchlistDraft) return
        await mutate(async () => {
            const symbols = parseAlarmSymbols(watchlistDraft.bist, watchlistDraft.crypto)
            if (!symbols.length) throw new Error("Listeye en az bir sembol ekleyin.")
            const saved = await saveServerWatchlist({ name: watchlistDraft.name.trim(), symbols, revision: watchlistDraft.revision }, watchlistDraft.id)
            setWatchlistDraft(null)
            setNotice(`${saved.name} sunucuya kaydedildi. Bu listeye bağlı alarmlar yeni üyeleri kullanacak.`)
        })
    }
    function editWatchlist(list: ServerWatchlist) { setWatchlistDraft({ id: list.id, revision: list.revision, name: list.name, bist: list.symbols.filter(s => s.market_type === "BIST").map(s => s.symbol).join(", "), crypto: list.symbols.filter(s => s.market_type === "Kripto").map(s => s.symbol).join(", ") }) }
    async function remove() {
        if (!deleting) return
        await mutate(async () => {
            if (deleting.kind === "rule") await removeAdvancedAlarm(deleting.id)
            else await removeServerWatchlist(deleting.id)
            setDeleting(null); setNotice("Kayıt kaldırıldı.")
        })
    }

    return <PageShell label="Kalıcı izleme" title="Alarm merkezi" description="Fiyat, teknik ve izleme listesi alarmlarını buradan yönet. Etkin kurallar, tarayıcın kapalıyken de sunucuda çalışır.">
        {!allowed ? <section className="space-y-3 rounded border border-border bg-surface p-5"><p>{session ? "Alarm yönetimi için yönetici yetkisi gerekir." : "Kalıcı alarmlarını yönetmek için hesabına giriş yap."}</p><Link href="/login?next=%2Falarms" className="inline-flex min-h-11 items-center rounded border border-border px-4 text-sm">Giriş yap</Link><p className="text-xs text-muted-foreground">Oturumun kapanması sunucudaki etkin kuralları durdurmaz.</p></section> : <>
            <section aria-label="Canlı alarm durumu" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded border border-border bg-surface p-4"><p className="flex items-center gap-2 text-xs text-muted-foreground"><Activity className="h-4 w-4" />Sunucu</p><p className="mt-2 text-sm font-semibold">{serviceLabel}</p><p className="mt-1 text-xs text-muted-foreground">Son tur: {timeLabel(runtime?.last_cycle_at)}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Son kontrol turu</p><p className="mt-2 text-sm font-semibold">{statistic(runtime?.evaluation?.ready)} hazır / {statistic(runtime?.evaluation?.checked)} kontrol</p><p className="mt-1 text-xs text-muted-foreground">Toplam {statistic(runtime?.evaluation?.total)} eşleşme · Bekleyen kontrol: {statistic(runtime?.evaluation?.backlog)}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Kalıcı veri takibi</p><p className="mt-2 text-sm font-semibold">{statistic(market.fresh_symbols ?? market.ready_symbols)} güncel / {statistic(market.tracked_symbols ?? market.symbol_count)} sembol</p><p className="mt-1 text-xs text-muted-foreground">{typeof market.state === "string" ? ({ ok: "Taze fiyat alınıyor", waiting: "İlk fiyat bekleniyor", warming: "Veri hazırlanıyor", auth_required: "Hesap bağlantısını doğrulayın", storage_error: "Veri kaydı bekletiliyor", error: "Bağlantı sorunu", running: "Veri takibi açık", connected: "Bağlantı açık", unavailable: "Veri bekleniyor", disabled: "Veri takibi kapalı", reconnecting: "Yeniden bağlanıyor" }[market.state] ?? "Durum ayrıntılarını inceleyin") : "İlk veri bekleniyor"}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Telegram kuyruğu</p><p className="mt-2 text-sm font-semibold">{statistic(runtime?.delivery?.pending)} bekleyen · {statistic(runtime?.delivery?.failed)} başarısız</p><p className="mt-1 text-xs text-muted-foreground">{runtime?.telegram_configured ? "Sunucudaki Telegram hedefi hazır" : "Telegram bağlantı durumu bekleniyor"}</p></div>
            </section>
            <p className="text-xs leading-relaxed text-muted-foreground">Ekran saniyede bir yenilenir. Fiyat koşulları yeni fiyatları, teknik koşullar sağlayıcı mumlarını izler. Teknik veri yenileme hedefi 1 dakikalık mumlarda 30 saniye, diğer periyotlarda 60 saniyedir; yoğunlukta uzayabilir. Seans dışında BIST&apos;te yeni işlem fiyatı oluşmayabilir. Canlı piyasa gecikmesi ve tetikleme kabulü henüz tamamlanmadı.</p>
            <details className="rounded border border-border bg-surface p-3 text-xs"><summary className="cursor-pointer">Veri kapsamı ve bağlantı ayrıntıları</summary><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><p>BIST evreni: <strong>{statistic(market.universe_count)}</strong></p><p>Abone olunan: <strong>{statistic(market.subscribed_symbols)}</strong></p><p>Bayat / beklenen fiyat: <strong>{statistic(market.stale_symbols)}</strong></p><p>Yeniden bağlantı: <strong>{statistic(market.reconnect_attempts)}</strong></p><p>Hazır mum serisi: <strong>{statistic(market.history_ready)}</strong></p><p>Bekleyen mum serisi: <strong>{statistic(market.history_pending)}</strong></p><p>İstenen / planlanan seri: <strong>{statistic(market.history_requested)} / {statistic(market.history_scheduled)}</strong></p><p>En eski mum alımı: <strong>{statistic(market.oldest_history_age_seconds)} sn</strong></p><p>Fiyat alınma yaşı: <strong>{statistic(market.quote_age_seconds)} sn</strong></p><p>Kaynak zamanının yaşı: <strong>{statistic(market.source_age_seconds)} sn</strong></p></div>{typeof market.message === "string" && <p className="mt-3 text-muted-foreground">{market.message}</p>}<p className="mt-3 leading-relaxed text-muted-foreground">BIST&apos;te kapanış teyidi sağlayıcının sonraki gerçek mumuna dayanır. Seansın son mumu ve günlük mum, sonraki mum gelene kadar bekleyebilir. Yoğunlukta aynı sembolün güncellemeleri birleştirilir; bu ekran her işlemin veya her alarmın bir saniyede tamamlandığına dair garanti vermez.</p></details>
            {(error || rules.isError || status.isError || runtime?.last_error) && <p role="alert" className="rounded border border-loss/40 bg-loss/5 p-3 text-sm">{error || (rules.isError ? readableError(rules.error) : status.isError ? "Canlı durum yenilenemedi; son kayıtlar güncel olmayabilir." : runtime?.last_error)}</p>}
            {notice && <p role="status" className="rounded border border-border bg-surface p-3 text-sm">{notice}</p>}
            <section className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex flex-wrap gap-2" aria-label="Alarm türleri">{(Object.keys(CATEGORY_LABELS) as AlarmCategory[]).map(key => <Button key={key} variant={category === key ? "default" : "outline"} aria-pressed={category === key} onClick={() => { setCategory(key); setPage(0) }}>{CATEGORY_LABELS[key]} <span className="ml-2 tabular-nums">{statistic(rules.data?.usage?.[key])} / 1.000</span></Button>)}</div><div className="flex gap-2"><Button variant="outline" aria-label="Alarmları yenile" disabled={pending} onClick={() => void Promise.all([rules.refetch(), status.refetch(), events.refetch()])}><RefreshCw className="h-4 w-4" /></Button><Button disabled={pending} onClick={() => openEditor()}><Plus className="mr-2 h-4 w-4" />Yeni alarm</Button></div></div>
                {draft && <section className="rounded border border-border bg-surface p-4 sm:p-5"><h2 ref={editorRef} tabIndex={-1} className="mb-4 text-base font-semibold">{editing ? "Alarmı düzenle" : `Yeni ${CATEGORY_LABELS[draft.category].toLocaleLowerCase("tr-TR")} alarmı`}</h2><form onSubmit={save} className="space-y-4"><fieldset disabled={pending} className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2"><label className="space-y-1 text-sm"><span>Alarm adı</span><Input value={draft.name} maxLength={80} required onChange={e => change("name", e.target.value)} placeholder="Örn. RSI dönüş ve trend onayı" /></label><div className="rounded border border-border p-3 text-sm">Süre: <strong>Süresiz</strong><p className="mt-1 text-xs text-muted-foreground">Sen duraklatana veya silene kadar kayıtlı kalır.</p></div>
                    {draft.category === "watchlist" && <><label className="space-y-1 text-sm"><span>İzlenecek evren</span><Select value={draft.scope} onChange={e => change("scope", e.target.value as AdvancedDraft["scope"])}><option value="all_bist">Tüm BIST hisseleri</option><option value="watchlist">Sunucudaki izleme listesi</option></Select></label>{draft.scope === "watchlist" && <label className="space-y-1 text-sm"><span>İzleme listesi</span><Select value={draft.watchlist_id ?? ""} onChange={e => change("watchlist_id", e.target.value || null)} required><option value="">Liste seç</option>{watchlists.data?.watchlists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.symbols.length})</option>)}</Select></label>}</>}
                    {draft.scope === "symbols" && <><label className="space-y-1 text-sm"><span>BIST hisseleri</span><Input value={draft.bist} onChange={e => change("bist", e.target.value)} placeholder="THYAO, ASELS, GARAN" autoCapitalize="characters" /></label><label className="space-y-1 text-sm"><span>Kripto çiftleri</span><Input value={draft.crypto} onChange={e => change("crypto", e.target.value)} placeholder="BTCUSDT, ETHUSDT" autoCapitalize="characters" /></label></>}
                    <label className="space-y-1 text-sm"><span>Alarm periyodu</span><Select value={draft.timeframe} onChange={e => change("timeframe", e.target.value as AlarmTimeframe)}>{Object.entries(TIMEFRAME_LABELS).map(([tf, label]) => <option key={tf} value={tf}>{label}</option>)}</Select></label><label className="space-y-1 text-sm"><span>Değerlendirme zamanı</span><Select value={draft.trigger} onChange={e => change("trigger", e.target.value as AdvancedDraft["trigger"])}><option value="intrabar">Veri geldikçe / mum içinde</option><option value="bar_close">Yalnız kapanmış mum</option></Select></label></div>
                    <ConditionBuilder value={draft.condition} onChange={condition => change("condition", condition)} category={draft.category} />
                    <p className="rounded bg-background/50 p-3 text-xs leading-relaxed">{conditionLabel(draft.condition)}</p>
                    <div className="grid gap-4 sm:grid-cols-2"><label className="space-y-1 text-sm"><span>Tekrarlama</span><Select value={draft.mode} onChange={e => change("mode", e.target.value as AdvancedDraft["mode"])}><option value="on_enter">Koşula her yeni girişte</option><option value="once_per_bar">Mum başına en fazla bir kez</option><option value="cooldown">Bekleme süresinden sonra tekrar</option></Select></label><label className="space-y-1 text-sm"><span>Bildirimler arasında en az (saniye)</span><Input type="number" min={1} max={86400} value={Number.isFinite(draft.cooldown_seconds) ? draft.cooldown_seconds : ""} onChange={e => change("cooldown_seconds", e.target.valueAsNumber)} /></label></div>
                    <div className="flex flex-wrap gap-x-6 gap-y-3"><label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={draft.enabled} onChange={e => change("enabled", e.target.checked)} />Alarm etkin</label><label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={draft.notify_telegram} onChange={e => change("notify_telegram", e.target.checked)} />Telegram&apos;a bildir</label></div>
                    <p className="text-xs leading-relaxed text-muted-foreground">İlk geçerli veri başlangıç durumunu kurar. Eksik veya bayat veriden tetik üretilmez. Mum içi göstergeler kapanışa kadar değişebilir. Aynı koşulda kullanılan farklı periyotlar kendi veri zamanlarıyla kontrol edilir.</p>
                    <div className="flex gap-2"><Button type="submit">{pending ? "Kaydediliyor…" : "Alarmı sunucuya kaydet"}</Button><Button type="button" variant="outline" onClick={() => { setDraft(null); setEditing(null) }}>Vazgeç</Button></div>
                </fieldset></form></section>}
                <label className="block max-w-md text-sm"><span className="sr-only">Kayıtlı alarmlarda ara</span><Input placeholder="Alarm adı veya sembol ara…" value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} /></label>
                {rules.isLoading && <p role="status">Alarmlar yükleniyor…</p>}
                {!rules.isLoading && !visible.length && <div className="rounded border border-dashed border-border p-8 text-center"><Bell className="mx-auto mb-3 h-6 w-6 text-muted-foreground" /><p className="text-sm">{search ? "Aramana uyan alarm bulunamadı." : "Bu türde henüz alarm yok."}</p><p className="mt-2 text-xs text-muted-foreground">Koşullarını seçip sunucuya kaydet; takibi buradan izle.</p></div>}
                {visible.map(rule => <article key={rule.id} className="space-y-2 rounded border border-border bg-surface p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><h3 className="break-words text-sm font-semibold">{rule.name}</h3><p className="mt-1 break-words text-xs leading-relaxed text-muted-foreground">{conditionLabel(rule.condition)}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={pending} onClick={() => void mutate(async () => { await saveAdvancedAlarm({ ...writeFromAdvancedDraft(draftFromAdvancedRule(rule), rule.revision), enabled: !rule.enabled }, rule.id) })}>{rule.enabled ? "Duraklat" : "Etkinleştir"}</Button><Button variant="outline" size="icon" aria-label={`${rule.name}: düzenle`} disabled={pending} onClick={() => openEditor(rule)}><Pencil className="h-4 w-4" /></Button><Button variant="outline" size="icon" aria-label={`${rule.name}: sil`} disabled={pending} onClick={() => setDeleting({ kind: "rule", id: rule.id, name: rule.name })}><Trash2 className="h-4 w-4" /></Button></div></div><p className="break-words text-xs">{rule.scope === "all_bist" ? "Tüm BIST" : rule.scope === "watchlist" ? watchlists.data?.watchlists.find(list => list.id === rule.watchlist_id)?.name ?? "İzleme listesi" : rule.symbols.map(item => item.symbol).join(", ")} · {TIMEFRAME_LABELS[rule.timeframe]} · {rule.trigger === "intrabar" ? "Mum içinde" : "Mum kapanışında"} · Süresiz</p><p className="text-xs text-muted-foreground">{stateLabels[rule.state] ?? rule.state} · Son kontrol: {timeLabel(rule.last_checked_at)} · Son tetik: {timeLabel(rule.last_triggered_at)} · Telegram {rule.notify_telegram ? "açık" : "kapalı"}</p>{rule.last_error && <p className="text-xs text-loss">{rule.last_error}</p>}</article>)}
                {filtered.length > 30 && <div className="flex items-center gap-3 text-xs"><Button variant="outline" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Önceki</Button><span>{safePage + 1} / {Math.ceil(filtered.length / 30)} · {filtered.length} alarm</span><Button variant="outline" disabled={(safePage + 1) * 30 >= filtered.length} onClick={() => setPage(safePage + 1)}>Sonraki</Button></div>}
            </section>
            <details className="rounded border border-border bg-surface p-4" open={Boolean(watchlistDraft)}><summary className="cursor-pointer text-sm font-semibold"><List className="mr-2 inline h-4 w-4" />Sunucudaki izleme listeleri ({watchlists.data?.watchlists.length ?? "—"})</summary><div className="mt-4 space-y-3"><p className="text-xs text-muted-foreground">Bu listeler sunucuda saklanır. Üyelerini değiştirdiğinde bağlı alarmlar da güncellenir.</p><Button variant="outline" size="sm" onClick={() => setWatchlistDraft({ name: "", bist: "", crypto: "" })}>Yeni liste</Button>
                {localLists.length > 0 && <label className="block max-w-md space-y-1 text-xs"><span>Tarayıcıdaki listeden kopyala</span><Select value="" onChange={e => { const list = localLists.find(item => item.id === e.target.value); if (list) setWatchlistDraft({ name: list.name, bist: list.rows.filter(row => row.kind === "symbol" && row.marketType === "BIST").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", "), crypto: list.rows.filter(row => row.kind === "symbol" && row.marketType === "Kripto").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", ") }) }}><option value="">Kaynak liste seç</option>{localLists.map(list => <option key={list.id} value={list.id}>{list.name}</option>)}</Select></label>}
                {watchlistDraft && <form onSubmit={saveWatchlist} className="space-y-3 border-t border-border pt-3"><fieldset disabled={pending} className="space-y-3"><label className="block space-y-1 text-sm"><span>Liste adı</span><Input required maxLength={80} value={watchlistDraft.name} onChange={e => setWatchlistDraft({ ...watchlistDraft, name: e.target.value })} /></label><label className="block space-y-1 text-sm"><span>BIST hisseleri</span><textarea className="min-h-20 w-full rounded border border-border bg-background p-2" value={watchlistDraft.bist} onChange={e => setWatchlistDraft({ ...watchlistDraft, bist: e.target.value })} placeholder="THYAO, ASELS, GARAN" /></label><label className="block space-y-1 text-sm"><span>Binance USDT çiftleri</span><Input value={watchlistDraft.crypto} onChange={e => setWatchlistDraft({ ...watchlistDraft, crypto: e.target.value })} placeholder="BTCUSDT, ETHUSDT" /></label><div className="flex gap-2"><Button type="submit">Listeyi kaydet</Button><Button type="button" variant="outline" onClick={() => setWatchlistDraft(null)}>Vazgeç</Button></div></fieldset></form>}
                {watchlists.isError && <p role="alert" className="text-sm text-loss">İzleme listeleri yüklenemedi.</p>}
                {watchlists.data?.watchlists.map(list => <div key={list.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3 text-sm"><div>{list.name}<span className="ml-2 text-xs text-muted-foreground">{list.symbols.length} sembol</span></div><div className="flex gap-2"><Button variant="outline" size="sm" disabled={pending} onClick={() => editWatchlist(list)}>Düzenle</Button><Button variant="outline" size="sm" disabled={pending} onClick={() => setDeleting({ kind: "watchlist", id: list.id, name: list.name })}>Sil</Button></div></div>)}
            </div></details>
            <section className="space-y-3 rounded border border-border bg-surface p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-sm font-semibold">Canlı alarm akışı</h2><span className="text-xs text-muted-foreground">Son 100 olay · Türkiye saati · saniyede bir yenilenir</span></div>{events.isError && <p role="alert" className="text-sm text-loss">Olay akışı yenilenemedi; son kayıtlar gösteriliyor.</p>}{events.isLoading && <p role="status" className="text-xs">Olaylar yükleniyor…</p>}{events.data?.events.length === 0 && <p className="text-sm text-muted-foreground">Henüz tetiklenen alarm yok.</p>}{[...(events.data?.events ?? [])].sort((a, b) => b.id - a.id).map(event => <article key={event.id} className="space-y-1 border-t border-border pt-3 text-xs"><div className="flex flex-wrap justify-between gap-2"><p className="font-medium">{event.rule_name} · {event.symbol}</p><p className="text-muted-foreground">{timeLabel(event.created_at)}</p></div><p>Değer: {typeof event.value === "number" && Number.isFinite(event.value) ? event.value.toLocaleString("tr-TR", { maximumFractionDigits: 5 }) : "—"} · {deliveryLabels[event.delivery_status] ?? event.delivery_status} · #{event.id}</p>{event.delivery_error && <p className="text-loss">{event.delivery_error}</p>}</article>)}</section>
            <ActionDialog open={Boolean(deleting)} title={deleting?.kind === "watchlist" ? "İzleme listesini sil" : "Alarmı sil"} description={`${deleting?.name ?? ""} kaldırılacak.${deleting?.kind === "watchlist" ? " Bu listeye bağlı alarmlar duraklatılacak." : " Geçmiş olay kayıtları korunacak."}${error ? ` ${error}` : ""}`} variant="danger" confirmLabel="Sil" cancelLabel="Vazgeç" pending={pending} onConfirm={() => void remove()} onCancel={() => setDeleting(null)} />
        </>}
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground"><Link href="/alarms/legacy" className="underline">Önceki günlük sunucu alarmları</Link><Link href="/alarms/local" className="underline">Eski tarayıcı alarmları</Link><Link href="/chart" className="underline">Grafiğe dön</Link></div>
    </PageShell>
}
