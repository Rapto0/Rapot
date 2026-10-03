"use client"

import { useState } from "react"
import { ChevronLeft, ChevronRight, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import type { ResearchTable } from "@/lib/api/borsapy-api"
import { formatResearchValue, researchCsv, researchLabel, researchLink } from "./research-utils"

export function ResultTable({ table }: { table: ResearchTable }) {
    const [page, setPage] = useState(0)
    const [search, setSearch] = useState("")
    const rows = table.rows.filter(row => !search || table.columns.some(column => formatResearchValue(row[column]).toLocaleLowerCase("tr").includes(search.toLocaleLowerCase("tr"))))
    const pages = Math.max(1, Math.ceil(rows.length / 20))
    const currentPage = Math.min(page, pages - 1)
    function download() {
        const blob = new Blob([researchCsv(table)], { type: "text/csv;charset=utf-8" })
        const url = URL.createObjectURL(blob)
        const anchor = document.createElement("a")
        anchor.href = url
        anchor.download = `rapot-${table.name.replace(/[^a-zA-Z0-9_-]/g, "_")}.csv`
        anchor.click()
        setTimeout(() => URL.revokeObjectURL(url), 1000)
    }
    return <section className="min-w-0 overflow-hidden border border-border bg-surface" aria-label={researchLabel(table.name)}>
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border p-4">
            <div><h3 className="text-sm font-semibold capitalize">{researchLabel(table.name)}</h3><p className="mt-1 text-xs text-muted-foreground">{table.rows.length.toLocaleString("tr-TR")} kayıt alındı{table.truncated ? ` · Toplam ${table.total_rows.toLocaleString("tr-TR")} kaydın bir bölümü` : ""}</p></div>
            <div className="flex flex-wrap gap-2"><Input aria-label={`${researchLabel(table.name)} içinde ara`} placeholder="Tabloda ara…" value={search} onChange={event => { setSearch(event.target.value); setPage(0) }} className="min-h-11 w-44" /><Button className="min-h-11" variant="outline" onClick={download} disabled={!table.rows.length}><Download aria-hidden="true" />CSV indir</Button></div>
        </div>
        {table.truncated && <p className="border-b border-border bg-amber-500/5 px-4 py-2 text-xs text-amber-300">Sunucu sonuç sınırına ulaştı. CSV yalnız alınan kayıtları içerir; daha dar bir tarih veya sembol seçebilirsiniz.</p>}
        {!rows.length ? <p className="p-6 text-center text-sm text-muted-foreground">{search ? "Aramaya uyan kayıt yok." : "Bu sorgu için kayıt bulunamadı."}</p> : <div className="max-h-[540px] overflow-auto" tabIndex={0} role="region" aria-label={`${researchLabel(table.name)} veri tablosu`}>
            <table className="w-full border-collapse text-left text-xs">
                <thead className="sticky top-0 z-10 bg-raised"><tr>{table.columns.map(column => <th key={column} scope="col" className="whitespace-nowrap border-b border-border px-4 py-3 font-medium capitalize text-muted-foreground">{researchLabel(column)}</th>)}</tr></thead>
                <tbody>{rows.slice(currentPage * 20, (currentPage + 1) * 20).map((row, index) => <tr key={currentPage * 20 + index} className="border-b border-border/60 last:border-b-0 hover:bg-raised/50">{table.columns.map(column => <td key={column} className={`max-w-[32rem] px-4 py-3 align-top ${typeof row[column] === "number" ? "whitespace-nowrap font-mono tabular-nums" : "min-w-28 break-words"}`}>{researchLink(row[column]) ? <a href={researchLink(row[column])!} target="_blank" rel="noopener noreferrer" className="inline-flex min-h-8 items-center text-profit underline underline-offset-4">Kaynağı aç ↗</a> : formatResearchValue(row[column])}</td>)}</tr>)}</tbody>
            </table>
        </div>}
        <div className="flex items-center justify-between gap-2 border-t border-border px-4 py-2 text-xs text-muted-foreground"><span>{rows.length ? `${currentPage * 20 + 1}–${Math.min((currentPage + 1) * 20, rows.length)} / ${rows.length}` : "0 kayıt"}</span><div className="flex items-center gap-2"><Button variant="ghost" className="min-h-11 min-w-11" aria-label="Önceki sayfa" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft aria-hidden="true" /></Button><span>{currentPage + 1} / {pages}</span><Button variant="ghost" className="min-h-11 min-w-11" aria-label="Sonraki sayfa" disabled={currentPage + 1 >= pages} onClick={() => setPage(currentPage + 1)}><ChevronRight aria-hidden="true" /></Button></div></div>
    </section>
}
