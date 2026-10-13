"use client"

import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import type { CustomIndicatorSpec, CustomInputs, CustomPoint } from "@/lib/api/custom-indicators-api"

export const customDefaults = (spec: CustomIndicatorSpec): CustomInputs => Object.fromEntries(spec.inputs.map(field => [field.key, field.default]))

export function validateCustomInputs(spec: CustomIndicatorSpec, draft: CustomInputs): CustomInputs {
    const result: CustomInputs = {}
    for (const field of spec.inputs) {
        const value = Object.hasOwn(draft, field.key) ? draft[field.key] : field.default
        if (field.type === "bool") {
            if (typeof value !== "boolean") throw new Error(`${field.label}: açık veya kapalı seçin.`)
            result[field.key] = value
        } else if (field.type === "int" || field.type === "float") {
            if (typeof value === "boolean" || typeof value === "string" && !value.trim()) throw new Error(`${field.label}: sayı girin.`)
            const number = Number(value)
            if (!Number.isFinite(number) || field.type === "int" && !Number.isInteger(number) || field.min !== undefined && number < field.min || field.max !== undefined && number > field.max) throw new Error(`${field.group} · ${field.label}: geçerli aralıkta ${field.type === "int" ? "tam " : ""}sayı girin.`)
            result[field.key] = number
        } else {
            if (typeof value !== "string") throw new Error(`${field.label}: metin girin.`)
            if (field.options && !field.options.some(option => (typeof option === "string" ? option : option.value) === value)) throw new Error(`${field.label}: listeden seçim yapın.`)
            if (field.type === "timeframe" && value !== "" && !/^(?:[1-9]\d{0,3}[SDWM]?|[DWM])$/.test(value)) throw new Error(`${field.group} · ${field.label}: 60, 1D, 3D, 1W veya 1M gibi Pine periyodu girin.`)
            result[field.key] = value
        }
    }
    return result
}

export function CustomIndicatorInputs({ spec, value, onChange, prefix = "Gösterge" }: { spec: CustomIndicatorSpec; value: CustomInputs; onChange: (value: CustomInputs) => void; prefix?: string }) {
    const groups = [...new Set(spec.inputs.map(field => field.group))]
    const change = (key: string, next: string | number | boolean) => onChange({ ...customDefaults(spec), ...value, [key]: next })
    return <div className="space-y-2" aria-label={`${prefix}: tüm ayarlar`}>
        {groups.map((group, index) => <details key={`${spec.id}:${group}`} open={index === 0} className="rounded border border-border p-2">
            <summary className="cursor-pointer text-xs font-medium">{group}</summary>
            <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{spec.inputs.filter(field => field.group === group).map(field => {
                const current = Object.hasOwn(value, field.key) ? value[field.key] : field.default
                const label = `${prefix}: ${field.group}: ${field.label}`
                return <label key={field.key} className="min-w-0 space-y-1 text-xs" title={field.tooltip}>
                    <span className="block">{field.label}{field.visual && <span className="ml-1 text-muted-foreground">(görünüm)</span>}</span>
                    {field.type === "bool" ? <input type="checkbox" aria-label={label} checked={current === true} onChange={event => change(field.key, event.target.checked)} className="h-5 w-5 accent-primary" />
                        : field.options ? <Select aria-label={label} value={String(current)} onChange={event => change(field.key, event.target.value)}>{field.options.map(option => <option key={typeof option === "string" ? option : option.value} value={typeof option === "string" ? option : option.value}>{typeof option === "string" ? option : option.label}</option>)}</Select>
                            : <Input aria-label={label} type={field.type === "int" || field.type === "float" ? "number" : "text"} min={field.min} max={field.max} step={field.step ?? (field.type === "int" ? 1 : "any")} value={typeof current === "boolean" || typeof current === "number" && !Number.isFinite(current) ? "" : current} onChange={event => change(field.key, field.type === "int" || field.type === "float" ? event.target.value.trim() ? Number(event.target.value) : NaN : event.target.value)} required={field.type === "int" || field.type === "float"} placeholder={field.type === "timeframe" ? "Grafik periyodu" : undefined} />}
                    {field.type === "timeframe" && <span className="block text-[10px] text-muted-foreground">60 = 1 saat · 1D = gün · 1M = ay</span>}
                </label>
            })}</div>
        </details>)}
    </div>
}

export const customPolicyLabel = (policy: CustomIndicatorSpec["base_policy"]) => policy === "daily" ? "Bu gösterge 1D grafikte çalışır; sinyali günlük kapanışta kesinleşir." : policy === "minimum" ? "Grafik periyodu, açık satırların en küçük periyoduyla aynı olmalıdır; sinyal kapanışta kesinleşir." : "Açık mumdaki skor değişebilir; geçmiş üst periyot değerleri kapanışa göre gösterilir."

export function customReceivedTime(value: string | number | null | undefined): number | null {
    const time = typeof value === "number" ? value : typeof value === "string" ? Date.parse(value) / 1000 : NaN
    return Number.isFinite(time) && time >= 0 && Number.isFinite(new Date(time * 1000).getTime()) ? time : null
}

export function customSeriesPath(points: CustomPoint[], output: string) {
    const values = points.slice(-500).filter(point => Number.isFinite(point.time))
    const finite = values.flatMap(point => typeof point.outputs[output] === "number" && Number.isFinite(point.outputs[output]) ? [point.outputs[output] as number] : [])
    if (!finite.length || !values.length) return null
    const min = Math.min(...finite), max = Math.max(...finite), low = min === max ? min - 1 : min, high = min === max ? max + 1 : max
    const start = values[0].time, end = values[values.length - 1].time
    let path = "", pen = false
    for (const point of values) {
        const value = point.outputs[output]
        if (typeof value !== "number" || !Number.isFinite(value)) { pen = false; continue }
        const x = 12 + (point.time - start) / Math.max(1, end - start) * 776
        const y = 108 - (value - low) / (high - low) * 96
        path += `${pen ? " L" : " M"}${x.toFixed(2)},${y.toFixed(2)}`
        pen = true
    }
    return { path: path.trim(), min, max, start, end, count: values.length }
}
