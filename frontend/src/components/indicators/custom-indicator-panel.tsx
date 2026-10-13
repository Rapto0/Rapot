"use client"

import { useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { useSession } from "@/lib/hooks/use-session"
import { storeCustomIndicatorPreset } from "@/lib/custom-indicator-presets"
import { previewCustomIndicator, type CustomInputs, type CustomPoint } from "@/lib/api/custom-indicators-api"
import { useCustomIndicatorCatalog } from "./custom-indicator-catalog"
import { CustomIndicatorInputs, customDefaults, customPolicyLabel, customReceivedTime, customSeriesPath, validateCustomInputs } from "./custom-indicator-inputs"

type Props = { symbol: string; market: "BIST" | "Kripto"; timeframe: string }
const numberLabel = (value: unknown) => typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("tr-TR", { maximumFractionDigits: 4 }) : typeof value === "boolean" ? value ? "Evet" : "Hayır" : value === null || value === undefined ? "—" : String(value)
const rowLabels: Record<string, string> = { slot: "Satır", timeframe: "Periyot", enabled: "Etkin", value: "Gösterge değeri", rsi: "RSI", smi: "SMI", rmi: "RMI", weight: "Ağırlık", dip_streak: "DİP serisi", top_streak: "TEPE serisi", dip_score: "DİP puanı", top_score: "TEPE puanı", buy_vote: "AL oyu", sell_vote: "SAT oyu", buy_threshold: "DİP eşiği", sell_threshold: "TEPE eşiği", ready: "Veri hazır", reason: "Açıklama", native_time: "Native mum başlangıcı", native_end: "Native mum kapanışı", observed_at: "Fiyat zamanı" }
const timeLabel = (time: number, market: Props["market"]) => new Date(time * 1000).toLocaleString("tr-TR", { timeZone: market === "BIST" ? "Europe/Istanbul" : "UTC", dateStyle: "short", timeStyle: "short" })

function ResultRows({ latest, market }: { latest: CustomPoint; market: Props["market"] }) {
    const namedValue = ["rsi", "smi", "rmi"].some(key => latest.rows.some(row => Object.hasOwn(row, key)))
    const columns = Object.keys(rowLabels).filter(key => !(key === "value" && namedValue) && latest.rows.some(row => Object.hasOwn(row, key)))
    return <div className="max-h-72 overflow-auto rounded border border-border"><table className="w-full text-left text-xs"><caption className="p-2 text-left text-muted-foreground">Zaman dilimlerinin ayrı değerleri</caption><thead><tr>{columns.map(key => <th key={key} className="whitespace-nowrap border-b border-border p-2">{rowLabels[key]}</th>)}</tr></thead><tbody>{latest.rows.map((row, index) => <tr key={index} className={row.enabled === false ? "text-muted-foreground" : ""}>{columns.map(key => <td key={key} className="whitespace-nowrap border-b border-border/30 p-2">{["native_time", "native_end", "observed_at"].includes(key) && typeof row[key] === "number" ? new Date(Number(row[key]) * 1000).toLocaleString("tr-TR", { timeZone: market === "BIST" ? "Europe/Istanbul" : "UTC", dateStyle: "short", timeStyle: "medium" }) : numberLabel(row[key])}</td>)}</tr>)}</tbody></table></div>
}

function IndicatorWorkspace({ symbol, market, timeframe, identity }: Props & { identity: string }) {
    const router = useRouter()
    const { query: catalog } = useCustomIndicatorCatalog()
    const [indicator, setIndicator] = useState("htf_rsi_score")
    const [inputs, setInputs] = useState<CustomInputs>({})
    const [baseTimeframe, setBaseTimeframe] = useState("")
    const [applied, setApplied] = useState<{ indicator: string; inputs: CustomInputs; baseTimeframe: string } | null>(null)
    const [output, setOutput] = useState("")
    const [error, setError] = useState("")
    const spec = catalog.data?.indicators.find(item => item.id === indicator)
    const payload = applied ? { indicator: applied.indicator, inputs: applied.inputs, symbol, market_type: market, chart_timeframe: applied.baseTimeframe || timeframe } : null
    const preview = useQuery({
        queryKey: ["custom-indicator-preview", identity, payload],
        queryFn: ({ signal }) => previewCustomIndicator(payload!, signal),
        enabled: payload !== null,
        refetchInterval: payload ? 1000 : false,
        refetchIntervalInBackground: false,
        gcTime: 0,
        retry: false,
    })
    const latest = preview.data?.latest
    const receivedTime = customReceivedTime(preview.data?.received_at)
    const sourceTime = customReceivedTime(preview.data?.source_timestamp)
    const receivedAge = receivedTime === null || receivedTime > Date.now() / 1000 + 5 ? null : Math.max(0, Math.floor(Date.now() / 1000 - receivedTime))
    const resultReady = !preview.isError && preview.data?.state === "ready" && latest?.ready
    const numeric = spec?.outputs.filter(item => item.kind === "number") ?? []
    const selectedOutput = numeric.some(item => item.key === output) ? output : numeric[0]?.key ?? ""
    const series = preview.data ? customSeriesPath(preview.data.points, selectedOutput) : null
    const signalHistory = preview.data?.points.filter(point => point.ready && (point.outputs.buy_signal === 1 || point.outputs.sell_signal === 1)).slice(-20).reverse() ?? []
    const dirty = Boolean(applied && spec && (baseTimeframe !== applied.baseTimeframe || JSON.stringify({ ...customDefaults(spec), ...inputs }) !== JSON.stringify(applied.inputs)))
    const showTable = (applied?.inputs.showTable ?? true) !== false
    const apply = () => {
        if (!spec) return
        try {
            if (baseTimeframe && !/^(?:[1-9]\d{0,3}[SDWM]?|[DWM])$/.test(baseTimeframe)) throw new Error("Gösterge ana periyodunu 60, 1D, 3D, 1W veya 1M gibi Pine biçiminde girin.")
            const validated = validateCustomInputs(spec, inputs)
            setApplied({ indicator: spec.id, inputs: validated, baseTimeframe }); setInputs(validated); setError("")
        }
        catch (failure) { setError(failure instanceof Error ? failure.message : "Ayarlar geçersiz.") }
    }
    const transfer = () => {
        if (!payload) return
        try {
            const token = storeCustomIndicatorPreset({ indicator: payload.indicator, inputs: payload.inputs, timeframe: payload.chart_timeframe, symbol, market_type: market }, identity)
            router.push(`/alarms?customPreset=${encodeURIComponent(token)}`)
        } catch (failure) { setError(failure instanceof Error ? failure.message : "Alarm taslağı açılamadı.") }
    }
    return <div className="space-y-3 p-3">
        <div className="flex flex-wrap items-end gap-3">
            <label className="min-w-48 flex-1 space-y-1 text-xs"><span>Sunucuda hesaplanan gösterge</span><Select aria-label="Grafik özel göstergesi" value={indicator} onChange={event => { setIndicator(event.target.value); setInputs({}); setApplied(null); setOutput(""); setError("") }}>{(catalog.data?.indicators ?? []).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
            <label className="w-44 space-y-1 text-xs"><span>Gösterge ana periyodu</span><Input aria-label="Gösterge ana periyodu" value={baseTimeframe} placeholder={`Grafik: ${timeframe}`} onChange={event => setBaseTimeframe(event.target.value)} /></label>
            <Button type="button" variant="outline" onClick={() => setBaseTimeframe("")}>Grafikteki periyodu kullan</Button>
            <Button type="button" onClick={apply} disabled={!spec}>Ayarları uygula ve izle</Button>
            {applied && <Button type="button" variant="outline" onClick={() => setApplied(null)}>Önizlemeyi durdur</Button>}
            {applied && <Button type="button" variant="outline" onClick={transfer} disabled={dirty}>Bu ayarlarla alarm oluştur</Button>}
        </div>
        <p className="text-xs text-muted-foreground">{symbol} · {market} · Grafik: {timeframe} · Gösterge: {payload?.chart_timeframe ?? (baseTimeframe || timeframe)} · Ekran önizlemesi saniyede bir yenilenir; sunucudaki alarm bu ekranı beklemeden her canlı fiyat olayında değerlendirilir. Ana periyot için 60 = saat, 3D = üç gün, 2W = iki hafta. Kalıcı alarmı <Link href={`/alarms?symbol=${encodeURIComponent(symbol)}&market=${market}`} className="text-primary underline">Alarm Merkezi&apos;nden</Link> bir izleme listesine veya sembole kurabilirsiniz.</p>
        {catalog.isError && <p role="alert" className="text-xs text-loss">Gösterge kataloğu alınamadı. <button type="button" onClick={() => void catalog.refetch()} className="underline">Yenile</button></p>}
        {!catalog.data && !catalog.isError && <p role="status" className="text-xs text-muted-foreground">Ayarlar yükleniyor…</p>}
        {spec && <>
            <p className="text-xs text-muted-foreground">{customPolicyLabel(spec.base_policy)}</p>
            <details className="rounded border border-border p-2"><summary className="cursor-pointer text-xs">Gösterge ayarları · {spec.inputs.length} seçenek</summary><div className="mt-3"><CustomIndicatorInputs spec={spec} value={inputs} onChange={setInputs} prefix="Grafik" /></div></details>
        </>}
        {error && <p role="alert" className="text-xs text-loss">{error}</p>}
        {dirty && <p role="status" className="text-xs text-warning">Ayarlar değişti. Son uygulanan ayarlar gösteriliyor; yeni değerler için “Ayarları uygula ve izle”ye basın.</p>}
        {preview.isError && <p role="alert" className="text-xs text-loss">Önizleme güncellenemedi. {preview.error instanceof Error ? preview.error.message : "Veri bağlantısını kontrol edin."}</p>}
        {payload && preview.isFetching && !preview.data && <p role="status" className="text-xs text-muted-foreground">Native mumlar ve gösterge durumu bekleniyor…</p>}
        {preview.data && <div className="space-y-3">
            <p role="status" className="text-xs">Kaynak: {preview.data.source || "Doğrulanmadı"} · {resultReady ? "Hesap hazır" : "Güncel sonuç hazır değil"}{latest ? ` · ${latest.confirmed ? "Kapanmış mum" : "Gelişen mum"} · ${timeLabel(latest.time, market)}` : ""}{preview.data.reason || latest?.reason ? ` · ${preview.data.reason || latest?.reason}` : ""}</p>
            <p className="text-xs text-muted-foreground">{receivedTime !== null && receivedAge !== null ? `Veri yaşı: ${receivedAge} saniye · Alınma: ${timeLabel(receivedTime, market)}` : "Verinin alınma zamanı doğrulanmadı."}{!resultReady && latest ? " Aşağıdaki değerler son hesaplamadır; güncel alarm koşulu olarak değerlendirilmemelidir." : ""}</p>
            <p className="text-xs text-muted-foreground">{sourceTime === null ? "Ortak fiyat gözlem zamanı doğrulanmadı." : `Bütün etkin periyotların ortak fiyat zamanı: ${new Date(sourceTime * 1000).toLocaleString("tr-TR", { timeZone: market === "BIST" ? "Europe/Istanbul" : "UTC", dateStyle: "short", timeStyle: "medium" })} · ${market === "BIST" ? "TSİ" : "UTC"}`}</p>
            {latest && spec && <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">{spec.outputs.map(item => <div key={item.key} className="rounded border border-border p-2"><dt className="text-[10px] text-muted-foreground">{item.label}</dt><dd className="mt-1 font-mono text-sm">{numberLabel(latest.outputs[item.key])}</dd></div>)}</dl>}
            {series && <div className="rounded border border-border p-2">
                <label className="flex items-center gap-2 text-xs"><span>Çizgi</span><Select aria-label="Özel gösterge çizgisi" className="max-w-72" value={selectedOutput} onChange={event => setOutput(event.target.value)}>{numeric.map(item => <option key={item.key} value={item.key}>{item.label}</option>)}</Select><span className="text-muted-foreground">{series.count} mum</span></label>
                <svg viewBox="0 0 800 120" className="mt-2 h-36 w-full" role="img" aria-label={`${spec?.name}: ${numeric.find(item => item.key === selectedOutput)?.label} geçmişi`} preserveAspectRatio="none"><path d={series.path} fill="none" stroke="currentColor" strokeWidth="1.5" className="text-primary" vectorEffect="non-scaling-stroke" /></svg>
                <div className="flex flex-wrap justify-between gap-2 text-[10px] text-muted-foreground"><span>{timeLabel(series.start, market)}</span><span>En düşük: {numberLabel(series.min)} · En yüksek: {numberLabel(series.max)}</span><span>{timeLabel(series.end, market)} · {market === "BIST" ? "TSİ" : "UTC"}</span></div>
            </div>}
            <section aria-label="Gösterge sinyal geçmişi" className="space-y-2 rounded border border-border p-2 text-xs">
                <h4 className="font-medium">Gösterge sinyal geçmişi · son 20 sinyal mumu</h4>
                <p className="text-muted-foreground">Bu işaretler hesaplanan gösterge geçmişidir; gönderilmiş alarm bildirimi değildir. Mum içindeki sinyal kapanışa kadar değişebilir. Saatler {market === "BIST" ? "TSİ" : "UTC"}.</p>
                {signalHistory.length ? <ul className="flex max-h-44 flex-wrap gap-2 overflow-auto">{signalHistory.map(point => <li key={point.time} className="flex items-center gap-2 rounded border border-border px-2 py-1"><time dateTime={new Date(point.time * 1000).toISOString()}>{timeLabel(point.time, market)}</time>{point.outputs.buy_signal === 1 && <strong className="text-profit">AL</strong>}{point.outputs.sell_signal === 1 && <strong className="text-loss">SAT</strong>}<span className="text-muted-foreground">{point.confirmed ? "Kapanmış" : "Mum içi"}</span></li>)}</ul> : <p className="text-muted-foreground">Alınan geçmişte doğrulanabilir AL/SAT işareti yok.</p>}
            </section>
            {latest && showTable && <ResultRows latest={latest} market={market} />}
        </div>}
    </div>
}

export function CustomIndicatorPanel(props: Props) {
    const session = useSession()
    const [open, setOpen] = useState(false)
    if (!session?.user.is_admin || session.user.disabled) return null
    const identity = `${session.user.username}:${session.expiresAt}`
    return <section className="shrink-0 border-t border-border" aria-label="Özel sunucu göstergeleri">
        <button type="button" onClick={() => setOpen(value => !value)} aria-expanded={open} className="flex min-h-11 w-full items-center justify-between gap-2 px-4 py-2 text-left text-sm font-medium"><span>Özel sunucu göstergeleri · RSI / SMI / RMI</span><span>{open ? "Kapat" : "Aç"}</span></button>
        {open && <IndicatorWorkspace key={identity} {...props} identity={identity} />}
    </section>
}
