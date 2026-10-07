"use client"

import { useEffect, useRef, useState, type FormEvent } from "react"
import { Play, Plus, Square, Radio, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { fetchResearchStream, stopResearchStream, type ResearchStream, type ResearchSubscription } from "@/lib/api/borsapy-api"
import { CandleView } from "./research-chart"
import { formatResearchValue, researchDate, researchError, researchLabel, studyInputValues, type StudyInputRow } from "./research-utils"

export function StreamPanel({ initialMode = "chart" }: { initialMode?: "quote" | "chart" | "study" }) {
    const [symbol, setSymbol] = useState("THYAO")
    const [interval, setIntervalValue] = useState("1m")
    const [mode, setMode] = useState(initialMode)
    const [study, setStudy] = useState("RSI")
    const [inputs, setInputs] = useState<StudyInputRow[]>([])
    const [active, setActive] = useState<ResearchSubscription | null>(null)
    const [lastRun, setLastRun] = useState<{ mode: typeof mode; study: string } | null>(null)
    const [data, setData] = useState<ResearchStream | null>(null)
    const [error, setError] = useState("")
    const [loading, setLoading] = useState(false)
    const [stopping, setStopping] = useState(false)
    const stopPending = useRef(false)
    const subscriber = useRef<string | null>(null)
    useEffect(() => {
        if (!active) return
        const controller = new AbortController()
        let timer: ReturnType<typeof setTimeout> | undefined
        async function poll() {
            if (controller.signal.aborted || !active) return
            try {
                const result = await fetchResearchStream(active, controller.signal)
                if (!controller.signal.aborted) { setData(result); setError("") }
            } catch (cause) {
                if (!controller.signal.aborted) setError(researchError(cause))
            } finally {
                if (!controller.signal.aborted) { setLoading(false); timer = setTimeout(() => void poll(), 4000) }
            }
        }
        void poll()
        return () => {
            controller.abort()
            if (timer) clearTimeout(timer)
            // Unmount releases no other panel's subscription; the server expires this lease.
        }
    }, [active])
    function start(event: FormEvent) {
        event.preventDefault()
        if (active || stopPending.current) return
        let studyInputs: Record<string, string | number | boolean> = {}
        try { if (mode === "study") studyInputs = studyInputValues(inputs) }
        catch (cause) { setError(cause instanceof Error ? cause.message : "Gösterge parametrelerini kontrol edin."); return }
        subscriber.current ??= crypto.randomUUID()
        setError(""); setData(null); setLoading(true)
        setLastRun({ mode, study: study.trim() })
        setActive({ symbol: symbol.trim().toUpperCase(), interval, study: mode === "study" ? study.trim() : undefined, studyInputs, subscriberId: subscriber.current })
    }
    async function stop() {
        if (stopPending.current || !active) return
        const subscription = active
        stopPending.current = true
        setStopping(true); setActive(null); setLoading(false)
        try { await stopResearchStream(subscription) }
        catch (cause) { setError(`${researchError(cause)} Kullanılmayan sunucu akışı süre sonunda kapanır.`) }
        finally { stopPending.current = false; setStopping(false) }
    }
    return <section className="space-y-4" aria-labelledby="stream-title">
        <div><h2 id="stream-title" className="flex items-center gap-2 text-[16px] text-foreground font-semibold"><Radio className="h-4 w-4" aria-hidden="true" />Fiyat, mum ve Pine gösterge akışı</h2><p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">Bir sembol seçip akışı başlatın. Bu sayfa açıkken sunucudaki son sonuç yaklaşık 4 saniyede bir alınır. Veri gecikmesi, TradingView hesabınızın piyasa yetkisine bağlıdır.</p></div>
        <form onSubmit={start} className="space-y-3 border border-border bg-surface p-4">
            <fieldset disabled={Boolean(active) || stopping} className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <label className="space-y-1 text-sm"><span>BIST / VİOP sembolü</span><Input value={symbol} onChange={event => setSymbol(event.target.value)} required maxLength={80} autoCapitalize="characters" className="min-h-11" placeholder="THYAO veya VIOP:F_XU030…" /></label>
                <label className="space-y-1 text-sm"><span>İnceleme</span><Select className="min-h-11" value={mode} onChange={event => setMode(event.target.value as typeof mode)}><option value="quote">Fiyat bilgileri</option><option value="chart">Mum grafiği</option><option value="study">Pine gösterge değerleri</option></Select></label>
                <label className="space-y-1 text-sm"><span>Mum periyodu</span><Select value={interval} onChange={event => setIntervalValue(event.target.value)} className="min-h-11">{[["1m", "1 dakika"], ["5m", "5 dakika"], ["15m", "15 dakika"], ["30m", "30 dakika"], ["1h", "1 saat"], ["4h", "4 saat"], ["1d", "1 gün"], ["1wk", "1 hafta"], ["1mo", "1 ay"]].map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></label>
                {mode === "study" && <label className="space-y-1 text-sm"><span>Gösterge adı veya kimliği</span><Input className="min-h-11" value={study} onChange={event => setStudy(event.target.value)} required maxLength={120} placeholder="RSI, MACD veya PUB;…" /></label>}
            </fieldset>
            {mode === "study" && <fieldset disabled={Boolean(active) || stopping} className="space-y-2 border-t border-border pt-3"><legend className="text-sm">Gösterge parametreleri</legend><p className="text-xs text-muted-foreground">Boş bırakırsanız göstergenin varsayılanları kullanılır. Örneğin RSI için length = 14. Parametre adları göstergeye göre değişir.</p>{inputs.map((row, index) => <div key={index} className="grid gap-2 sm:grid-cols-[1fr_120px_1fr_auto]"><Input aria-label={`Parametre ${index + 1} adı`} className="min-h-11" required value={row.name} maxLength={40} placeholder="length" onChange={event => setInputs(current => current.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /><Select aria-label={`Parametre ${index + 1} türü`} className="min-h-11" value={row.type} onChange={event => setInputs(current => current.map((item, i) => i === index ? { ...item, type: event.target.value as StudyInputRow["type"], value: event.target.value === "boolean" ? "true" : "" } : item))}><option value="number">Sayı</option><option value="text">Metin</option><option value="boolean">Evet / hayır</option></Select>{row.type === "boolean" ? <Select aria-label={`Parametre ${index + 1} değeri`} className="min-h-11" value={row.value} onChange={event => setInputs(current => current.map((item, i) => i === index ? { ...item, value: event.target.value } : item))}><option value="true">Evet</option><option value="false">Hayır</option></Select> : <Input aria-label={`Parametre ${index + 1} değeri`} className="min-h-11" type={row.type === "number" ? "number" : "text"} step={row.type === "number" ? "any" : undefined} required min={row.type === "number" ? -1e7 : undefined} max={row.type === "number" ? 1e7 : undefined} maxLength={80} value={row.value} onChange={event => setInputs(current => current.map((item, i) => i === index ? { ...item, value: event.target.value } : item))} />}<Button aria-label={`Parametre ${index + 1} sil`} type="button" className="min-h-11" variant="ghost" onClick={() => setInputs(current => current.filter((_, i) => i !== index))}><Trash2 aria-hidden="true" /></Button></div>)}<Button type="button" className="min-h-11" variant="outline" disabled={inputs.length >= 16} onClick={() => setInputs(current => [...current, { name: "", type: "number", value: "" }])}><Plus aria-hidden="true" />Parametre ekle</Button></fieldset>}
            {mode === "study" && <p className="text-xs leading-relaxed text-muted-foreground">RSI, MACD, BB gibi standart göstergeleri veya hesabınızın erişebildiği PUB;/USER; kimliğini kullanın. Hesaplama TradingView’de yapılır; buraya Pine kaynak kodu yapıştırılmaz. Bu ekran kalıcı alarm kurmaz.</p>}
            <div className="flex flex-wrap items-center gap-3"><Button type="submit" className="min-h-11" disabled={Boolean(active) || stopping}><Play aria-hidden="true" />Akışı başlat</Button><Button type="button" className="min-h-11" variant="outline" disabled={!active || stopping} onClick={() => void stop()}><Square aria-hidden="true" />{stopping ? "Durduruluyor…" : "Durdur"}</Button><span role="status" className="text-xs text-muted-foreground">{active ? loading ? "İlk veri bekleniyor…" : `${active.symbol} · ${active.interval} · İzleme açık` : data ? "İzleme durdu; son alınan veri gösteriliyor." : "Akış başlatılmadı."}</span></div>
        </form>
        {data?.volume_quality && !data.volume_quality.verified && <p role="status" className="border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-300">{data.volume_quality.message}</p>}
        <div className="flex flex-wrap gap-2 text-[11px]"><span className="rounded-full border border-border px-3 py-1">Kaynak: TradingView / borsapy</span><span className="rounded-full border border-amber-500/30 bg-amber-500/5 px-3 py-1 text-amber-300">Gerçek zamanlı veri kabulü doğrulanmadı</span></div>
        {error && <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-sm text-loss">{error} {data ? "Gösterilen değerler önceki yanıta aittir." : ""}</p>}
        {data && <><div className="border border-border bg-surface p-4"><p role="status" className="text-sm">{data.message || "Sağlayıcı durumu alındı."}</p><p className="mt-2 text-xs text-muted-foreground">Sunucuya ulaşma: {researchDate(data.received_at)} · Sağlayıcı zamanı: {researchDate(data.quote?.timestamp ?? data.quote?.last_time ?? data.quote?.time)} (Türkiye)</p></div>
            {data.quote && <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{Object.entries(data.quote).filter(([key]) => !["timestamp", "received_at", "time"].includes(key)).map(([key, value]) => <div key={key} className="min-w-0 border border-border bg-surface p-4"><dt className="text-xs capitalize text-muted-foreground">{researchLabel(key)}</dt><dd className="mt-2 break-words font-mono text-sm">{formatResearchValue(value)}</dd></div>)}</dl>}
            {lastRun?.mode !== "quote" && <CandleView candles={data.candles ?? []} />}
            {lastRun?.mode === "study" && <section className="space-y-3 border border-border bg-surface p-4"><h3 className="text-sm font-medium">{lastRun.study} · Gösterge değerleri</h3>{data.study && Object.keys(data.study).length ? <dl className="grid gap-3 sm:grid-cols-3">{Object.entries(data.study).map(([key, value]) => <div key={key}><dt className="text-xs capitalize text-muted-foreground">{researchLabel(key)}</dt><dd className="mt-1 break-words font-mono text-sm">{formatResearchValue(value)}</dd></div>)}</dl> : <p className="text-sm text-muted-foreground">Henüz gösterge değeri alınmadı. Gösterge erişimi ve bağlantı durumunu kontrol edin.</p>}</section>}
        </>}
    </section>
}
