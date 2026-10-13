"use client"

import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { fetchServerWatchlists } from "@/lib/api/advanced-alarms-api"
import { useAlarmRuntimeHealth } from "@/lib/hooks/use-health"
import { useSession } from "@/lib/hooks/use-session"
import { serverWatchlistHref } from "@/lib/server-watchlists"

export function AlarmWorkspace() {
    const session = useSession()
    const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
    const lists = useQuery({
        queryKey: ["advanced-alarm-watchlists", session?.user.username, session?.expiresAt],
        queryFn: ({ signal }) => fetchServerWatchlists(signal), enabled: allowed,
        staleTime: 30_000, refetchInterval: 30_000, refetchIntervalInBackground: false, retry: false,
    })
    const runtime = useAlarmRuntimeHealth()
    const watchlists = allowed ? lists.data?.watchlists ?? [] : []
    return <section className="space-y-4 border border-border bg-surface p-4" aria-labelledby="alarm-workspace-heading">
        <div className="flex flex-wrap items-start justify-between gap-3">
            <div><h2 id="alarm-workspace-heading" className="text-base font-semibold text-foreground">İzleme listelerim ve alarmlarım</h2><p className="mt-1 text-sm text-muted-foreground">Sembollerinizi gruplayın; fiyat ve gösterge koşullarınızı sunucuda takip edin.</p></div>
            <div className="flex flex-wrap gap-2"><Link href="/alarms?manage=watchlists#watchlists" className="inline-flex min-h-11 items-center border border-border px-3 text-xs">Liste oluştur / yönet</Link><Link href="/alarms" className="inline-flex min-h-11 items-center border border-primary/40 px-3 text-xs text-primary">Alarm merkezi</Link></div>
        </div>
        {!allowed ? <p className="text-sm text-muted-foreground">Listelerinizi ve alarm durumunu görmek için <Link className="text-primary underline" href="/login?next=%2F">yönetici girişi yapın</Link>.</p> : <>
            <p className="text-xs text-muted-foreground">Alarm motoru: {runtime.label}</p>
            {lists.isError && <div role="alert" className="text-sm text-amber-400">Listeler yenilenemedi. Önceki sonuçlar gösteriliyor. <button className="underline" onClick={() => void lists.refetch()}>Yeniden dene</button></div>}
            {lists.isLoading ? <p className="text-sm text-muted-foreground">Listeler yükleniyor…</p> : !watchlists.length && !lists.isError ? <p className="text-sm text-muted-foreground">Henüz bir sunucu listeniz yok. İlk listenizi oluşturup ardından koşullarınızı ekleyebilirsiniz.</p> : null}
            {watchlists.length > 0 && <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-3">{watchlists.slice(0, 6).map(list => <article key={list.id} className="min-w-0 space-y-2 border border-border p-3"><h3 className="break-words text-sm font-medium text-foreground">{list.name}</h3><p className="text-xs text-muted-foreground">{list.symbols.length} sembol</p><div className="flex flex-wrap gap-3 text-xs"><Link className="inline-flex min-h-11 items-center text-primary underline" href={serverWatchlistHref(list.id, "chart")}>Grafikte aç</Link><Link className="inline-flex min-h-11 items-center text-primary underline" href={serverWatchlistHref(list.id)}>Alarm ekle</Link><Link className="inline-flex min-h-11 items-center underline" href={serverWatchlistHref(list.id, "detail")}>Liste alarmları</Link></div></article>)}</div>}
            {watchlists.length > 6 && <Link href="/alarms?manage=watchlists#watchlists" className="inline-flex min-h-11 items-center text-sm text-primary underline">Tüm {watchlists.length} listeyi yönet</Link>}
        </>}
    </section>
}
