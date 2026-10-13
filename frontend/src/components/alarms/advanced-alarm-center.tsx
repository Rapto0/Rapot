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
import { fetchBistSymbols, fetchCryptoSymbols } from "@/lib/api/client"
import { fetchAdvancedAlarms, fetchAdvancedAlarmStatus, fetchAdvancedEvents, fetchServerWatchlists, removeAdvancedAlarm, removeServerWatchlist, saveAdvancedAlarm, saveServerWatchlist, type AdvancedAlarmRule, type AlarmCategory, type AlarmTimeframe, type ServerWatchlist } from "@/lib/api/advanced-alarms-api"
import { CATEGORY_LABELS, CUSTOM_INDICATOR_LABELS, withIndicatorPreset, conditionLabel, draftForWatchlist, draftFromAdvancedRule, emptyAdvancedDraft, mergeWatchlistSnapshot, parseAlarmSymbols, TIMEFRAME_LABELS, writeFromAdvancedDraft, type AdvancedDraft } from "@/lib/advanced-alarm-form"
import { consumeCustomIndicatorPreset } from "@/lib/custom-indicator-presets"
import { serverWatchlistHref } from "@/lib/server-watchlists"
import { loadStoredScannerWatchlists, loadStoredWatchlists, type StoredWatchlistModel } from "@/lib/watchlist-alarms"

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
    const [selectedListId, setSelectedListId] = useState("")
    const [requestedList, setRequestedList] = useState<{ id: string; create: boolean } | null>(null)
    const handledListLink = useRef(false)
    const handledCustomPreset = useRef(false)
    const [listSearch, setListSearch] = useState("")
    const [listPage, setListPage] = useState(0)
    const [deleting, setDeleting] = useState<{ kind: "rule" | "watchlist"; id: string; name: string } | null>(null)
    const [pending, setPending] = useState(false)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const pendingRef = useRef(false)
    const editorRef = useRef<HTMLHeadingElement>(null)
    const runtime = status.data ?? rules.data?.runtime
    const market = runtime?.market ?? {}
    const customStatus = market.custom_indicators !== null && typeof market.custom_indicators === "object" && !Array.isArray(market.custom_indicators) ? market.custom_indicators as Record<string, unknown> : {}
    const delayed = Boolean(runtime?.last_cycle_at && Date.now() - Date.parse(runtime.last_cycle_at) > 15_000)
    const serviceLabel = status.isError ? "Durum doğrulanamadı" : !runtime ? "Durum yükleniyor" : !runtime.running ? "Alarm motoru çalışmıyor" : runtime.last_error ? "Alarm motoru uyarı veriyor" : delayed ? "Son kontrol gecikti" : "Alarm motoru çalışıyor"

    useEffect(() => {
        setLocalLists([...loadStoredWatchlists(), ...loadStoredScannerWatchlists()])
        const params = new URLSearchParams(window.location.search)
        const serverListId = params.get("serverList")
        if (serverListId) setRequestedList({ id: serverListId, create: params.get("action") === "new" })
        if (params.get("manage") === "watchlists") setCategory("watchlist")
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
    useEffect(() => {
        if (!allowed || !requestedList || !watchlists.data || handledListLink.current) return
        handledListLink.current = true
        const list = watchlists.data.watchlists.find(item => item.id === requestedList.id)
        if (!list) { setError("Seçilen sunucu listesi bulunamadı. Listeyi yenileyip tekrar seçin."); return }
        setSelectedListId(list.id); setCategory("watchlist"); setPage(0)
        if (requestedList.create) { setEditing(null); setDraft(draftForWatchlist(list)) }
    }, [allowed, requestedList, watchlists.data])
    const editorOpen = draft !== null
    useEffect(() => { if (editorOpen) editorRef.current?.focus() }, [editorOpen])

    useEffect(() => {
        if (!allowed || handledCustomPreset.current || !session) return
        const nonce = new URLSearchParams(window.location.search).get("customPreset")
        if (!nonce) return
        handledCustomPreset.current = true
        const preset = consumeCustomIndicatorPreset(nonce, `${session.user.username}:${session.expiresAt}`)
        if (!preset) { setError("Grafikteki ayarlar bulunamadı veya süresi doldu. Grafikte tekrar ‘Bu ayarlarla alarm oluştur’ seçeneğini kullanın."); return }
        const next = withIndicatorPreset(emptyAdvancedDraft("technical"), preset.indicator)
        next.name = `${CUSTOM_INDICATOR_LABELS[preset.indicator]} · ${preset.symbol}`.slice(0, 80)
        next.timeframe = preset.timeframe
        next.bist = preset.market_type === "BIST" ? preset.symbol : ""
        next.crypto = preset.market_type === "Kripto" ? preset.symbol : ""
        next.condition = { op: "eq", left: { field: "custom", indicator: preset.indicator, output: "buy_signal", inputs: preset.inputs }, right: 1 }
        setCategory("technical"); setEditing(null); setDraft(next)
        setNotice("Grafikte uyguladığın ayarlar forma aktarıldı. İstersen hedefi izleme listesi yapıp aşağıdan seçebilirsin; kaydedene kadar alarm oluşturulmaz.")
    }, [allowed, session])

    const selectedList = watchlists.data?.watchlists.find(list => list.id === selectedListId)
    const selectedRules = (rules.data?.rules ?? []).filter(rule => rule.watchlist_id === selectedListId)
    const matchingLists = (watchlists.data?.watchlists ?? []).filter(list => !listSearch.trim() || list.name.toLocaleLowerCase("tr-TR").includes(listSearch.toLocaleLowerCase("tr-TR")))
    const safeListPage = Math.min(listPage, Math.max(0, Math.ceil(matchingLists.length / 20) - 1))
    const filtered = useMemo(() => (rules.data?.rules ?? []).filter(rule => rule.category === category && (category !== "watchlist" || !selectedListId || rule.watchlist_id === selectedListId) && (!search.trim() || `${rule.name} ${rule.symbols.map(s => s.symbol).join(" ")}`.toLocaleLowerCase("tr-TR").includes(search.toLocaleLowerCase("tr-TR")))), [rules.data, category, search, selectedListId])
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
        setEditing(rule ?? null); setDraft(rule ? draftFromAdvancedRule(rule) : category === "watchlist" && selectedList ? draftForWatchlist(selectedList) : emptyAdvancedDraft(category)); setError(""); setNotice("")
    }
    function selectList(list: ServerWatchlist) { setSelectedListId(list.id); setCategory("watchlist"); setPage(0); setSearch("") }
    function newListAlarm(list: ServerWatchlist, kind: "price" | "technical") {
        selectList(list); setEditing(null); setDraft(draftForWatchlist(list, kind)); setError(""); setNotice("")
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
            selectList(saved)
            if (!watchlistDraft.id) { setEditing(null); setDraft(draftForWatchlist(saved)) }
            setNotice(`${saved.name} sunucuya kaydedildi. ${watchlistDraft.id ? "Bağlı alarmlar yeni üyeleri kullanacak." : "Alarm taslağı hazır; alarmı ayrıca kaydetmeden izleme başlamaz. Eski tarayıcı listeniz korundu."}`)
        })
    }
    function editWatchlist(list: ServerWatchlist) { setWatchlistDraft({ id: list.id, revision: list.revision, name: list.name, bist: list.symbols.filter(s => s.market_type === "BIST").map(s => s.symbol).join(", "), crypto: list.symbols.filter(s => s.market_type === "Kripto").map(s => s.symbol).join(", ") }) }
    async function addUniverse(marketType: "BIST" | "Kripto") {
        if (!allowed || !watchlistDraft || pendingRef.current) return
        const currentDraft = watchlistDraft
        pendingRef.current = true; setPending(true); setError(""); setNotice("")
        try {
            const response = await (marketType === "BIST" ? fetchBistSymbols() : fetchCryptoSymbols())
            const merged = mergeWatchlistSnapshot(currentDraft.bist, currentDraft.crypto, marketType, response.symbols)
            setWatchlistDraft(current => current === currentDraft ? { ...current, bist: merged.bist, crypto: merged.crypto } : current)
            setNotice(`Kaynaktan alınan kodlar mevcut üyelerle birleştirildi: ${merged.count} sembol. Bu anlık bir liste kopyasıdır; yeni kodlar otomatik eklenmez. Kaydetmeden sunucu listesi veya alarm değişmez.`)
        } catch {
            setError("Sembol listesi alınamadı, geçersiz kod içeriyor veya toplam 2.000 sınırını aşıyor. Mevcut girişler korundu; daha sonra tekrar deneyebilirsiniz.")
        } finally { pendingRef.current = false; setPending(false) }
    }
    async function remove() {
        if (!deleting) return
        await mutate(async () => {
            if (deleting.kind === "rule") await removeAdvancedAlarm(deleting.id)
            else { await removeServerWatchlist(deleting.id); if (selectedListId === deleting.id) { setSelectedListId(""); setDraft(null) } }
            setDeleting(null); setNotice("Kayıt kaldırıldı.")
        })
    }

    return <PageShell label="Kalıcı izleme" title="Alarm merkezi" description="Fiyat, teknik ve izleme listesi alarmlarını buradan yönet. Etkin kurallar, tarayıcın kapalıyken de sunucuda çalışır.">
        {!allowed ? <section className="space-y-3 rounded border border-border bg-surface p-5"><p>{session ? "Alarm yönetimi için yönetici yetkisi gerekir." : "Kalıcı alarmlarını yönetmek için hesabına giriş yap."}</p><Link href="/login?next=%2Falarms" className="inline-flex min-h-11 items-center rounded border border-border px-4 text-sm">Giriş yap</Link><p className="text-xs text-muted-foreground">Oturumun kapanması sunucudaki etkin kuralları durdurmaz.</p></section> : <>
            <section aria-label="Canlı alarm durumu" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <div className="rounded border border-border bg-surface p-4"><p className="flex items-center gap-2 text-xs text-muted-foreground"><Activity className="h-4 w-4" />Sunucu</p><p className="mt-2 text-sm font-semibold">{serviceLabel}</p><p className="mt-1 text-xs text-muted-foreground">Son tur: {timeLabel(runtime?.last_cycle_at)}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Son kontrol turu</p><p className="mt-2 text-sm font-semibold">{statistic(runtime?.evaluation?.ready)} hazır / {statistic(runtime?.evaluation?.checked)} kontrol</p><p className="mt-1 text-xs text-muted-foreground">Toplam {statistic(runtime?.evaluation?.total)} eşleşme · Bekleyen kontrol: {statistic(runtime?.evaluation?.backlog)}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Fiyat takibi</p><p className="mt-2 text-sm font-semibold">{statistic(market.fresh_symbols ?? market.ready_symbols)} güncel / {statistic(market.tracked_symbols ?? market.symbol_count)} sembol</p><p className="mt-1 text-xs text-muted-foreground">{typeof market.state === "string" ? ({ ok: "Taze fiyat alınıyor", waiting: "İlk fiyat bekleniyor", warming: "Veri hazırlanıyor", auth_required: "Hesap bağlantısını doğrulayın", storage_error: "Veri kaydı bekletiliyor", error: "Bağlantı sorunu", running: "Veri takibi açık", connected: "Bağlantı açık", unavailable: "Veri bekleniyor", disabled: "Veri takibi kapalı", reconnecting: "Yeniden bağlanıyor" }[market.state] ?? "Durum ayrıntılarını inceleyin") : "İlk veri bekleniyor"}</p></div>
                <div className="rounded border border-border bg-surface p-4"><p className="text-xs text-muted-foreground">Telegram kuyruğu</p><p className="mt-2 text-sm font-semibold">{statistic(runtime?.delivery?.pending)} bekleyen · {statistic(runtime?.delivery?.failed)} başarısız</p><p className="mt-1 text-xs text-muted-foreground">{runtime?.telegram_configured ? "Sunucudaki Telegram hedefi hazır" : "Telegram bağlantı durumu bekleniyor"}</p></div>
            </section>
            <p className="text-xs leading-relaxed text-muted-foreground">Ekran saniyede bir yenilenir. Fiyat koşulları yeni fiyatları, teknik koşullar sağlayıcı mumlarını izler. Geçmiş mumlar yalnız etkin alarm koşulları ve yakın zamanda açılan grafikler için istenir. Teknik veri yenileme hedefi 1 dakikalık mumlarda 30 saniye, diğer periyotlarda 60 saniyedir; yoğunlukta uzayabilir. Seans dışında BIST&apos;te yeni işlem fiyatı oluşmayabilir. Tam piyasa kapsamı ve sürekli gecikmesiz veri doğrulanmadı.</p>
            <details className="rounded border border-border bg-surface p-3 text-xs">
                <summary className="cursor-pointer">Veri kapsamı ve bağlantı ayrıntıları</summary>
                <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><p>BIST evreni: <strong>{statistic(market.universe_count)}</strong></p><p>Abone olunan: <strong>{statistic(market.subscribed_symbols)}</strong></p><p>Bayat / beklenen fiyat: <strong>{statistic(market.stale_symbols)}</strong></p><p>Yeniden bağlantı: <strong>{statistic(market.reconnect_attempts)}</strong></p><p>Alarmın istediği standart seri: <strong>{statistic(market.history_alarm_series)}</strong></p><p>Yalnız açık grafiğin istediği seri: <strong>{statistic(market.history_chart_series)}</strong></p><p>Hazır standart mum serisi: <strong>{statistic(market.history_ready)}</strong></p><p>Bekleyen standart mum serisi: <strong>{statistic(market.history_pending)}</strong></p><p>İstenen / planlanan standart mum serisi: <strong>{statistic(market.history_requested)} / {statistic(market.history_scheduled)}</strong></p><p>En uzun mum sırası bekleyişi: <strong>{statistic(market.history_oldest_pending_seconds)} sn</strong></p><p>Standart gösterge değerleri: <strong>{statistic(market.indicator_value_count)}</strong></p><p>En eski mum alımı: <strong>{statistic(market.oldest_history_age_seconds)} sn</strong></p><p>Fiyat alınma yaşı: <strong>{statistic(market.quote_age_seconds)} sn</strong></p><p>Kaynak zamanının yaşı: <strong>{statistic(market.source_age_seconds)} sn</strong></p></div>
                <section aria-label="Özel gösterge hesapları" className="mt-3 space-y-3 rounded border border-border p-3">
                    <h3 className="font-semibold">Özel gösterge hesapları</h3>
                    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        <p>Hesaplayıcı: <strong>{customStatus.running === true ? "Çalışıyor" : customStatus.running === false ? "Kapalı" : "Durum bekleniyor"}</strong></p>
                        <p>Farklı ayar kümesi: <strong>{statistic(customStatus.configured)}</strong></p>
                        <p>Kapasiteye takılan ayar kümesi: <strong>{statistic(customStatus.blocked_configurations)}</strong></p>
                        <p>İstenen kural / sembol hesabı: <strong>{statistic(customStatus.requested_rule_symbols)}</strong></p>
                        <p>Bekleyen veya bayat hesap: <strong>{statistic(customStatus.pending_or_stale_rule_symbols)}</strong></p>
                        <p>Önbellekteki hesap kaydı: <strong>{statistic(customStatus.results)}</strong></p>
                        <p>En eski sonuç yaşı: <strong>{statistic(customStatus.oldest_result_age_seconds)} sn</strong></p>
                        <p>Son hesaplama süresi: <strong>{statistic(customStatus.last_cycle_seconds)} sn</strong></p>
                        <p>Son tamamlanan hesap: <strong>{timeLabel(typeof customStatus.last_completed_at === "string" ? customStatus.last_completed_at : null)}</strong></p>
                    </div>
                    <p className="leading-relaxed text-muted-foreground">En fazla 256 farklı etkin hesap ayarı izlenir. Aynı gösterge, periyot ve hesaplama ayarlarını kullanan kurallar ortak hesabı paylaşır.</p>
                    {typeof customStatus.blocked_configurations === "number" && customStatus.blocked_configurations > 0 && <p role="alert" className="text-warning">Kapasite sınırına takılan {statistic(customStatus.blocked_configurations)} ayar kümesi hesaplanmıyor; bu çıktıları kullanan alarmlar çalışmaz. Kullanılmayan alarmları duraklatın veya aynı hesaplama ayarlarını paylaşın.</p>}
                    <p className="leading-relaxed text-muted-foreground">Özel gösterge yenileme hedefi {typeof customStatus.refresh_target_seconds === "number" ? statistic(customStatus.refresh_target_seconds) : "varsayılan 30"} saniyedir; izleme listelerindeki yoğunluk ve kuyruk bu süreyi uzatabilir. Bütün sembollerin aynı anda değerlendirilmesi garanti edilmez. Önbellek sayısı güncel veya hazır hesap sayısı değildir.</p>
                    {typeof customStatus.last_error === "string" && customStatus.last_error && <p role="alert" className="text-loss">{customStatus.last_error}</p>}
                </section>
                {typeof market.message === "string" && <p className="mt-3 text-muted-foreground">{market.message}</p>}
                <p className="mt-3 leading-relaxed text-muted-foreground">Standart mum okuyucusu sonraki gerçek mumu bekleyebilir; özel göstergeler sağlayıcı seans/kapanış bilgisini ayrıca doğrular. Yoğunlukta aynı sembolün güncellemeleri birleştirilir; bu ekran her işlemin veya her alarmın bir saniyede tamamlandığına dair garanti vermez.</p>
            </details>
            {(error || rules.isError || status.isError || runtime?.last_error) && <p role="alert" className="rounded border border-loss/40 bg-loss/5 p-3 text-sm">{error || (rules.isError ? readableError(rules.error) : status.isError ? "Canlı durum yenilenemedi; son kayıtlar güncel olmayabilir." : runtime?.last_error)}</p>}
            {notice && <p role="status" className="rounded border border-border bg-surface p-3 text-sm">{notice}</p>}
            <section id="watchlists" className="space-y-4 rounded border border-border bg-surface p-4">
                <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-sm font-semibold text-foreground"><List className="mr-2 inline h-4 w-4" />Sunucudaki izleme listeleri ({watchlists.data?.watchlists.length ?? "—"})</h2><Button variant="outline" size="sm" disabled={pending} onClick={() => setWatchlistDraft({ name: "", bist: "", crypto: "" })}>Yeni liste</Button></div>
                <p className="text-xs leading-relaxed text-muted-foreground">BIST hisseleri ve Binance USDT çiftleri aynı listede olabilir. Her listeye birden fazla fiyat veya teknik koşul bağlayabilirsiniz. Üye değişince bağlı alarmlar yeni üyeleri kullanır; eski bekleyen bildirimler iptal edilir. Liste kaydetmek tek başına alarm başlatmaz.</p>
                {watchlists.isLoading && <p role="status" className="text-sm">Listeler yükleniyor…</p>}
                {watchlists.isError && <p role="alert" className="text-sm text-loss">İzleme listeleri yenilenemedi; görünen son kayıtlar güncel olmayabilir. <button className="underline" onClick={() => void watchlists.refetch()}>Yeniden dene</button></p>}
                <label className="block max-w-md text-sm"><span className="sr-only">Sunucu listelerinde ara</span><Input placeholder="Liste adı ara…" value={listSearch} onChange={e => { setListSearch(e.target.value); setListPage(0) }} /></label>
                {matchingLists.slice(safeListPage * 20, (safeListPage + 1) * 20).map(list => <div key={list.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3 text-sm"><button className="min-w-0 break-words text-left" aria-pressed={selectedListId === list.id} onClick={() => selectList(list)}><span className="font-medium">{list.name}</span><span className="ml-2 text-xs text-muted-foreground">{list.symbols.length} sembol · {(rules.data?.rules ?? []).filter(rule => rule.watchlist_id === list.id).length} bağlı alarm</span></button><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={pending} onClick={() => newListAlarm(list, "technical")}>Alarm ekle</Button><Button variant="outline" size="sm" disabled={pending} onClick={() => editWatchlist(list)}>Düzenle</Button><Button variant="outline" size="sm" disabled={pending} onClick={() => setDeleting({ kind: "watchlist", id: list.id, name: list.name })}>Sil</Button></div></div>)}
                {matchingLists.length > 20 && <nav className="flex items-center gap-3 text-xs" aria-label="Sunucu listeleri sayfaları"><Button variant="outline" disabled={safeListPage === 0} onClick={() => setListPage(safeListPage - 1)}>Önceki</Button><span>{safeListPage + 1} / {Math.ceil(matchingLists.length / 20)}</span><Button variant="outline" disabled={(safeListPage + 1) * 20 >= matchingLists.length} onClick={() => setListPage(safeListPage + 1)}>Sonraki</Button></nav>}
                {localLists.length > 0 && <details className="rounded border border-border p-3"><summary className="cursor-pointer text-xs">Eski tarayıcı listesini elle kopyala</summary><p className="my-2 text-xs text-muted-foreground">Yalnız liste adı ve BIST/Binance USDT üyeleri yeni kayda kopyalanır. Yerel liste, notlar ve eski alarmlar korunur; otomatik taşınmaz veya etkinleştirilmez.</p><label className="block max-w-md space-y-1 text-xs"><span>Tarayıcıdaki listeden kopyala</span><Select disabled={pending} value="" onChange={e => { const list = localLists.find(item => item.id === e.target.value); if (list) setWatchlistDraft({ name: list.name, bist: list.rows.filter(row => row.kind === "symbol" && row.marketType === "BIST").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", "), crypto: list.rows.filter(row => row.kind === "symbol" && row.marketType === "Kripto").map(row => row.kind === "symbol" ? row.rawSymbol : "").join(", ") }) }}><option value="">Kaynak liste seç</option>{localLists.map(list => <option key={list.id} value={list.id}>{list.name}{list.id.startsWith("scanner:") ? " (eski tarayıcı)" : ""}</option>)}</Select></label></details>}
                {watchlistDraft && <form onSubmit={saveWatchlist} className="space-y-3 border-t border-border pt-3"><h3 className="text-sm font-semibold text-foreground">{watchlistDraft.id ? "Listeyi düzenle" : "Yeni sunucu listesi"}</h3><fieldset disabled={pending} className="space-y-3"><div className="flex flex-wrap gap-2"><Button type="button" variant="outline" size="sm" onClick={() => addUniverse("BIST")}>Tüm BIST kodlarını ekle</Button><Button type="button" variant="outline" size="sm" onClick={() => addUniverse("Kripto")}>Binance USDT çiftlerini ekle</Button></div><p className="text-xs text-muted-foreground">Bu düğmeler o anda kaynaktan gelen kodları forma ekler; mevcut üyeleri silmez, listeyi kaydetmez. Kaydedilen üyeler sabittir. Dinamik tüm BIST takibi için alarm formunda ilgili kapsamı seçin.</p><label className="block space-y-1 text-sm"><span>Liste adı</span><Input required maxLength={80} value={watchlistDraft.name} onChange={e => setWatchlistDraft({ ...watchlistDraft, name: e.target.value })} /></label><label className="block space-y-1 text-sm"><span>BIST hisseleri</span><textarea className="min-h-20 w-full rounded border border-border bg-background p-2" value={watchlistDraft.bist} onChange={e => setWatchlistDraft({ ...watchlistDraft, bist: e.target.value })} placeholder="THYAO, ASELS, GARAN" /></label><label className="block space-y-1 text-sm"><span>Binance USDT çiftleri</span><Input value={watchlistDraft.crypto} onChange={e => setWatchlistDraft({ ...watchlistDraft, crypto: e.target.value })} placeholder="BTCUSDT, ETHUSDT" /></label><p className="text-xs text-muted-foreground">BIST için veri sağlayıcınızın desteklediği hisse kodlarını, kripto için Binance USDT çiftlerini kullanın. Sembol kaydetmek veri erişimini doğrulamaz; desteklenmeyen sembol veri bekler.</p><div className="flex gap-2"><Button type="submit">Listeyi kaydet</Button><Button type="button" variant="outline" onClick={() => setWatchlistDraft(null)}>Vazgeç</Button></div></fieldset></form>}
            </section>
            <section className="space-y-4">
                {selectedList && <section className="space-y-3 rounded border border-primary/30 bg-surface p-4" aria-label="Seçilen liste ayrıntısı"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="break-words text-base font-semibold text-foreground">{selectedList.name}</h2><Button variant="ghost" size="sm" onClick={() => { setSelectedListId(""); setPage(0) }}>Liste filtresini kaldır</Button></div><p className="text-xs text-muted-foreground">{selectedList.symbols.filter(item => item.market_type === "BIST").length} BIST · {selectedList.symbols.filter(item => item.market_type === "Kripto").length} Binance USDT · {selectedRules.length} bağlı alarm. Her kural listedeki her sembole ayrı uygulanır.</p><div className="flex flex-wrap gap-2"><Button variant="outline" disabled={pending || !selectedList.symbols.length} onClick={() => newListAlarm(selectedList, "price")}>Fiyat koşulu ekle</Button><Button variant="outline" disabled={pending || !selectedList.symbols.length} onClick={() => newListAlarm(selectedList, "technical")}>Teknik koşul ekle</Button><Link href={serverWatchlistHref(selectedList.id, "chart")} className="inline-flex min-h-11 items-center px-2 text-xs text-primary underline">Bu listeyi grafikte aç</Link></div><details className="text-xs"><summary className="cursor-pointer">Liste üyeleri ({selectedList.symbols.length})</summary><p className="mt-2 max-h-36 overflow-y-auto break-words leading-relaxed text-muted-foreground">{selectedList.symbols.map(item => `${item.symbol} (${item.market_type})`).join(", ") || "Liste boş."}</p></details></section>}
                {selectedListId && !selectedList && !watchlists.isLoading && <p role="status" className="text-sm">Seçilen liste artık bulunamıyor. <button className="underline" onClick={() => setSelectedListId("")}>Liste filtresini kaldır</button></p>}
                <p className="text-xs leading-relaxed text-muted-foreground">Kota sunucu genelinde her kategoride 1.000 kuraldır; duraklatılanlar da sayılır. Gösterilen kullanım hesabınıza aittir. Bir liste alarmı bir kural sayılır, ancak üye sayısı kadar ayrı kontrol gerektirir. 3.000 kuralın her sembolde aynı saniyede kontrolü garanti edilmez.</p>
                <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex flex-wrap gap-2" aria-label="Alarm türleri">{(Object.keys(CATEGORY_LABELS) as AlarmCategory[]).map(key => <Button key={key} variant={category === key ? "default" : "outline"} aria-pressed={category === key} onClick={() => { setCategory(key); setPage(0) }}>{CATEGORY_LABELS[key]} <span className="ml-2 tabular-nums">{statistic(rules.data?.usage?.[key])} / 1.000</span></Button>)}</div><div className="flex gap-2"><Button variant="outline" aria-label="Alarmları yenile" disabled={pending} onClick={() => void Promise.all([rules.refetch(), status.refetch(), events.refetch()])}><RefreshCw className="h-4 w-4" /></Button><Button disabled={pending} onClick={() => openEditor()}><Plus className="mr-2 h-4 w-4" />Yeni alarm</Button></div></div>
                {draft && <section className="rounded border border-border bg-surface p-4 sm:p-5"><h2 ref={editorRef} tabIndex={-1} className="mb-4 text-base font-semibold text-foreground">{editing ? "Alarmı düzenle" : `Yeni ${CATEGORY_LABELS[draft.category].toLocaleLowerCase("tr-TR")} alarmı`}</h2><form onSubmit={save} className="space-y-4"><fieldset disabled={pending} className="space-y-4">
                    {draft.category !== "price" && <label className="block max-w-md space-y-1 text-sm"><span>Alarm hedefi</span><Select value={draft.category === "watchlist" ? "watchlist" : "technical"} onChange={e => setDraft({ ...draft, category: e.target.value === "watchlist" ? "watchlist" : "technical", scope: e.target.value === "watchlist" ? "watchlist" : "symbols", watchlist_id: e.target.value === "watchlist" ? draft.watchlist_id : null })}><option value="technical">Seçtiğim semboller</option><option value="watchlist">İzleme listesi</option></Select></label>}
                    <div className="grid gap-4 sm:grid-cols-2"><label className="space-y-1 text-sm"><span>Alarm adı</span><Input value={draft.name} maxLength={80} required onChange={e => change("name", e.target.value)} placeholder="Örn. RSI dönüş ve trend onayı" /></label><div className="rounded border border-border p-3 text-sm">Süre: <strong>Süresiz</strong><p className="mt-1 text-xs text-muted-foreground">Sen duraklatana veya silene kadar kayıtlı kalır.</p></div>
                    {draft.category === "watchlist" && <><label className="space-y-1 text-sm"><span>İzlenecek evren</span><Select value={draft.scope} onChange={e => change("scope", e.target.value as AdvancedDraft["scope"])}><option value="watchlist">Sunucudaki izleme listesi</option><option value="all_bist">Tüm BIST hisseleri (dinamik evren)</option></Select></label>{draft.scope === "watchlist" && <label className="space-y-1 text-sm"><span>İzleme listesi</span><Select value={draft.watchlist_id ?? ""} onChange={e => change("watchlist_id", e.target.value || null)} required><option value="">Liste seç</option>{watchlists.data?.watchlists.map(list => <option key={list.id} value={list.id}>{list.name} ({list.symbols.length})</option>)}</Select></label>}</>}
                    {draft.scope === "symbols" && <><label className="space-y-1 text-sm"><span>BIST hisseleri</span><Input value={draft.bist} onChange={e => change("bist", e.target.value)} placeholder="THYAO, ASELS, GARAN" autoCapitalize="characters" /></label><label className="space-y-1 text-sm"><span>Kripto çiftleri</span><Input value={draft.crypto} onChange={e => change("crypto", e.target.value)} placeholder="BTCUSDT, ETHUSDT" autoCapitalize="characters" /></label></>}
                    <label className="space-y-1 text-sm"><span>Alarm periyodu</span><Select value={draft.timeframe} onChange={e => change("timeframe", e.target.value as AlarmTimeframe)}>{!Object.hasOwn(TIMEFRAME_LABELS, draft.timeframe) && <option value={draft.timeframe}>{draft.timeframe}</option>}{Object.entries(TIMEFRAME_LABELS).map(([tf, label]) => <option key={tf} value={tf}>{label}</option>)}</Select></label><label className="space-y-1 text-sm"><span>Değerlendirme zamanı</span><Select value={draft.trigger} onChange={e => change("trigger", e.target.value as AdvancedDraft["trigger"])}><option value="intrabar">Veri geldikçe / mum içinde</option><option value="bar_close">Yalnız kapanmış mum</option></Select></label></div>
                    {draft.scope === "watchlist" && <p className="text-xs text-muted-foreground">Bu koşul seçilen listenin {watchlists.data?.watchlists.find(list => list.id === draft.watchlist_id)?.symbols.length ?? "—"} üyesine ayrı uygulanır. Liste değişirse kapsam da değişir. Fiyat ve teknik koşullar bu liste alarmında birlikte kullanılabilir.</p>}
                    {draft.scope === "all_bist" && <p className="text-xs text-warning">Bu seçim dinamik BIST evreninin tamamına uygulanır ({statistic(market.universe_count)} aday). Daha çok geçmiş veri ve kontrol işi gerektirebilir; bütün adaylarda veri erişimi doğrulanmış değildir.</p>}
                    {draft.category !== "price" && <section className="space-y-2 rounded border border-border p-3"><h3 className="text-sm font-medium">Kendi göstergelerim</h3><p className="text-xs text-muted-foreground">Bir gösterge seçerek AL sinyali koşuluyla başla; tüm ayarlarını, yönünü ve ek koşullarını aşağıdan değiştirebilirsin. Bu düğmeler formdaki koşulu değiştirir.</p><div className="flex flex-wrap gap-2">{Object.entries(CUSTOM_INDICATOR_LABELS).map(([id, label]) => <Button key={id} type="button" variant="outline" size="sm" onClick={() => setDraft(withIndicatorPreset(draft, id))}>{label}</Button>)}</div><label className="block space-y-1 text-xs"><span>Özel alarm periyodu (gerekiyorsa)</span><Input value={draft.timeframe} onChange={e => change("timeframe", e.target.value)} placeholder="1d, 3D, 2W" /></label><p className="text-xs text-muted-foreground">N OY göstergelerinde en küçük etkin satır periyodunu kullan. Snapshot için 1d seç. AL/SAT sinyalini 1 ile karşılaştır; oy veya skor çıktısında istediğin eşiği kullan. Kapanış sinyalleri için mum başına bir kez uygundur.</p></section>}
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
                {visible.map(rule => <article key={rule.id} className="space-y-2 rounded border border-border bg-surface p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0 flex-1"><h3 className="break-words text-sm font-semibold">{rule.name}</h3><p className="mt-1 break-words text-xs leading-relaxed text-muted-foreground">{conditionLabel(rule.condition)}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" size="sm" disabled={pending} onClick={() => void mutate(async () => { await saveAdvancedAlarm({ ...writeFromAdvancedDraft(draftFromAdvancedRule(rule), rule.revision), enabled: !rule.enabled }, rule.id) })}>{rule.enabled ? "Duraklat" : "Etkinleştir"}</Button><Button variant="outline" size="icon" aria-label={`${rule.name}: düzenle`} disabled={pending} onClick={() => openEditor(rule)}><Pencil className="h-4 w-4" /></Button><Button variant="outline" size="icon" aria-label={`${rule.name}: sil`} disabled={pending} onClick={() => setDeleting({ kind: "rule", id: rule.id, name: rule.name })}><Trash2 className="h-4 w-4" /></Button></div></div><p className="break-words text-xs">{rule.scope === "all_bist" ? "Tüm BIST" : rule.scope === "watchlist" ? watchlists.data?.watchlists.find(list => list.id === rule.watchlist_id)?.name ?? "İzleme listesi" : rule.symbols.map(item => item.symbol).join(", ")} · {TIMEFRAME_LABELS[rule.timeframe] ?? rule.timeframe} · {rule.trigger === "intrabar" ? "Mum içinde" : "Mum kapanışında"} · Süresiz</p><p className="text-xs text-muted-foreground">{stateLabels[rule.state] ?? rule.state} · Son kontrol: {timeLabel(rule.last_checked_at)} · Son tetik: {timeLabel(rule.last_triggered_at)} · Telegram {rule.notify_telegram ? "açık" : "kapalı"}</p>{rule.last_error && <p className="text-xs text-loss">{rule.last_error}</p>}</article>)}
                {filtered.length > 30 && <div className="flex items-center gap-3 text-xs"><Button variant="outline" disabled={safePage === 0} onClick={() => setPage(safePage - 1)}>Önceki</Button><span>{safePage + 1} / {Math.ceil(filtered.length / 30)} · {filtered.length} alarm</span><Button variant="outline" disabled={(safePage + 1) * 30 >= filtered.length} onClick={() => setPage(safePage + 1)}>Sonraki</Button></div>}
            </section>
            <section className="space-y-3 rounded border border-border bg-surface p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="text-sm font-semibold">Canlı alarm akışı</h2><span className="text-xs text-muted-foreground">Son 100 olay · Türkiye saati · saniyede bir yenilenir</span></div>{events.isError && <p role="alert" className="text-sm text-loss">Olay akışı yenilenemedi; son kayıtlar gösteriliyor.</p>}{events.isLoading && <p role="status" className="text-xs">Olaylar yükleniyor…</p>}{events.data?.events.length === 0 && <p className="text-sm text-muted-foreground">Henüz tetiklenen alarm yok.</p>}{[...(events.data?.events ?? [])].sort((a, b) => b.id - a.id).map(event => <article key={event.id} className="space-y-1 border-t border-border pt-3 text-xs"><div className="flex flex-wrap justify-between gap-2"><p className="font-medium">{event.rule_name} · {event.symbol}</p><p className="text-muted-foreground">{timeLabel(event.created_at)}</p></div><p>Değer: {typeof event.value === "number" && Number.isFinite(event.value) ? event.value.toLocaleString("tr-TR", { maximumFractionDigits: 5 }) : "—"} · {deliveryLabels[event.delivery_status] ?? event.delivery_status} · #{event.id}</p>{event.delivery_error && <p className="text-loss">{event.delivery_error}</p>}</article>)}</section>
            <ActionDialog open={Boolean(deleting)} title={deleting?.kind === "watchlist" ? "İzleme listesini sil" : "Alarmı sil"} description={`${deleting?.name ?? ""} kaldırılacak.${deleting?.kind === "watchlist" ? " Bu listeye bağlı alarmlar duraklatılacak." : " Geçmiş olay kayıtları korunacak."}${error ? ` ${error}` : ""}`} variant="danger" confirmLabel="Sil" cancelLabel="Vazgeç" pending={pending} onConfirm={() => void remove()} onCancel={() => setDeleting(null)} />
        </>}
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground"><Link href="/alarms/legacy" className="underline">Önceki günlük sunucu alarmları</Link><Link href="/alarms/local" className="underline">Eski tarayıcı alarmları</Link><Link href="/chart" className="underline">Grafiğe dön</Link></div>
    </PageShell>
}
