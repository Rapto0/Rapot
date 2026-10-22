"use client"

import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import type { FieldRef } from "@/lib/api/advanced-alarms-api"
import { useCustomIndicatorCatalog } from "./custom-indicator-catalog"
import { CustomIndicatorInputs, customDefaults, customPolicyLabel } from "./custom-indicator-inputs"

const outputNames: Record<string, string> = {
    buy_signal: "AL (DİP) sinyali", sell_signal: "SAT (TEPE) sinyali", any_signal: "AL veya SAT sinyali",
    buy_votes: "AL oyu sayısı", sell_votes: "SAT oyu sayısı",
    active_count: "Etkin zaman dilimi sayısı", ready_count: "Hesabı hazır zaman dilimi sayısı",
    buy_reachable: "Etkin periyot sayısı AL hedefi için yeterli", sell_reachable: "Etkin periyot sayısı SAT hedefi için yeterli",
}

export function CustomIndicatorField({ value, onChange, label }: { value: FieldRef; onChange: (value: FieldRef) => void; label: string }) {
    const { query, allowed } = useCustomIndicatorCatalog()
    if (!allowed) return <p className="text-xs text-muted-foreground">Gösterge ayarları için yönetici girişi yapın.</p>
    if (query.isError) return <div role="alert" className="text-xs text-loss">Gösterge kataloğu alınamadı. <Button type="button" size="sm" variant="outline" onClick={() => void query.refetch()}>Yenile</Button></div>
    if (!query.data) return <p role="status" className="text-xs text-muted-foreground">Gösterge ayarları yükleniyor…</p>
    const spec = query.data.indicators.find(item => item.id === value.indicator)
    const selected = spec?.outputs.find(output => output.key === value.output)
    const isVotes = spec?.id.endsWith("_votes")
    const settings = spec ? { ...customDefaults(spec), ...value.inputs } : {}
    const signalHelp = spec?.id === "htf_rsi_score"
        ? "Sinyal, skor DİP veya TEPE bölgesine yeni girdiğinde oluşur. Bölge çıktısı ise skor o bölgede kaldığı sürece 1 olur."
        : spec?.id === "rsi_snapshot"
            ? "AL sinyali DİP puanı, SAT sinyali TEPE puanı kendi hedef puanına ulaştığında veya üzerine çıktığında 1 olur."
            : settings.onlyFirst
                ? "İlk sinyal seçeneği açık: AL/SAT sinyali, gereken oy koşuluna yeni girişte 1 olur. Eşik koşulu ise gereken oy sayısı sağlandığı sürece 1 kalır."
                : "İlk sinyal seçeneği kapalı: AL/SAT sinyali, ilgili yönde gereken oy sayısı sağlandığı sürece 1 olur. Eşik koşulu da aynı durumu gösterir."
    return <div className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
            <label className="space-y-1 text-xs"><span>Özel gösterge</span><Select aria-label={`${label}: özel gösterge`} value={value.indicator ?? ""} onChange={event => {
                const next = query.data.indicators.find(item => item.id === event.target.value)
                if (next) onChange({ field: "custom", indicator: next.id, output: next.outputs.find(output => output.key === "buy_signal")?.key ?? next.outputs[0].key, inputs: customDefaults(next), ...(value.timeframe ? { timeframe: value.timeframe } : {}) })
            }}><option value="">Gösterge seçin</option>{query.data.indicators.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
            {spec && <label className="space-y-1 text-xs"><span>{spec.name} çıktısı</span><Select aria-label={`${label}: gösterge çıktısı`} value={value.output ?? ""} onChange={event => onChange({ ...value, output: event.target.value })}><option value="">Çıktı seçin</option>{spec.outputs.map(output => <option key={output.key} value={output.key}>{spec.name} · {outputNames[output.key] ?? (output.key === "buy_zone" ? isVotes ? "AL eşik koşulu (en az N oy)" : "AL (DİP) bölgesi" : output.key === "sell_zone" ? isVotes ? "SAT eşik koşulu (en az N oy)" : "SAT (TEPE) bölgesi" : output.label)}{output.kind === "boolean" ? " · 1 / 0" : ""}</option>)}</Select></label>}
        </div>
        {spec && <>
            <div className="space-y-1 rounded border border-border p-3 text-xs" aria-live="polite">
                <p>Bu koşul yalnız <strong>{spec.name}</strong> göstergesinin aşağıdaki ayarlarla hesaplanan çıktısını okur.</p>
                <p>{signalHelp}</p>
                {selected?.kind === "boolean" && <p>1 = koşul oluştu, 0 = oluşmadı. Seçtiğiniz sinyali yakalamak için “Eşittir 1” kullanabilirsiniz.</p>}
                {(value.output === "buy_votes" || value.output === "sell_votes") && <p>Bu çıktı sinyal değil, koşulu sağlayan etkin zaman dilimlerinin sayısıdır. Örneğin en az 8 oy için “Büyük veya eşit 8” seçin.</p>}
                {(value.output === "buy_reachable" || value.output === "sell_reachable") && <p>Bu bir AL/SAT sinyali değildir; yalnız etkin zaman dilimi sayısının belirlediğiniz N hedefine yetip yetmediğini gösterir.</p>}
                {(value.output === "active_count" || value.output === "ready_count") && <p>Bu bir AL/SAT sinyali değildir; zaman dilimlerinin sayısını gösterir.</p>}
                {(value.output === "score" || value.output === "dip_score" || value.output === "top_score") && <p>Bu sayısal bir puandır. Sinyal yerine puanı seçtiğinizde karşılaştırılacak eşik değerini siz belirlersiniz.</p>}
                <p>Bildirim sıklığını alarmın tekrar ayarı belirler. Eksik veri alarm üretmez.</p>
            </div>
            <p className="text-xs text-muted-foreground">{customPolicyLabel(spec.base_policy)}</p>
            <CustomIndicatorInputs spec={spec} value={value.inputs ?? {}} onChange={inputs => onChange({ ...value, inputs })} prefix={label} />
        </>}
    </div>
}
