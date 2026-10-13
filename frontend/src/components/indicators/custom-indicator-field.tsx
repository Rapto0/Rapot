"use client"

import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import type { FieldRef } from "@/lib/api/advanced-alarms-api"
import { useCustomIndicatorCatalog } from "./custom-indicator-catalog"
import { CustomIndicatorInputs, customDefaults, customPolicyLabel } from "./custom-indicator-inputs"

export function CustomIndicatorField({ value, onChange, label }: { value: FieldRef; onChange: (value: FieldRef) => void; label: string }) {
    const { query, allowed } = useCustomIndicatorCatalog()
    if (!allowed) return <p className="text-xs text-muted-foreground">Gösterge ayarları için yönetici girişi yapın.</p>
    if (query.isError) return <div role="alert" className="text-xs text-loss">Gösterge kataloğu alınamadı. <Button type="button" size="sm" variant="outline" onClick={() => void query.refetch()}>Yenile</Button></div>
    if (!query.data) return <p role="status" className="text-xs text-muted-foreground">Gösterge ayarları yükleniyor…</p>
    const spec = query.data.indicators.find(item => item.id === value.indicator)
    return <div className="space-y-3">
        <div className="grid gap-2 sm:grid-cols-2">
            <label className="space-y-1 text-xs"><span>Özel gösterge</span><Select aria-label={`${label}: özel gösterge`} value={value.indicator ?? ""} onChange={event => {
                const next = query.data.indicators.find(item => item.id === event.target.value)
                if (next) onChange({ field: "custom", indicator: next.id, output: next.outputs.find(output => output.key === "buy_signal")?.key ?? next.outputs[0].key, inputs: customDefaults(next), ...(value.timeframe ? { timeframe: value.timeframe } : {}) })
            }}><option value="">Gösterge seçin</option>{query.data.indicators.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>
            {spec && <label className="space-y-1 text-xs"><span>Alarmın okuyacağı çıktı</span><Select aria-label={`${label}: gösterge çıktısı`} value={value.output ?? ""} onChange={event => onChange({ ...value, output: event.target.value })}><option value="">Çıktı seçin</option>{spec.outputs.map(output => <option key={output.key} value={output.key}>{output.label}{output.kind === "boolean" ? " · 1 / 0" : ""}</option>)}</Select></label>}
        </div>
        {spec && <>
            <p className="text-xs text-muted-foreground">{customPolicyLabel(spec.base_policy)}</p>
            <p className="text-xs text-muted-foreground">Sinyal çıktısında 1 = koşul oluştu, 0 = oluşmadı. Örneğin AL sinyali için “Eşittir 1” seçebilirsiniz. Eksik veri alarm üretmez.</p>
            <CustomIndicatorInputs spec={spec} value={value.inputs ?? {}} onChange={inputs => onChange({ ...value, inputs })} prefix={label} />
        </>}
    </div>
}
