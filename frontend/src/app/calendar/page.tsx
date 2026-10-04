"use client"

import { useEffect, useMemo, useState } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { FilterChips, type FilterChipOption } from "@/components/ui/filter-chips"
import { fetchEconomicCalendar, type EconomicCalendarEvent } from "@/lib/api/client"
import { useSession } from "@/lib/hooks/use-session"
import { cn } from "@/lib/utils"

type Impact = "Düşük" | "Orta" | "Yüksek" | "Belirsiz"
type UiEvent = { id: string; date: string; time: string; country: string; impact: Impact; title: string; actual: string; forecast: string; previous: string; orderKey: string }
const IMPACT_OPTIONS: readonly FilterChipOption<string>[] = [
  { value: "all", label: "Tümü" }, { value: "Yüksek", label: "Yüksek" },
  { value: "Orta", label: "Orta" }, { value: "Düşük", label: "Düşük" },
  { value: "Belirsiz", label: "Belirsiz" },
]

export default function CalendarPage() {
  const session = useSession()
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
  const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : ""
  return <PageShell label="Takvim" title="Ekonomik takvim" description="Borsapy / Doviz.com ekonomik olayları. Türkiye ve ABD için yayımlanan takvim.">
    {!allowed ? <section className="space-y-3 border border-border bg-surface p-5">
      <p className="text-sm text-muted-foreground">{session ? "Takvim için yönetici yetkisi gerekiyor." : "Takvimi görmek için yönetici hesabınızla giriş yapın."}</p>
      <Link href="/login?next=%2Fcalendar" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-sm">Giriş yap</Link>
    </section> : <CalendarWorkspace key={sessionKey} sessionKey={sessionKey} />}
  </PageShell>
}

function CalendarWorkspace({ sessionKey }: { sessionKey: string }) {
  const [today, setToday] = useState(() => istanbulDay(new Date()))
  const [selectedDate, setSelectedDate] = useState("all")
  const [selectedImpact, setSelectedImpact] = useState("all")
  const [selectedCountry, setSelectedCountry] = useState("all")
  useEffect(() => {
    const timer = setInterval(() => setToday(istanbulDay(new Date())), 60_000)
    return () => clearInterval(timer)
  }, [])
  const toDate = addDays(today, 14)
  const query = useQuery({
    queryKey: ["calendar-page", sessionKey, today, toDate],
    queryFn: ({ signal }) => fetchEconomicCalendar({ from_date: today, to_date: toDate }, { signal }),
    refetchInterval: 60_000, staleTime: 60_000, retry: false,
  })
  const events = useMemo(() => mapCalendarEvents(query.data?.events ?? []), [query.data])
  const dateOptions = useMemo(() => [
    { value: "all", label: "Tümü" },
    ...Array.from(new Set(events.map(event => event.date))).sort().map(value => ({ value, label: dateLabel(value) })),
  ], [events])
  const countryOptions = useMemo(() => [
    { value: "all", label: "Tümü" },
    ...Array.from(new Set(events.map(event => event.country))).sort().map(value => ({ value, label: value })),
  ], [events])
  const visible = events.filter(event =>
    (selectedDate === "all" || event.date === selectedDate) &&
    (selectedImpact === "all" || event.impact === selectedImpact) &&
    (selectedCountry === "all" || event.country === selectedCountry))
  const metadata = query.data?.meta
  return <div className="space-y-3">
    <section className="space-y-2 border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">Sunucunun aldığı yanıt: {metadata ? new Date(metadata.fetched_at).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" }) : "—"} (İstanbul)</p>
        <Button type="button" size="sm" variant="outline" onClick={() => void query.refetch()} disabled={query.isFetching} aria-busy={query.isFetching} className="min-h-11 gap-1.5">
          <RefreshCw aria-hidden="true" className={cn("h-3.5 w-3.5", query.isFetching && "animate-spin")} />{query.isFetching ? "Yenileniyor…" : "Yenile"}
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">Sağlayıcı veriyi 1 saat önbellekte tutabilir. Dakikalık kontrol veya Yenile düğmesi yeni veri geldiği anlamına gelmez.</p>
      <p className="text-xs text-muted-foreground">Olay saatleri kaynaktaki haliyle gösterilir; saat dilimi doğrulanmadığı için İstanbul veya UTC saatine çevrilmez.</p>
      {metadata?.state === "stale" && <p role="status" className="text-xs text-warning">Kaynak yenilenemedi; önceki yanıt gösteriliyor. Alınma zamanını kontrol edin.</p>}
      {metadata?.warnings.filter(message => !message.includes("saat dilimi") && !message.includes("önbelleği")).map(message => <p key={message} className="text-xs text-muted-foreground">{message}</p>)}
    </section>
    <section className="flex flex-wrap gap-3 border border-border bg-surface p-3">
      <FilterChips label="Tarih" options={dateOptions} value={selectedDate} onChange={setSelectedDate} />
      <FilterChips label="Etki" options={IMPACT_OPTIONS} value={selectedImpact} onChange={setSelectedImpact} />
      <FilterChips label="Bölge" options={countryOptions} value={selectedCountry} onChange={setSelectedCountry} />
    </section>
    {query.isError && <p role="alert" className="border border-border p-4 text-sm text-loss">Takvim alınamadı. {query.error instanceof Error ? query.error.message : "Daha sonra yeniden deneyin."}</p>}
    {query.isLoading ? <p role="status" className="p-6 text-center text-sm text-muted-foreground">Takvim yükleniyor…</p> : visible.length === 0 ? <p className="border border-border p-6 text-center text-sm text-muted-foreground">{query.isError ? "Gösterilebilecek takvim yanıtı yok." : "Bu filtrelerde yayımlanmış kayıt bulunamadı. Bu sonuç kesin olarak olay olmadığı anlamına gelmez."}</p> :
      <div className="overflow-x-auto border border-border bg-surface">
        <table className="w-full min-w-[760px] text-left text-xs">
          <thead className="border-b border-border text-muted-foreground"><tr>{["Tarih / kaynak saati", "Bölge", "Etki", "Olay", "Güncel", "Tahmin", "Önceki"].map(label => <th key={label} scope="col" className="p-3 font-normal">{label}</th>)}</tr></thead>
          <tbody className="divide-y divide-border">{visible.map(event => <tr key={event.id}>
            <td className="p-3"><span className="block whitespace-nowrap">{dateLabel(event.date)}</span><span className="mono-numbers text-muted-foreground">{event.time}</span></td>
            <td className="p-3">{event.country}</td>
            <td className="p-3"><span className={cn("signal-badge", event.impact === "Yüksek" ? "signal-sell" : event.impact === "Orta" ? "signal-neutral" : "border border-border")}>{event.impact}</span></td>
            <td className="min-w-48 p-3">{event.title}</td>
            <td className="mono-numbers whitespace-nowrap p-3">{event.actual}</td>
            <td className="mono-numbers whitespace-nowrap p-3 text-muted-foreground">{event.forecast}</td>
            <td className="mono-numbers whitespace-nowrap p-3 text-muted-foreground">{event.previous}</td>
          </tr>)}</tbody>
        </table>
      </div>}
  </div>
}

function mapCalendarEvents(rows: EconomicCalendarEvent[]): UiEvent[] {
  return rows.map(item => ({
    id: item.id, date: item.date, time: item.source_time ?? "Saat belirtilmedi",
    country: item.country || "Belirtilmedi", impact: mapImpact(item.impact),
    title: item.event || "Ekonomik veri", actual: formatMetric(item.actual, item.unit),
    forecast: formatMetric(item.estimate, item.unit), previous: formatMetric(item.previous, item.unit),
    orderKey: `${item.date}T${item.source_time ?? "99:99"}`,
  })).sort((left, right) => left.orderKey.localeCompare(right.orderKey))
}

function mapImpact(value: string | null): Impact {
  if (value === "high") return "Yüksek"
  if (value === "mid" || value === "medium") return "Orta"
  if (value === "low") return "Düşük"
  return "Belirsiz"
}

function formatMetric(value: number | string | null, unit: string | null): string {
  if (value === null || value === undefined) return "—"
  if (typeof value === "string") return value || "—"
  if (!Number.isFinite(value)) return "—"
  return `${Number.isInteger(value) ? value : value.toFixed(2)}${unit || ""}`
}

function dateLabel(value: string): string {
  return new Date(`${value}T00:00:00Z`).toLocaleDateString("tr-TR", { timeZone: "UTC", day: "2-digit", month: "short" })
}

function istanbulDay(value: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit" }).format(value)
}

function addDays(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}
