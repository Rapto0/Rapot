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
type WindowPreset = "last7" | "next7" | "next14" | "next30"
type UiEvent = { id: string; date: string; time: string; country: string; impact: Impact; title: string; actual: string; forecast: string; previous: string; orderKey: string }

const IMPACT_OPTIONS: readonly FilterChipOption<string>[] = [
  { value: "all", label: "Tümü" }, { value: "Yüksek", label: "Yüksek" },
  { value: "Orta", label: "Orta" }, { value: "Düşük", label: "Düşük" },
  { value: "Belirsiz", label: "Belirsiz" },
]

const WINDOW_OPTIONS: readonly FilterChipOption<WindowPreset>[] = [
  { value: "last7", label: "Son 7 gün" },
  { value: "next7", label: "Gelecek 7 gün" },
  { value: "next14", label: "Gelecek 14 gün" },
  { value: "next30", label: "Gelecek 30 gün" },
]

const SUPPORTED_COUNTRIES = [
  { code: "TR", label: "TR" },
  { code: "US", label: "US" },
  { code: "EU", label: "EU" },
  { code: "DE", label: "DE" },
  { code: "GB", label: "GB" },
  { code: "JP", label: "JP" },
  { code: "CN", label: "CN" },
] as const

export default function CalendarPage() {
  const session = useSession()
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
  const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : ""
  return <PageShell label="Takvim" title="Ekonomik takvim" description="Borsapy / Doviz.com ekonomik olayları. Seçili ülkeler ve tarih aralığı için yayımlanan takvim.">
    {!allowed ? <section className="space-y-3 border border-border bg-surface p-5">
      <p className="text-sm text-muted-foreground">{session ? "Takvim için yönetici yetkisi gerekiyor." : "Takvimi görmek için yönetici hesabınızla giriş yapın."}</p>
      <Link href="/login?next=%2Fcalendar" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-sm">Giriş yap</Link>
    </section> : <CalendarWorkspace key={sessionKey} sessionKey={sessionKey} />}
  </PageShell>
}

function CalendarWorkspace({ sessionKey }: { sessionKey: string }) {
  const [today, setToday] = useState(() => istanbulDay(new Date()))
  const [windowPreset, setWindowPreset] = useState<WindowPreset>("next14")
  const [countries, setCountries] = useState<string[]>(["TR", "US"])
  const [selectedDate, setSelectedDate] = useState("all")
  const [selectedImpact, setSelectedImpact] = useState("all")
  const [selectedCountry, setSelectedCountry] = useState("all")
  useEffect(() => {
    const timer = setInterval(() => setToday(istanbulDay(new Date())), 60_000)
    return () => clearInterval(timer)
  }, [])
  const { fromDate, toDate } = resolveCalendarRange(today, windowPreset)
  const countryParam = countries.join(",")
  const query = useQuery({
    queryKey: ["calendar-page", sessionKey, fromDate, toDate, countryParam],
    queryFn: ({ signal }) => fetchEconomicCalendar({ from_date: fromDate, to_date: toDate, country: countryParam }, { signal }),
    refetchInterval: 300_000, staleTime: 300_000, refetchIntervalInBackground: false, retry: false,
  })
  const toggleCountry = (code: string) => {
    setCountries(current => {
      if (current.includes(code)) {
        return current.length > 1 ? current.filter(item => item !== code) : current
      }
      if (current.length >= 3) return current
      return [...current, code]
    })
    setSelectedCountry("all")
  }
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
      <p className="text-xs text-muted-foreground">Sağlayıcı veriyi 1 saat önbellekte tutabilir. 5 dakikalık otomatik yenileme veya Yenile düğmesi yeni veri geldiği anlamına gelmez.</p>
      <p className="text-xs text-muted-foreground">Olay saatleri kaynaktaki haliyle gösterilir; saat dilimi doğrulanmadığı için İstanbul veya UTC saatine çevrilmez.</p>
      {metadata?.state === "stale" && <p role="status" className="text-xs text-warning">Kaynak yenilenemedi; önceki yanıt gösteriliyor. Alınma zamanını kontrol edin.</p>}
      {metadata?.warnings.filter(message => !message.includes("saat dilimi") && !message.includes("önbelleği")).map(message => <p key={message} className="text-xs text-muted-foreground">{message}</p>)}
    </section>
    <section className="flex flex-wrap items-center gap-4 border border-border bg-surface p-3" aria-label="Takvim sorgu kapsamı">
      <FilterChips
        label="Aralık"
        options={WINDOW_OPTIONS}
        value={windowPreset}
        onChange={(next) => { setWindowPreset(next); setSelectedDate("all") }}
      />
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Ülke seçimi (en fazla 3)">
        <span className="label-uppercase">Ülkeler (maks 3)</span>
        {SUPPORTED_COUNTRIES.map(item => {
          const active = countries.includes(item.code)
          const disabled = (!active && countries.length >= 3) || (active && countries.length <= 1)
          return <button
            key={item.code}
            type="button"
            aria-pressed={active}
            disabled={disabled}
            onClick={() => toggleCountry(item.code)}
            className={cn(
              "min-h-9 rounded-sm border px-2.5 text-xs transition-colors disabled:opacity-45",
              active ? "border-foreground/50 bg-raised font-medium text-foreground" : "border-border text-muted-foreground hover:bg-raised"
            )}
          >{item.label}</button>
        })}
      </div>
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

function resolveCalendarRange(today: string, preset: WindowPreset): { fromDate: string; toDate: string } {
  if (preset === "last7") return { fromDate: addDays(today, -7), toDate: today }
  if (preset === "next7") return { fromDate: today, toDate: addDays(today, 7) }
  if (preset === "next30") return { fromDate: today, toDate: addDays(today, 30) }
  return { fromDate: today, toDate: addDays(today, 14) }
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
