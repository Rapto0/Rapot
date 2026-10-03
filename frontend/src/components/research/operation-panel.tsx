"use client"

import { useEffect, useRef, useState, type FormEvent } from "react"
import { Play, Plus, Save, Square, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { runResearchQuery, saveResearch, type ResearchOperation, type ResearchResult } from "@/lib/api/borsapy-api"
import { CandleView } from "./research-chart"
import { ResultTable } from "./result-table"
import { ValueChart } from "./value-chart"
import { availableResearchPeriods, changeResearchParam, formatResearchValue, initialResearchParams, researchDate, researchError, researchLabel, researchOptionLabel, researchParams } from "./research-utils"

type Position = { symbol: string; shares: string; cost: string; asset_type: string }
function positionsFrom(value: string): Position[] {
    try {
        const parsed: unknown = JSON.parse(value)
        if (Array.isArray(parsed) && parsed.length) return parsed.slice(0, 10).map(row => ({ symbol: String(row.symbol ?? ""), shares: String(row.shares ?? ""), cost: String(row.cost ?? ""), asset_type: String(row.asset_type ?? "stock") }))
    } catch { /* An empty draft starts with one editable row. */ }
    return [{ symbol: "", shares: "", cost: "", asset_type: "stock" }]
}
export function PositionsEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
    const positions = positionsFrom(value)
    const change = (index: number, key: keyof Position, next: string) => onChange(JSON.stringify(positions.map((row, i) => i === index ? { ...row, [key]: next } : row)))
    return <fieldset className="space-y-3 sm:col-span-2 xl:col-span-3"><legend className="mb-2 text-sm font-medium">Portföy varlıkları</legend><p className="text-xs text-muted-foreground">Maliyet, bir adet için alış fiyatıdır. En fazla 10 varlık ekleyebilirsiniz.</p>
        {positions.map((row, index) => <div className="grid gap-2 border border-border bg-background p-3 sm:grid-cols-2 xl:grid-cols-[1fr_1fr_1fr_1fr_auto]" key={index}>
            <label className="space-y-1 text-xs"><span>Varlık {index + 1}</span><Input className="min-h-11" required maxLength={40} value={row.symbol} placeholder={row.asset_type === "fx" ? "USD veya gram-altin" : "Sembol"} onChange={event => change(index, "symbol", row.asset_type === "fx" ? event.target.value : event.target.value.toUpperCase())} /></label>
            <label className="space-y-1 text-xs"><span>Varlık türü</span><Select className="min-h-11" value={row.asset_type} onChange={event => change(index, "asset_type", event.target.value)}><option value="stock">BIST hissesi</option><option value="fund">Yatırım fonu</option><option value="fx">Döviz / emtia</option><option value="crypto">Kripto</option></Select></label>
            <label className="space-y-1 text-xs"><span>Miktar</span><Input className="min-h-11" type="number" min="0.00000001" step="any" required value={row.shares} onChange={event => change(index, "shares", event.target.value)} /></label>
            <label className="space-y-1 text-xs"><span>Birim maliyet</span><Input className="min-h-11" type="number" min="0" step="any" required value={row.cost} onChange={event => change(index, "cost", event.target.value)} /></label>
            <Button type="button" variant="ghost" className="min-h-11 self-end" aria-label={`Varlık ${index + 1} satırını sil`} disabled={positions.length === 1} onClick={() => onChange(JSON.stringify(positions.filter((_, i) => i !== index)))}><Trash2 aria-hidden="true" /></Button>
        </div>)}
        <Button type="button" className="min-h-11" variant="outline" disabled={positions.length >= 10} onClick={() => onChange(JSON.stringify([...positions, { symbol: "", shares: "", cost: "", asset_type: "stock" }]))}><Plus aria-hidden="true" />Varlık ekle</Button>
    </fieldset>
}

export function OperationPanel({ operation, initialParams, onSaved, onConnection }: {
    operation: ResearchOperation;
    initialParams?: Record<string, unknown>;
    onSaved: () => void;
    onConnection: () => void;
}) {
    const [draft, setDraft] = useState<Record<string, string>>(() => ({ ...initialResearchParams(operation), ...Object.fromEntries(Object.entries(initialParams ?? {}).map(([key, value]) => [key, typeof value === "object" ? JSON.stringify(value) : String(value)])) }))
    const [result, setResult] = useState<ResearchResult | null>(null)
    const [pending, setPending] = useState(false)
    const [error, setError] = useState("")
    const [notice, setNotice] = useState("")
    const [name, setName] = useState("")
    const [resultKey, setResultKey] = useState(0)
    const request = useRef<AbortController | null>(null)
    const form = useRef<HTMLFormElement>(null)
    useEffect(() => () => request.current?.abort(), [])
    function changeDraft(name: string, value: string) { setDraft(current => changeResearchParam(operation.fields, current, name, value)); setResult(null) }
    function params() {
        const parsed = researchParams(operation.fields, draft)
        if (operation.fields.some(field => field.name === "positions")) {
            const positions = positionsFrom(draft.positions ?? "")
            if (positions.some(row => !row.symbol.trim() || !row.shares.trim() || !row.cost.trim() || !Number.isFinite(Number(row.shares)) || Number(row.shares) <= 0 || !Number.isFinite(Number(row.cost)) || Number(row.cost) < 0)) throw new Error("Portföydeki sembol, miktar ve maliyet alanlarını tamamlayın.")
            parsed.positions = positions.map(row => ({ symbol: row.symbol.trim(), shares: Number(row.shares), cost: Number(row.cost), asset_type: row.asset_type }))
        }
        return parsed
    }
    async function submit(event: FormEvent) {
        event.preventDefault()
        if (request.current) return
        let payload: Record<string, unknown>
        try { payload = params() } catch (cause) { setError(cause instanceof Error ? cause.message : "Alanları kontrol edin."); return }
        const controller = new AbortController()
        request.current = controller
        setPending(true); setError(""); setNotice(""); setResult(null)
        try {
            const next = await runResearchQuery(operation.id, payload, controller.signal)
            if (!controller.signal.aborted) { setResult(next); setResultKey(key => key + 1) }
        } catch (cause) {
            if (!controller.signal.aborted) setError(researchError(cause))
        } finally {
            if (!controller.signal.aborted) setPending(false)
            if (request.current === controller) request.current = null
        }
    }
    async function save() {
        if (request.current || !form.current?.reportValidity()) return
        if (!name.trim()) { setError("Kaydınız için bir ad girin."); return }
        let payload: Record<string, unknown>
        try { payload = params() } catch (cause) { setError(cause instanceof Error ? cause.message : "Alanları kontrol edin."); return }
        const controller = new AbortController()
        request.current = controller
        setPending(true); setError(""); setNotice("")
        try {
            await saveResearch(name.trim(), operation.id, payload, controller.signal)
            if (!controller.signal.aborted) { setNotice("Araştırma ayarlarınız sunucuya kaydedildi."); onSaved() }
        } catch (cause) { if (!controller.signal.aborted) setError(researchError(cause)) }
        finally { if (!controller.signal.aborted) setPending(false); if (request.current === controller) request.current = null }
    }
    function cancel() { request.current?.abort(); request.current = null; setPending(false); setNotice("Sonuç bekleme iptal edildi.") }
    const isBacktest = operation.view === "backtest"
    return <div className="min-w-0 space-y-4">
        <section className="border border-border bg-surface p-4 sm:p-5">
            <div className="mb-4 space-y-2"><h2 className="text-[16px] text-foreground font-semibold">{operation.label}</h2><p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">{operation.description}</p><div className="flex flex-wrap gap-2 text-[11px]"><span className="rounded-full border border-border px-3 py-1">Kaynak: {operation.source}</span>{isBacktest && <span className="rounded-full border border-amber-500/30 bg-amber-500/5 px-3 py-1 text-amber-300">Deneysel · aynı mum kapanışı</span>}</div></div>
            {Boolean(operation.requires?.length) && <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border border-border bg-raised/40 p-3 text-xs"><p>Bağlantı gereksinimi: {operation.requires?.map(value => ({ tradingview: "TradingView", evds: "TCMB EVDS anahtarı", twitter: "X / Twitter" })[value] ?? value).join(", ")}</p><Button type="button" variant="link" onClick={onConnection}>Bağlantıları yönet</Button></div>}
            <form ref={form} onSubmit={submit} aria-busy={pending} className="space-y-4">
                <fieldset disabled={pending} className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                    {operation.fields.map(field => field.name === "positions" ? <PositionsEditor key={field.name} value={draft[field.name] ?? ""} onChange={value => changeDraft(field.name, value)} /> : <label key={field.name} className={`block space-y-1 text-sm ${field.type === "textarea" ? "sm:col-span-2 xl:col-span-3" : ""}`}><span>{field.label}{field.required ? " *" : ""}</span>{field.type === "select" ? <Select className="min-h-11" name={field.name} required={field.required} value={draft[field.name] ?? ""} onChange={event => changeDraft(field.name, event.target.value)}><option value="">Seçin</option>{(field.name === "period" && draft.interval ? availableResearchPeriods(operation.fields, draft.interval) : field.options)?.map(option => <option key={option.value} value={option.value}>{researchOptionLabel(field, option.value, option.label)}</option>)}</Select> : field.type === "textarea" ? <textarea className="min-h-24 w-full rounded-sm border border-border bg-background p-3 text-sm outline-none focus:border-ring" name={field.name} maxLength={12000} required={field.required} value={draft[field.name] ?? ""} onChange={event => changeDraft(field.name, event.target.value)} /> : <Input className="min-h-11" name={field.name} type={field.type} step={field.type === "number" ? "any" : undefined} min={field.min} max={field.max} maxLength={field.type === "text" ? 1000 : undefined} required={field.required} value={draft[field.name] ?? ""} onChange={event => changeDraft(field.name, event.target.value)} />}</label>)}
                </fieldset>
                {draft.interval && operation.fields.some(field => field.name === "period") && <p className="text-xs leading-relaxed text-muted-foreground">Kısa periyotlarda geçmiş sınırı: 1 dakika → 5 gün; 5 dakika → 1 ay; 15 dakika → 3 ay; 30 dakika / 1 saat / 4 saat → 6 ay. Mum periyodunu değiştirince geçmiş aralığı uygun sınırla daraltılır.</p>}
                {isBacktest && <p className="text-xs leading-relaxed text-amber-300">Bu deneysel hesaplama sinyalin oluştuğu mumun kapanışında işlem varsayar. Rapot’un sonraki mum açılışını kullanan backtestiyle doğrudan karşılaştırılmaz; gerçek emir oluşturulmaz.</p>}
                <div className="flex flex-wrap items-center gap-2"><Button type="submit" className="min-h-11" disabled={pending}><Play aria-hidden="true" />{pending ? "İşleniyor…" : isBacktest ? "Deneyi çalıştır" : operation.view === "replay" ? "Mumları getir" : "Sonuçları getir"}</Button>{pending && <Button type="button" className="min-h-11" variant="outline" onClick={cancel}><Square aria-hidden="true" />Beklemeyi iptal et</Button>}</div>
            </form>
            <div className="mt-5 flex flex-wrap items-end gap-2 border-t border-border pt-4"><label className="flex-1 space-y-1 text-xs text-muted-foreground"><span>Bu ayarları daha sonra kullan</span><Input className="min-h-11" aria-label="Kaydedilecek araştırmanın adı" value={name} onChange={event => setName(event.target.value)} maxLength={80} placeholder="Ör. Temettü araştırmam" disabled={pending} /></label><Button className="min-h-11" type="button" variant="outline" disabled={pending} onClick={() => void save()}><Save aria-hidden="true" />Ayarları kaydet</Button></div>
        </section>
        {error && <p role="alert" className="border border-loss/40 bg-loss/5 p-4 text-sm text-loss">{error}</p>}
        {notice && <p role="status" className="border border-border bg-surface p-3 text-sm">{notice}</p>}
        {pending && <div role="status" className="animate-pulse border border-border bg-surface p-6 text-sm text-muted-foreground">Sağlayıcı yanıtı bekleniyor…</div>}
        {!result && !pending && !error && <div className="border border-dashed border-border p-8 text-center"><p className="text-sm text-muted-foreground">Alanları seçip sorguyu çalıştırın.</p><p className="mt-2 text-xs text-muted-foreground">Sonuçlar kaynağı ve alınma zamanı ile burada gösterilir.</p></div>}
        {result && <div key={resultKey} className="space-y-4">
            <div className="flex flex-wrap gap-x-5 gap-y-2 border border-border bg-surface p-3 text-xs text-muted-foreground"><span>Kaynak: {result.source}</span><span>Alınma: {researchDate(result.as_of)} (Türkiye)</span><span>Canlı piyasa kabulü doğrulanmadı</span></div>
            {result.warnings?.map((warning, index) => <p key={index} role="status" className="border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-300">{warning}</p>)}
            {Object.keys(result.summary ?? {}).length > 0 && <dl className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(result.summary).map(([key, value]) => <div key={key} className="min-w-0 border border-border bg-surface p-4"><dt className="text-xs capitalize text-muted-foreground">{researchLabel(key)}</dt><dd className="mt-2 break-words text-sm font-medium">{formatResearchValue(value)}</dd></div>)}</dl>}
            {result.candles && <CandleView candles={result.candles} replay={operation.view === "replay"} />}
            {operation.view !== "replay" && (operation.id === "ta.indicators" || !result.candles?.length || operation.view === "portfolio" || isBacktest) && <ValueChart tables={result.tables ?? []} />}
            {result.tables?.map((table, index) => <ResultTable key={`${index}-${table.name}`} table={table} />)}
            {!result.tables?.length && !result.candles?.length && !Object.keys(result.summary ?? {}).length && <p className="border border-border p-6 text-center text-sm text-muted-foreground">Bu sorgu için veri bulunamadı. Tarih aralığını ve sembolü kontrol edin.</p>}
        </div>}
    </div>
}
