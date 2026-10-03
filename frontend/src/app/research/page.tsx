"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { ArrowUpRight, BookOpen, ChevronRight, Compass, KeyRound, Radio, RefreshCw, Search, Trash2 } from "lucide-react"
import { ActionDialog } from "@/components/ui/action-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { ConnectionPanel } from "@/components/research/connection-panel"
import { OperationPanel } from "@/components/research/operation-panel"
import { StreamPanel } from "@/components/research/stream-panel"
import { researchDate, researchError } from "@/components/research/research-utils"
import { deleteSavedResearch, fetchResearchCatalog, fetchSavedResearch, type ResearchOperation, type SavedResearch } from "@/lib/api/borsapy-api"
import { useSession } from "@/lib/hooks/use-session"

export default function ResearchPage() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : ""
    return <PageShell label="Kişisel çalışma alanı" title="Araştırma Merkezi" description="Türk piyasalarını inceleyin, verileri karşılaştırın ve araştırma ayarlarınızı kendi hesabınızda saklayın." width="wide" actions={<Link href="/chart" className="inline-flex min-h-11 items-center gap-2 rounded-sm border border-border px-3 text-xs hover:bg-raised">Grafiğe git<ArrowUpRight className="h-4 w-4" aria-hidden="true" /></Link>}>
        {!allowed ? <section className="space-y-3 border border-border bg-surface p-5"><h2 className="text-sm font-medium">Özel araştırma alanı</h2><p className="text-sm text-muted-foreground">{session ? "Bu alanı kullanmak için yönetici yetkisi gerekiyor." : "Araştırmalarınızı ve veri bağlantılarınızı yönetmek için yönetici hesabınızla giriş yapın."}</p><Link className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-sm hover:bg-raised" href="/login?next=%2Fresearch">Giriş yap</Link></section> : <ResearchWorkspace key={sessionKey} sessionKey={sessionKey} />}
    </PageShell>
}

function ResearchWorkspace({ sessionKey }: { sessionKey: string }) {
    const catalog = useQuery({ queryKey: ["research-catalog", sessionKey], queryFn: ({ signal }) => fetchResearchCatalog(signal), retry: false })
    const saved = useQuery({ queryKey: ["research-saved", sessionKey], queryFn: ({ signal }) => fetchSavedResearch(signal), retry: false })
    const [tab, setTab] = useState<"catalog" | "stream" | "connections">("catalog")
    const [group, setGroup] = useState("all")
    const [search, setSearch] = useState("")
    const [selected, setSelected] = useState<string | null>(null)
    const [preset, setPreset] = useState<{ key: number; params: Record<string, unknown> } | null>(null)
    const [streamMode, setStreamMode] = useState<"quote" | "chart" | "study">("chart")
    const [deleting, setDeleting] = useState<SavedResearch | null>(null)
    const [deletePending, setDeletePending] = useState(false)
    const [savedError, setSavedError] = useState("")
    const deleteRequest = useRef<AbortController | null>(null)
    useEffect(() => () => deleteRequest.current?.abort(), [])
    useEffect(() => {
        const initial = new URLSearchParams(window.location.search).get("tab")
        if (initial === "connection" || initial === "connections") setTab("connections")
        else if (initial === "stream") setTab("stream")
    }, [])
    const operations = catalog.data?.operations ?? []
    const groups = catalog.data?.groups ?? []
    const visible = operations.filter(operation => (group === "all" || operation.group === group) && `${operation.label} ${operation.description} ${operation.source} ${groups.find(item => item.id === operation.group)?.label ?? ""}`.toLocaleLowerCase("tr").includes(search.toLocaleLowerCase("tr")))
    const operation = operations.find(item => item.id === selected) ?? operations.find(item => item.transport !== "stream" && item.view !== "stream")
    function choose(next: ResearchOperation) {
        setSavedError(""); setPreset(null); setSelected(next.id)
        if (next.transport === "stream" || next.view === "stream") {
            setStreamMode(next.id.includes("study") ? "study" : next.id.includes("quote") ? "quote" : "chart")
            setTab("stream")
        } else setTab("catalog")
    }
    function loadSaved(item: SavedResearch) {
        if (!operations.some(operation => operation.id === item.operation)) { setSavedError("Bu kayıt için gereken özellik güncel katalogda bulunamadı."); return }
        setSavedError(""); setTab("catalog"); setSelected(item.operation); setPreset({ key: Date.now(), params: item.params })
    }
    async function removeSaved() {
        if (!deleting || deleteRequest.current) return
        const controller = new AbortController()
        deleteRequest.current = controller
        setDeletePending(true); setSavedError("")
        try {
            await deleteSavedResearch(deleting.id, controller.signal)
            if (!controller.signal.aborted) { setDeleting(null); await saved.refetch() }
        } catch (cause) { if (!controller.signal.aborted) setSavedError(researchError(cause)) }
        finally { if (!controller.signal.aborted) setDeletePending(false); if (deleteRequest.current === controller) deleteRequest.current = null }
    }
    return <>
        <section className="grid gap-3 sm:grid-cols-3" aria-label="Araştırma kapsamı">
            <div className="flex items-start gap-3 border border-border bg-surface p-4"><Compass className="mt-1 h-5 w-5 text-profit" aria-hidden="true" /><div><p className="text-sm font-medium">Tek çalışma alanı</p><p className="mt-1 text-xs text-muted-foreground">{catalog.data ? `${groups.length} başlık · ${operations.length} araştırma işlemi` : "Özellik kataloğu yükleniyor"}</p></div></div>
            <div className="flex items-start gap-3 border border-border bg-surface p-4"><BookOpen className="mt-1 h-5 w-5 text-muted-foreground" aria-hidden="true" /><div><p className="text-sm font-medium">Kaynağı görünen sonuçlar</p><p className="mt-1 text-xs text-muted-foreground">Her sorguda kaynak, alınma zamanı ve veri sınırları.</p></div></div>
            <div className="flex items-start gap-3 border border-border bg-surface p-4"><KeyRound className="mt-1 h-5 w-5 text-muted-foreground" aria-hidden="true" /><div><p className="text-sm font-medium">Kişisel bağlantılar</p><p className="mt-1 text-xs text-muted-foreground">TradingView, EVDS ve X ayarlarınızı sunucudan yönetin.</p></div></div>
        </section>
        <div className="flex flex-wrap gap-2 border border-border bg-surface p-2" role="tablist" aria-label="Araştırma alanları">{[
            { id: "catalog", label: "Araştırma araçları", icon: Compass },
            { id: "stream", label: "Veri akışı ve Pine", icon: Radio },
            { id: "connections", label: "Bağlantılar", icon: KeyRound },
        ].map(item => <button key={item.id} id={`research-tab-${item.id}`} role="tab" aria-selected={tab === item.id} aria-controls={`research-panel-${item.id}`} onClick={() => setTab(item.id as typeof tab)} className={`inline-flex min-h-11 items-center gap-2 rounded-sm border px-4 text-sm transition-colors ${tab === item.id ? "border-profit/40 bg-profit/10 text-foreground" : "border-transparent text-muted-foreground hover:bg-raised"}`}><item.icon className="h-4 w-4" aria-hidden="true" />{item.label}</button>)}</div>
        <section role="tabpanel" id={`research-panel-${tab}`} aria-labelledby={`research-tab-${tab}`} className="min-w-0">
            {tab === "connections" ? <ConnectionPanel sessionKey={sessionKey} /> : tab === "stream" ? <StreamPanel key={streamMode} initialMode={streamMode} /> : <div className="grid min-w-0 gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
                <aside className="min-w-0 space-y-3" aria-label="Araştırma seçimi">
                    <section className="border border-border bg-surface p-3"><label className="relative block"><span className="sr-only">Araştırma aracı ara</span><Search className="absolute left-3 top-3.5 h-4 w-4 text-muted-foreground" aria-hidden="true" /><Input value={search} onChange={event => setSearch(event.target.value)} placeholder="Hisse, fon, gösterge…" className="min-h-11 pl-9" /></label><div className="mt-3 flex flex-wrap gap-1.5"><button onClick={() => setGroup("all")} aria-pressed={group === "all"} className={`min-h-9 rounded-sm border px-2 text-xs ${group === "all" ? "border-foreground/40 bg-raised" : "border-border text-muted-foreground"}`}>Tümü</button>{groups.map(item => <button title={item.description} aria-pressed={group === item.id} key={item.id} onClick={() => setGroup(item.id)} className={`min-h-9 rounded-sm border px-2 text-xs ${group === item.id ? "border-foreground/40 bg-raised" : "border-border text-muted-foreground"}`}>{item.label}</button>)}</div></section>
                    {catalog.isLoading && <p role="status" className="border border-border p-4 text-sm text-muted-foreground">Araştırma araçları yükleniyor…</p>}
                    {catalog.isError && <div role="alert" className="space-y-2 border border-loss/40 p-4 text-sm"><p>{researchError(catalog.error)}</p><Button className="min-h-11" variant="outline" onClick={() => void catalog.refetch()}><RefreshCw aria-hidden="true" />Yeniden dene</Button></div>}
                    <nav className="max-h-[580px] overflow-y-auto border border-border bg-surface" aria-label="Araştırma işlemleri">{visible.map(item => <button key={item.id} type="button" onClick={() => choose(item)} aria-current={operation?.id === item.id ? "true" : undefined} className={`flex w-full items-start gap-2 border-b border-border px-4 py-3 text-left last:border-b-0 ${operation?.id === item.id ? "bg-profit/5 shadow-[inset_2px_0_0_0_var(--color-profit)]" : "hover:bg-raised"}`}><span className="min-w-0 flex-1"><span className="block text-sm font-medium">{item.label}</span><span className="mt-1 block text-[11px] text-muted-foreground">{item.source}</span></span><ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" /></button>)}{!visible.length && !catalog.isLoading && <p className="p-4 text-sm text-muted-foreground">Bu seçime uyan araştırma aracı yok.</p>}</nav>
                    <details className="border border-border bg-surface" open><summary className="cursor-pointer px-4 py-3 text-sm font-medium">Kayıtlı araştırmalar {saved.data ? `(${saved.data.length})` : ""}</summary><div className="space-y-2 border-t border-border p-3">
                        <p className="text-xs text-muted-foreground">Yüklemek yalnız formu doldurur. Veriyi almak için sorguyu ayrıca çalıştırın.</p>
                        {saved.isLoading && <p role="status" className="text-xs">Kayıtlar yükleniyor…</p>}
                        {saved.isError && <div className="text-xs text-loss"><p>Kayıtlar alınamadı.</p><Button variant="link" onClick={() => void saved.refetch()}>Yeniden dene</Button></div>}
                        {saved.data?.length === 0 && <p className="text-xs text-muted-foreground">Henüz kayıtlı araştırmanız yok.</p>}
                        {saved.data?.map(item => <div className="flex items-center gap-1 border border-border p-2" key={item.id}><button className="min-h-11 min-w-0 flex-1 text-left" onClick={() => loadSaved(item)}><span className="block break-words text-xs font-medium">{item.name}</span><span className="mt-1 block text-[10px] text-muted-foreground">{researchDate(item.updated_at)}</span></button><Button variant="ghost" className="min-h-11 min-w-11" aria-label={`${item.name} kaydını sil`} onClick={() => { setSavedError(""); setDeleting(item) }} disabled={deletePending}><Trash2 aria-hidden="true" /></Button></div>)}
                        {savedError && <p role="alert" className="text-xs text-loss">{savedError}</p>}
                    </div></details>
                    <div className="flex flex-wrap gap-x-4 gap-y-2 px-1 text-xs text-muted-foreground"><Link href="/scanner" className="underline underline-offset-4">Rapot tarayıcı</Link><Link href="/calendar" className="underline underline-offset-4">Takvim</Link><Link href="/alarms" className="underline underline-offset-4">Sunucu alarmları</Link></div>
                </aside>
                <main className="min-w-0">{operation ? <OperationPanel key={`${operation.id}:${preset?.key ?? "default"}`} operation={operation} initialParams={preset?.params} onSaved={() => void saved.refetch()} onConnection={() => setTab("connections")} /> : !catalog.isLoading && !catalog.isError ? <p className="border border-border p-6 text-sm text-muted-foreground">Sunucuda kullanılabilir araştırma aracı bulunamadı.</p> : <div className="h-48 animate-pulse border border-border bg-surface" aria-hidden="true" />}</main>
            </div>}
        </section>
        <ActionDialog open={Boolean(deleting)} title="Kayıtlı araştırmayı sil" description={deleting ? `${deleting.name} kaydı silinecek. Bu işlem yalnız kaydedilmiş araştırma ayarlarını kaldırır.${savedError ? ` ${savedError}` : ""}` : undefined} confirmLabel="Kaydı sil" cancelLabel="Vazgeç" variant="danger" pending={deletePending} onCancel={() => setDeleting(null)} onConfirm={() => void removeSaved()} />
    </>
}
