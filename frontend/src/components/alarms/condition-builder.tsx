"use client"

import { Plus, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import type { AlarmCategory, AlarmField, AlarmTimeframe, CompareOp, Condition, FieldRef } from "@/lib/api/advanced-alarms-api"
import { defaultLeaf, FIELD_LABELS, isGroup, makeRef, OP_LABELS, PERIOD_FIELDS, TIMEFRAME_LABELS } from "@/lib/advanced-alarm-form"

function ReferenceEditor({ value, onChange, label, priceOnly }: { value: FieldRef; onChange: (ref: FieldRef) => void; label: string; priceOnly: boolean }) {
    return <fieldset className="grid min-w-0 gap-2 sm:grid-cols-3"><legend className="mb-1 text-xs text-muted-foreground">{label}</legend>
        <label className="space-y-1 text-xs"><span>Alan</span><Select aria-label={`${label}: alan`} value={value.field} onChange={e => onChange({ ...makeRef(e.target.value as AlarmField), ...(value.timeframe ? { timeframe: value.timeframe } : {}) })}>{Object.entries(FIELD_LABELS).filter(([field]) => !priceOnly || field === "price").map(([field, name]) => <option key={field} value={field}>{name}</option>)}</Select></label>
        {value.field !== "price" && <label className="space-y-1 text-xs"><span>Periyot</span><Select aria-label={`${label}: periyot`} value={value.timeframe ?? ""} onChange={e => { const { timeframe: _old, ...rest } = value; void _old; onChange({ ...rest, ...(e.target.value ? { timeframe: e.target.value as AlarmTimeframe } : {}) }) }}><option value="">Alarm periyodu</option>{Object.entries(TIMEFRAME_LABELS).map(([tf, name]) => <option key={tf} value={tf}>{name}</option>)}</Select></label>}
        {PERIOD_FIELDS.has(value.field) && <label className="space-y-1 text-xs"><span>Uzunluk</span><Input aria-label={`${label}: uzunluk`} type="number" min={2} max={200} value={Number.isFinite(value.period) ? value.period : ""} onChange={e => onChange({ ...value, period: e.target.valueAsNumber })} /></label>}
        {(value.field === "combo" || value.field === "hunter") && <label className="space-y-1 text-xs"><span>Skor</span><Select aria-label={`${label}: skor`} value={value.side} onChange={e => onChange({ ...value, side: e.target.value as "buy" | "sell" })}><option value="buy">Alış / dip</option><option value="sell">Satış / tepe</option></Select></label>}
    </fieldset>
}

export function ConditionBuilder({ value, onChange, category, depth = 1, path = "Koşul" }: { value: Condition; onChange: (condition: Condition) => void; category: AlarmCategory; depth?: number; path?: string }) {
    const priceOnly = category === "price"
    if (isGroup(value)) return <fieldset className="min-w-0 space-y-3 rounded border border-border bg-background/30 p-3">
        <legend className="px-1 text-xs text-muted-foreground">{path}</legend>
        <div className="flex flex-wrap items-center gap-2"><Select aria-label={`${path}: birleştirme`} value={value.op} onChange={e => onChange({ ...value, op: e.target.value as "and" | "or" })} className="w-auto"><option value="and">TÜMÜ gerçekleşsin (VE)</option><option value="or">HERHANGİ BİRİ gerçekleşsin (VEYA)</option></Select><span className="text-xs text-muted-foreground">{value.children.length} koşul</span></div>
        {value.children.map((child, index) => <div key={index} className="flex min-w-0 items-start gap-2"><div className="min-w-0 flex-1"><ConditionBuilder value={child} onChange={next => onChange({ ...value, children: value.children.map((old, i) => i === index ? next : old) })} category={category} depth={depth + 1} path={`${path} ${index + 1}`} /></div><Button type="button" variant="outline" size="icon" aria-label={`${path} ${index + 1}: kaldır`} disabled={value.children.length === 1} onClick={() => onChange({ ...value, children: value.children.filter((_, i) => i !== index) })}><Trash2 className="h-4 w-4" /></Button></div>)}
        {depth < 4 && <div className="flex flex-wrap gap-2"><Button type="button" variant="outline" size="sm" disabled={value.children.length >= 32} onClick={() => onChange({ ...value, children: [...value.children, defaultLeaf(category)] })}><Plus className="mr-1 h-3 w-3" />Koşul ekle</Button>{depth < 3 && <Button type="button" variant="outline" size="sm" onClick={() => onChange({ ...value, children: [...value.children, { op: "or", children: [defaultLeaf(category)] }] })}>VE / VEYA grubu ekle</Button>}</div>}
    </fieldset>
    return <fieldset className="min-w-0 space-y-3 rounded border border-border p-3"><legend className="px-1 text-xs text-muted-foreground">{path}</legend>
        <ReferenceEditor value={value.left} onChange={left => onChange({ ...value, left })} label={`${path} sol`} priceOnly={priceOnly} />
        <label className="block space-y-1 text-xs"><span>Karşılaştırma</span><Select aria-label={`${path}: karşılaştırma`} value={value.op} onChange={e => onChange({ ...value, op: e.target.value as CompareOp })}>{Object.entries(OP_LABELS).map(([op, label]) => <option key={op} value={op}>{label}</option>)}</Select></label>
        <div className="grid gap-2 sm:grid-cols-2"><label className="space-y-1 text-xs"><span>Karşılaştırılan değer</span><Select aria-label={`${path}: hedef türü`} value={typeof value.right === "number" ? "number" : "field"} onChange={e => onChange({ ...value, right: e.target.value === "number" ? 0 : makeRef(priceOnly ? "price" : "ema") })}><option value="number">Sabit sayı</option><option value="field">Başka alan / gösterge</option></Select></label>{typeof value.right === "number" && <label className="space-y-1 text-xs"><span>Eşik</span><Input aria-label={`${path}: eşik`} type="number" step="any" value={Number.isFinite(value.right) ? value.right : ""} onChange={e => onChange({ ...value, right: e.target.valueAsNumber })} required /></label>}</div>
        {typeof value.right !== "number" && <ReferenceEditor value={value.right} onChange={right => onChange({ ...value, right })} label={`${path} sağ`} priceOnly={priceOnly} />}
        {depth < 4 && <Button type="button" variant="ghost" size="sm" onClick={() => onChange({ op: "and", children: [value, defaultLeaf(category)] })}><Plus className="mr-1 h-3 w-3" />Bir koşulla birleştir</Button>}
    </fieldset>
}
