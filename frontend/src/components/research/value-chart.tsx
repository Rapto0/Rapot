"use client"

import { useState } from "react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Select } from "@/components/ui/select"
import type { ResearchTable } from "@/lib/api/borsapy-api"
import { formatResearchValue, researchDate, researchLabel, researchSeries } from "./research-utils"

export function ValueChart({ tables }: { tables: ResearchTable[] }) {
    const candidates = tables.map((table, index) => ({ table, index, series: researchSeries(table) })).filter(item => item.series !== null)
    const [selectedTable, setSelectedTable] = useState(candidates[0]?.index ?? -1)
    const candidate = candidates.find(item => item.index === selectedTable) ?? candidates[0]
    const columns = candidate?.series?.valueColumns ?? []
    const preferred = columns.find(column => !["open", "high", "low", "close", "volume"].includes(column.toLowerCase())) ?? columns[0]
    const [selectedColumn, setSelectedColumn] = useState(preferred ?? "")
    const column = columns.includes(selectedColumn) ? selectedColumn : preferred
    if (!candidate?.series || !column) return null
    return <section className="min-w-0 border border-border bg-surface p-4" aria-label="Zaman serisi grafiği"><div className="mb-4 flex flex-wrap items-center gap-3"><h3 className="mr-auto text-sm font-medium">Zaman içinde değişim</h3>{candidates.length > 1 && <label className="flex items-center gap-2 text-xs">Tablo<Select className="min-h-11 max-w-48" value={candidate.index} onChange={event => setSelectedTable(Number(event.target.value))}>{candidates.map(item => <option key={item.index} value={item.index}>{researchLabel(item.table.name)}</option>)}</Select></label>}<label className="flex items-center gap-2 text-xs">Değer<Select className="min-h-11 max-w-48" value={column} onChange={event => setSelectedColumn(event.target.value)}>{columns.map(value => <option key={value} value={value}>{researchLabel(value)}</option>)}</Select></label></div><div className="h-72 w-full min-w-0"><ResponsiveContainer width="100%" height="100%"><AreaChart data={candidate.series.points} margin={{ top: 10, right: 8, bottom: 0, left: 10 }}><CartesianGrid stroke="#252a35" vertical={false} /><XAxis dataKey="time" tickFormatter={value => new Date(Number(value) * 1000).toLocaleDateString("tr-TR", { day: "numeric", month: "short", timeZone: "Europe/Istanbul" })} tick={{ fontSize: 11, fill: "#9ca3af" }} minTickGap={35} /><YAxis domain={["auto", "auto"]} tickFormatter={value => Number(value).toLocaleString("tr-TR", { notation: "compact", maximumFractionDigits: 1 })} tick={{ fontSize: 11, fill: "#9ca3af" }} width={65} /><Tooltip labelFormatter={value => researchDate(Number(value))} formatter={value => [formatResearchValue(value), researchLabel(column)]} contentStyle={{ background: "#141720", borderColor: "#343a46", fontSize: 12 }} /><Area type="linear" dataKey={column} stroke="#34d399" fill="#34d399" fillOpacity={0.08} strokeWidth={2} isAnimationActive={false} connectNulls={false} /></AreaChart></ResponsiveContainer></div><p className="mt-2 text-xs text-muted-foreground">{candidate.table.truncated ? "Grafik, tablonun sunucudan alınan bölümüyle sınırlıdır." : "Grafik, alınan tablodaki kayıtları gösterir."} Eksik değerler birleştirilmez.</p></section>
}
