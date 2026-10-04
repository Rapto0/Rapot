"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import { fetchResearchCatalog } from "@/lib/api/borsapy-api"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"
import { OperationPanel } from "@/components/research/operation-panel"
import { Select } from "@/components/ui/select"

export function BorsapyScreener() {
    const { allowed, sessionKey } = usePrivateMarket()
    const router = useRouter()
    const [selected, setSelected] = useState("screener.fundamental")
    const catalog = useQuery({ queryKey: ["borsapy-catalog", sessionKey], queryFn: ({ signal }) => fetchResearchCatalog(signal), enabled: allowed, staleTime: 300_000 })
    const operations = catalog.data?.operations.filter(operation => operation.id.startsWith("screener.")) ?? []
    const operation = operations.find(item => item.id === selected)
    return <section className="space-y-3">
        <div className="flex flex-wrap items-center gap-3"><label className="space-y-1 text-sm"><span>Tarama türü</span><Select className="min-h-11" value={selected} onChange={event => setSelected(event.target.value)}>{operations.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</Select></label><p className="text-xs text-muted-foreground">Piyasa koşullarını belirleyip taramayı başlatın. Sonuçlar geçmiş COMBO/HUNTER sinyallerinden ayrıdır.</p></div>
        {catalog.isPending && <p role="status" className="text-sm text-muted-foreground">Tarama seçenekleri yükleniyor…</p>}
        {catalog.isError && <p role="alert" className="text-sm text-loss">Tarama seçenekleri alınamadı.</p>}
        {operation && <OperationPanel key={`${sessionKey}:${operation.id}`} operation={operation} onSaved={() => {}} onConnection={() => router.push("/research?tab=connection")} />}
    </section>
}
