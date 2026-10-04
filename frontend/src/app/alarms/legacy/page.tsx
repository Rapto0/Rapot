"use client"

import { useEffect, useRef, useState, type FormEvent } from "react"
import Link from "next/link"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell, Pencil, Plus, RefreshCw, Trash2 } from "lucide-react"
import { ActionDialog } from "@/components/ui/action-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { Select } from "@/components/ui/select"
import {
    createServerAlarm, deleteServerAlarm, fetchServerAlarmEvents, fetchServerAlarms, updateServerAlarm,
    type ServerAlarmList, type ServerAlarmRule,
} from "@/lib/api/alarms-api"
import { ApiError } from "@/lib/api/core"
import { useSession } from "@/lib/hooks/use-session"
import {
    alarmCondition, alarmPrefill, alarmWriteFromDraft, draftForRule, emptyAlarmDraft, SERVER_INDICATORS,
    type AlarmDraft,
} from "@/lib/server-alarm-form"
import { loadStoredWatchlists } from "@/lib/watchlist-alarms"

const STATE_LABELS = { pending: "İlk kontrol bekleniyor", active: "İzleniyor", error: "Kontrol hatası", paused: "Duraklatıldı" }
const DELIVERY_LABELS = { not_requested: "Telegram seçilmedi", pending: "Gönderim bekliyor", sent: "Telegram'a gönderildi", failed: "Telegram gönderilemedi" }
const dateLabel = (value: string | null) => value ? new Date(value).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" }) : "Henüz yok"
const errorLabel = (cause: unknown) => cause instanceof ApiError && cause.status === 422
    ? "Kural kabul edilmedi. Sembol, periyot, eşik ve sunucu limitlerini kontrol edin."
    : cause instanceof ApiError && cause.status >= 500 ? "Sunucuya ulaşılamadı veya geçici bir hata oluştu."
    : cause instanceof Error ? cause.message : "İşlem tamamlanamadı. Tekrar deneyin."

export default function AlarmsPage() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const queryClient = useQueryClient()
    const queryKey = ["server-alarms", session?.user.username, session?.expiresAt]
    const rules = useQuery({
        queryKey,
        queryFn: ({ signal }) => fetchServerAlarms(signal),
        enabled: allowed, refetchInterval: 15_000, retry: false,
    })
    const events = useQuery({
        queryKey: ["server-alarm-events", session?.user.username, session?.expiresAt],
        queryFn: ({ signal }) => fetchServerAlarmEvents(signal),
        enabled: allowed, refetchInterval: 15_000, retry: false,
    })
    const [draft, setDraft] = useState<AlarmDraft>(emptyAlarmDraft)
    const [formOpen, setFormOpen] = useState(false)
    const [editing, setEditing] = useState<string | null>(null)
    const [deleting, setDeleting] = useState<ServerAlarmRule | null>(null)
    const [pending, setPending] = useState(false)
    const pendingRef = useRef(false)
    const formRef = useRef<HTMLHeadingElement>(null)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const [returnTo, setReturnTo] = useState("/alarms")

    useEffect(() => {
        const search = window.location.search
        setReturnTo(`/alarms${search}`)
        if (search) {
            setDraft(alarmPrefill(search, loadStoredWatchlists()))
            setFormOpen(true)
        }
    }, [])
    useEffect(() => {
        if (formOpen) formRef.current?.focus()
    }, [formOpen, editing])

    function change<K extends keyof AlarmDraft>(key: K, value: AlarmDraft[K]) {
        setDraft(current => ({ ...current, [key]: value }))
    }

    function openEditor(rule?: ServerAlarmRule) {
        if (pendingRef.current) return
        setEditing(rule?.id ?? null)
        setDraft(rule ? draftForRule(rule) : emptyAlarmDraft())
        setError("")
        setNotice("")
        setFormOpen(true)
        formRef.current?.focus()
    }

    async function mutate(operation: () => Promise<void>) {
        if (!allowed || pendingRef.current) return
        pendingRef.current = true
        setPending(true)
        setError("")
        setNotice("")
        try { await operation() }
        catch (cause) { setError(errorLabel(cause)) }
        finally { pendingRef.current = false; setPending(false) }
    }

    function cacheRule(rule: ServerAlarmRule) {
        queryClient.setQueryData<ServerAlarmList>(queryKey, current => current ? {
            ...current, rules: [...current.rules.filter(item => item.id !== rule.id), rule],
        } : current)
    }

    async function save(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        await mutate(async () => {
            const payload = alarmWriteFromDraft(draft, rules.data?.limits.max_symbols_per_rule ?? 20)
            const saved = editing ? await updateServerAlarm(editing, payload) : await createServerAlarm(payload)
            cacheRule(saved)
            setFormOpen(false)
            setEditing(null)
            setNotice(saved.enabled ? "Alarm sunucuya kaydedildi. Çalışma durumunu aşağıdan izleyebilirsiniz." : "Alarm duraklatılmış olarak kaydedildi.")
            await rules.refetch()
        })
    }

    async function toggle(rule: ServerAlarmRule) {
        await mutate(async () => {
            const payload = alarmWriteFromDraft(draftForRule(rule), rules.data?.limits.max_symbols_per_rule ?? 20)
            const saved = await updateServerAlarm(rule.id, { ...payload, enabled: !rule.enabled })
            cacheRule(saved)
            setNotice(saved.enabled ? "Alarm etkinleştirildi." : "Alarm duraklatıldı.")
            await rules.refetch()
        })
    }

    async function remove() {
        if (!deleting) return
        const id = deleting.id
        await mutate(async () => {
            await deleteServerAlarm(id)
            queryClient.setQueryData<ServerAlarmList>(queryKey, current => current ? {
                ...current, rules: current.rules.filter(rule => rule.id !== id),
            } : current)
            setDeleting(null)
            if (editing === id) { setFormOpen(false); setEditing(null) }
            setNotice("Alarm silindi; geçmiş tetik kayıtları korunur.")
            await rules.refetch()
        })
    }

    const spec = SERVER_INDICATORS[draft.indicator]
    const runtime = rules.data?.runtime
    const subscriptionCount = rules.data?.rules.reduce((sum, rule) => sum + rule.symbols.length, 0) ?? 0
    const staleRuntime = Boolean(runtime?.last_cycle_at && Date.now() - Date.parse(runtime.last_cycle_at) > Math.max(180, runtime.poll_interval_seconds * 3) * 1000)
    const status = rules.isError ? "Durum doğrulanamadı" : !runtime ? "Durum yükleniyor"
        : !runtime.running ? "Alarm servisi çalışmıyor" : !runtime.last_cycle_at ? "İlk sunucu kontrolü bekleniyor"
            : runtime.last_cycle_error ? "Son alarm döngüsü tamamlanamadı" : staleRuntime ? "Son kontrol gecikti" : "Alarm servisi çalışıyor"

    return (
        <PageShell label="Sunucu alarmları" title="Alarm merkezi" description="Kurallar sunucuda saklanır. Alarm servisi çalışırken tarayıcınız ve bilgisayarınız kapalı olsa da kontrol edilir.">
            {!allowed ? (
                <section className="space-y-3 border border-border bg-surface p-4">
                    <p className="text-sm">{session ? "Sunucu alarmlarını yönetmek için yönetici yetkisi gerekir." : "Sunucu alarmlarınızı görmek ve düzenlemek için yönetici hesabınızla giriş yapın."}</p>
                    <Link href={`/login?next=${encodeURIComponent(returnTo)}`} className="inline-flex min-h-11 items-center rounded border border-border px-3 text-sm hover:bg-raised">Giriş yap</Link>
                    <p className="text-xs text-muted-foreground">Oturumun kapanması veya süresinin dolması, sunucuda etkin olan alarmları durdurmaz.</p>
                </section>
            ) : <>
                <section aria-label="Alarm hizmeti durumu" className="grid gap-3 border border-border bg-surface p-4 sm:grid-cols-2 lg:grid-cols-4">
                    <div><p className="text-xs text-muted-foreground">Sunucu</p><p className="mt-1 text-sm font-medium">{status}</p><p className="mt-1 text-xs text-muted-foreground">Son döngü: {dateLabel(runtime?.last_cycle_at ?? null)} (Türkiye)</p></div>
                    <div><p className="text-xs text-muted-foreground">Kurallar</p><p className="mt-1 text-sm">{rules.data ? `${rules.data.rules.length} / ${rules.data.limits.max_rules}` : "—"}</p><p className="mt-1 text-xs text-muted-foreground">{rules.data ? `${subscriptionCount} / ${rules.data.limits.max_subscriptions} sembol-kural` : ""}</p></div>
                    <div><p className="text-xs text-muted-foreground">Telegram</p><p className="mt-1 text-sm">{runtime ? runtime.telegram_configured ? "Sunucuda yapılandırılmış" : "Sunucuda yapılandırılmamış" : "—"}</p><p className="mt-1 text-xs text-muted-foreground">Bildirimler sunucuda tanımlı mevcut Telegram hedefine gider.</p></div>
                    <div className="flex flex-wrap items-center gap-2">
                        <Button variant="outline" className="min-h-11" disabled={rules.isFetching || events.isFetching || pending} onClick={() => { void rules.refetch(); void events.refetch() }}><RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />Yenile</Button>
                        <Button className="min-h-11" disabled={pending} onClick={() => openEditor()}><Plus className="mr-2 h-4 w-4" aria-hidden="true" />Yeni alarm</Button>
                    </div>
                </section>

                <p className="text-xs leading-relaxed text-muted-foreground">Yalnız kapanmış mumlar değerlendirilir. Her kontrol turundan sonra yaklaşık {runtime?.poll_interval_seconds ?? 60} saniye beklenir; tüm semboller aynı turda tamamlanamayabilir. BIST: yalnız 1 gün. Binance Spot USDT: 1 saat / 4 saat / 1 gün. BIST günlük mumları, Türkiye saatinde ertesi gün 00.00 geçince kapanmış kabul edilir. Veri veya hizmet kesintilerinde kontrol gecikebilir; geçmişte kaçırılmış mumlar geriye dönük taranmaz. Sayfadaki durum 15 saniyede bir yenilenir.</p>
                {rules.isError && <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-sm">Kurallar yenilenemedi: {errorLabel(rules.error)} {rules.data ? "Son alınan kurallar gösteriliyor; güncel durum bilinmiyor." : ""}</p>}
                {runtime?.last_cycle_error && <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-sm">{runtime.last_cycle_error}</p>}
                {error && <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-sm">{error}</p>}
                {notice && <p role="status" className="border border-border bg-surface p-3 text-sm">{notice}</p>}

                {formOpen && <section className="border border-border bg-surface p-4">
                    <h2 ref={formRef} tabIndex={-1} className="mb-3 text-base font-semibold text-foreground">{editing ? "Alarmı düzenle" : "Yeni sunucu alarmı"}</h2>
                    <form onSubmit={save} className="space-y-4" aria-busy={pending}>
                        <fieldset disabled={pending} className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            <label className="space-y-1 text-sm"><span>Alarm adı</span><Input name="name" maxLength={80} value={draft.name} onChange={event => change("name", event.target.value)} required className="min-h-11" /></label>
                            <label className="space-y-1 text-sm"><span>Gösterge</span><Select name="indicator" value={draft.indicator} className="min-h-11" onChange={event => { const indicator = event.target.value as AlarmDraft["indicator"]; setDraft(current => ({ ...current, indicator, threshold: String(SERVER_INDICATORS[indicator][current.side]) })) }}>{Object.entries(SERVER_INDICATORS).map(([value, item]) => <option key={value} value={value}>{item.label}</option>)}</Select></label>
                            <label className="space-y-1 text-sm"><span>Periyot</span><Select name="timeframe" value={draft.timeframe} className="min-h-11" onChange={event => change("timeframe", event.target.value as AlarmDraft["timeframe"])}><option value="1h">1 saat (yalnız kripto)</option><option value="4h">4 saat (yalnız kripto)</option><option value="1d">1 gün</option></Select></label>
                            <label className="space-y-1 text-sm"><span>BIST sembolleri</span><Input name="bistSymbols" value={draft.bistSymbols} onChange={event => change("bistSymbols", event.target.value)} placeholder="THYAO, ASELS" className="min-h-11" autoCapitalize="characters" /><span className="block text-xs text-muted-foreground">Yalnız 1 günlük alarmlar. Virgülle ayırın: THYAO, ASELS.</span></label>
                            <label className="space-y-1 text-sm"><span>Kripto sembolleri</span><Input name="cryptoSymbols" value={draft.cryptoSymbols} onChange={event => change("cryptoSymbols", event.target.value)} placeholder="BTCUSDT, ETHUSDT" className="min-h-11" autoCapitalize="characters" /><span className="block text-xs text-muted-foreground">Binance Spot USDT çiftleri; iki piyasada toplam en fazla {rules.data?.limits.max_symbols_per_rule ?? 20} sembol.</span></label>
                            <label className="space-y-1 text-sm"><span>Koşul yönü</span><Select name="side" value={draft.side} className="min-h-11" onChange={event => { const side = event.target.value as AlarmDraft["side"]; setDraft(current => ({ ...current, side, threshold: String(SERVER_INDICATORS[current.indicator][side]) })) }}><option value="dip">Dip / alış skoru</option><option value="top">Tepe / satış skoru</option></Select></label>
                            <label className="space-y-1 text-sm"><span>Eşik ({spec.min}–{spec.max})</span><Input name="threshold" type="number" min={spec.min} max={spec.max} step={spec.step} value={draft.threshold} onChange={event => change("threshold", event.target.value)} className="min-h-11" required /><span className="block text-xs text-muted-foreground">{alarmCondition(draft.indicator, draft.side, draft.threshold)}</span></label>
                            <label className="space-y-1 text-sm sm:col-span-2"><span>Tetikleme biçimi</span><Select name="mode" value={draft.mode} className="min-h-11" onChange={event => change("mode", event.target.value as AlarmDraft["mode"])}><option value="on_enter">Koşula girişte bir kez</option><option value="once_per_bar">Koşulu sağlayan her kapanmış mumda</option></Select><span className="block text-xs text-muted-foreground">Koşula giriş: önceki kapanmış mum koşulu sağlamazken son kapanmış mum sağlar. Zaten süren koşulda yeniden bildirim oluşmaz. Her mum: koşul devam ettikçe yeni kapanışta tekrar tetikler.</span></label>
                            <label className="flex min-h-11 items-center gap-2 text-sm"><input name="enabled" type="checkbox" checked={draft.enabled} onChange={event => change("enabled", event.target.checked)} className="h-4 w-4" />Alarm etkin</label>
                            <label className="flex min-h-11 items-center gap-2 text-sm sm:col-span-2"><input name="notify_telegram" type="checkbox" checked={draft.notify_telegram} onChange={event => change("notify_telegram", event.target.checked)} className="h-4 w-4" />Telegram&apos;a da gönder</label>
                        </fieldset>
                        {draft.notify_telegram && !runtime?.telegram_configured && <p className="text-sm text-loss">Telegram yapılandırması doğrulanamadı veya eksik. Kurulum tamamlanmadan etkin ve Telegram bildirimli bir alarm kaydedilemez. Telegram seçimini kapatabilir veya alarmı duraklatılmış kaydedebilirsiniz.</p>}
                        <p className="text-xs text-muted-foreground">Sembol listesi kaydettiğiniz haliyle sunucuda tutulur; tarayıcı izleme listesindeki sonraki değişiklikler bu alarmı değiştirmez. COMBO 4, HUNTER 15 göstergenin skorunu kullanır. Alarm hesabı sunucu göstergelerini kullanır; grafikteki hesaplamayla farklılık olabilir. Bu ekran Pine kodu çalıştırmaz.</p>
                        <div className="flex flex-wrap gap-2"><Button type="submit" className="min-h-11" disabled={pending}>{pending ? "Kaydediliyor…" : "Sunucuya kaydet"}</Button><Button type="button" variant="outline" className="min-h-11" disabled={pending} onClick={() => { setFormOpen(false); setEditing(null); setError("") }}>Vazgeç</Button></div>
                    </form>
                </section>}

                <section className="space-y-3" aria-labelledby="server-rules-heading">
                    <h2 id="server-rules-heading" className="text-base font-semibold text-foreground">Kayıtlı alarmlar</h2>
                    {rules.isLoading && <p role="status" className="text-sm text-muted-foreground">Kurallar yükleniyor…</p>}
                    {rules.data?.rules.length === 0 && <p className="border border-border bg-surface p-4 text-sm text-muted-foreground">Henüz sunucu alarmı yok. Yeni alarm düğmesiyle bir kural oluşturun.</p>}
                    {rules.data?.rules.map(rule => <article key={rule.id} className="min-w-0 space-y-2 border border-border bg-surface p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><h3 className="flex items-center gap-2 break-words text-sm font-semibold text-foreground"><Bell className="h-4 w-4 shrink-0" aria-hidden="true" />{rule.name}</h3><p className="mt-1 text-xs text-muted-foreground">{alarmCondition(rule.indicator, rule.side, rule.threshold)} · {rule.timeframe === "1d" ? "1 gün" : rule.timeframe === "4h" ? "4 saat" : "1 saat"} · {rule.mode === "on_enter" ? "Koşula girişte" : "Her kapanmış mumda"}</p></div>
                            <div className="flex flex-wrap gap-2"><Button variant="outline" className="min-h-11" disabled={pending} onClick={() => void toggle(rule)} aria-label={`${rule.name}: ${rule.enabled ? "duraklat" : "etkinleştir"}`}>{rule.enabled ? "Duraklat" : "Etkinleştir"}</Button><Button variant="outline" className="min-h-11" disabled={pending} onClick={() => openEditor(rule)} aria-label={`${rule.name}: düzenle`}><Pencil className="mr-1 h-4 w-4" aria-hidden="true" />Düzenle</Button><Button variant="outline" className="min-h-11" disabled={pending} onClick={() => setDeleting(rule)} aria-label={`${rule.name}: sil`}><Trash2 className="mr-1 h-4 w-4" aria-hidden="true" />Sil</Button></div></div>
                        <p className="break-words text-xs">{rule.symbols.map(item => `${item.symbol} (${item.market_type})`).join(", ")}</p>
                        <p className="text-xs text-muted-foreground">{STATE_LABELS[rule.state]} · Son kontrol: {dateLabel(rule.last_checked_at)} · Son tetik: {dateLabel(rule.last_triggered_at)} · Telegram: {rule.notify_telegram ? "Açık" : "Kapalı"}</p>
                        {rule.last_error && <p className="break-words text-xs text-loss">Kontrol sorunu: {rule.last_error}</p>}
                    </article>)}
                </section>

                <section className="space-y-3 border border-border bg-surface p-4" aria-labelledby="alarm-history-heading">
                    <h2 id="alarm-history-heading" className="text-base font-semibold text-foreground">Son 100 tetik</h2>
                    <p className="text-xs text-muted-foreground">Kayıt ve Telegram teslim durumları ayrıdır. Saatler Türkiye saatidir. Mum zamanı, değerlendirilen mumun başlangıcıdır. Tamamlanan kayıtlar en fazla 30 gün ve 20.000 kayıt sınırında tutulur; bu ekran son 100 kaydı gösterir.</p>
                    {events.isLoading && <p role="status" className="text-sm">Geçmiş yükleniyor…</p>}
                    {events.isError && <p role="alert" className="text-sm text-loss">Geçmiş yenilenemedi: {errorLabel(events.error)} {events.data ? "Son alınan kayıtlar gösteriliyor." : ""}</p>}
                    {events.data?.events.length === 0 && <p className="text-sm text-muted-foreground">Henüz tetik kaydı yok.</p>}
                    {events.data?.events.map(event => <article key={event.id} className="space-y-1 border-t border-border pt-3 text-xs">
                        <p className="break-words font-medium">{event.rule_name} · {event.symbol} ({event.market_type}) · {event.side === "dip" ? "Dip" : "Tepe"} · Değer: {Number.isFinite(event.value) ? event.value.toFixed(2) : "—"}</p>
                        <p className="text-muted-foreground">Tetik: {dateLabel(event.created_at)} · Mum: {dateLabel(event.bar_time)} · {event.timeframe}</p>
                        <p>{DELIVERY_LABELS[event.delivery_status]}</p>
                        {event.delivery_error && <p className="break-words text-loss">{event.delivery_error}</p>}
                    </article>)}
                </section>
                <ActionDialog open={Boolean(deleting)} title="Sunucu alarmını sil" description={deleting ? `${deleting.name} artık izlenmeyecek. Geçmiş tetik kayıtları korunacak.${error ? ` İşlem hatası: ${error}` : ""}` : undefined} variant="danger" confirmLabel="Alarmı sil" cancelLabel="Vazgeç" pending={pending} onConfirm={() => void remove()} onCancel={() => setDeleting(null)} />
            </>}
            <details className="border border-border bg-surface p-4 text-xs text-muted-foreground"><summary className="cursor-pointer py-1">Eski tarayıcı alarmları</summary><p className="mt-2">Eski kurallarınız tarayıcıda korunur; otomatik olarak sunucuya aktarılmaz. İsterseniz onları görüntüleyip yeni sunucu formunda ayrı bir kural oluşturabilirsiniz. Eski kurallar yalnız yerel alarm sayfası açıkken kontrol edilir.</p><Link href="/alarms/local" className="mt-2 inline-flex min-h-11 items-center underline">Eski yerel alarmları aç</Link></details>
        </PageShell>
    )
}
