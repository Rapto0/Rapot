"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { FilterChips, type FilterChipOption } from "@/components/ui/filter-chips"
import { cn } from "@/lib/utils"
import { fetchEconomicCalendar, type EconomicCalendarEvent } from "@/lib/api/client"
import { RefreshCw } from "lucide-react"

type UiImpact = "Dusuk" | "Orta" | "Yuksek"
type ImpactFilter = UiImpact | "all"

type UiEvent = {
  id: string
  date: string
  time: string
  country: string
  impact: UiImpact
  title: string
  actual: string
  forecast: string
  previous: string
  orderKey: string
}

const IMPACT_ORDER: UiImpact[] = ["Dusuk", "Orta", "Yuksek"]
const AUTO_REFRESH_MS = 60_000
const IMPACT_OPTIONS: readonly FilterChipOption<ImpactFilter>[] = [
  { value: "all", label: "Tumu" },
  ...IMPACT_ORDER.map((value) => ({ value, label: value })),
]

export default function CalendarPage() {
  const [selectedDate, setSelectedDate] = useState<string>("all")
  const [selectedImpact, setSelectedImpact] = useState<ImpactFilter>("all")
  const [selectedCountry, setSelectedCountry] = useState<string>("all")

  const fromDate = useMemo(() => formatYmd(new Date()), [])
  const toDate = useMemo(() => {
    const end = new Date()
    end.setDate(end.getDate() + 14)
    return formatYmd(end)
  }, [])

  const {
    data: rawEvents,
    isLoading,
    isFetching,
    isError,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ["calendar-page", fromDate, toDate],
    queryFn: () => fetchEconomicCalendar({ from_date: fromDate, to_date: toDate }),
    refetchInterval: AUTO_REFRESH_MS,
    staleTime: 30_000,
  })

  const events = useMemo(() => mapCalendarEvents(rawEvents || []), [rawEvents])

  const dates = useMemo(
    () => Array.from(new Set(events.map((event) => event.date))).sort(),
    [events]
  )

  const countries = useMemo(
    () => Array.from(new Set(events.map((event) => event.country))).sort(),
    [events]
  )

  const dateOptions = useMemo<readonly FilterChipOption<string>[]>(
    () => [
      { value: "all", label: "Tumu" },
      ...dates.map((date) => ({ value: date, label: formatDateLabel(date) })),
    ],
    [dates]
  )

  const countryOptions = useMemo<readonly FilterChipOption<string>[]>(
    () => [
      { value: "all", label: "Tumu" },
      ...countries.map((country) => ({ value: country, label: country })),
    ],
    [countries]
  )

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      if (selectedDate !== "all" && event.date !== selectedDate) return false
      if (selectedImpact !== "all" && event.impact !== selectedImpact) return false
      if (selectedCountry !== "all" && event.country !== selectedCountry) return false
      return true
    })
  }, [events, selectedDate, selectedImpact, selectedCountry])

  const lastUpdateLabel =
    dataUpdatedAt > 0
      ? new Date(dataUpdatedAt).toLocaleString("tr-TR")
      : "--"

  return (
    <PageShell
      label="Takvim"
      title="Ekonomik takvim"
      description="Finnhub tabanli canli veri. Her 60 saniyede otomatik yenilenir."
      actions={
        <>
          <span className="text-[11px] text-muted-foreground">Son guncelleme: {lastUpdateLabel}</span>
          {isFetching && <span className="text-[11px] text-primary">Yenileniyor...</span>}
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
            aria-busy={isFetching}
            className="gap-1.5"
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
            Yenile
          </Button>
        </>
      }
    >

      <section className="border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center gap-3">
          <FilterChips
            label="Tarih"
            options={dateOptions}
            value={selectedDate}
            onChange={setSelectedDate}
          />
          <FilterChips
            label="Etki"
            options={IMPACT_OPTIONS}
            value={selectedImpact}
            onChange={setSelectedImpact}
          />
          <FilterChips
            label="Bolge"
            options={countryOptions}
            value={selectedCountry}
            onChange={setSelectedCountry}
          />
        </div>
      </section>

      <section className="border border-border bg-surface">
        <div className="grid grid-cols-[80px_90px_90px_1fr_110px_110px_110px] border-b border-border px-3 py-2 text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
          <span>Saat</span>
          <span>Bolge</span>
          <span>Etki</span>
          <span>Olay</span>
          <span className="text-right">Guncel</span>
          <span className="text-right">Tahmin</span>
          <span className="text-right">Onceki</span>
        </div>

        {isLoading ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">Veriler yukleniyor...</div>
        ) : isError ? (
          <div className="px-3 py-8 text-center text-xs text-loss">
            Takvim verisi alinamadi. `FINNHUB_API_KEY` ayarini kontrol edin.
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">Kayit bulunamadi.</div>
        ) : (
          <div className="divide-y divide-border">
            {filteredEvents.map((event) => (
              <div key={event.id} className="grid grid-cols-[80px_90px_90px_1fr_110px_110px_110px] items-center gap-2 px-3 py-2">
                <span className="mono-numbers text-xs text-foreground">{event.time}</span>
                <span className="text-xs text-muted-foreground">{event.country}</span>
                <span
                  className={cn(
                    "signal-badge w-fit",
                    event.impact === "Yuksek"
                      ? "signal-sell"
                      : event.impact === "Orta"
                        ? "signal-neutral"
                        : "border border-border bg-base text-muted-foreground"
                  )}
                >
                  {event.impact}
                </span>
                <span className="truncate text-xs text-foreground" title={event.title}>
                  {event.title}
                </span>
                <span className="mono-numbers text-right text-xs text-foreground">{event.actual || "--"}</span>
                <span className="mono-numbers text-right text-xs text-muted-foreground">{event.forecast || "--"}</span>
                <span className="mono-numbers text-right text-xs text-muted-foreground">{event.previous || "--"}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </PageShell>
  )
}

function mapCalendarEvents(rawEvents: EconomicCalendarEvent[]): UiEvent[] {
  return rawEvents
    .map((item, index) => {
      const parsed = parseApiDateTime(item.time)
      if (!parsed) return null

      return {
        id: `${parsed.orderKey}-${item.country || "ROW"}-${index}`,
        date: parsed.date,
        time: parsed.time,
        country: (item.country || item.currency || "ROW").toUpperCase(),
        impact: mapImpact(item.impact),
        title: item.event || "Ekonomik veri",
        actual: formatMetric(item.actual, item.unit),
        forecast: formatMetric(item.estimate, item.unit),
        previous: formatMetric(item.previous, item.unit),
        orderKey: parsed.orderKey,
      }
    })
    .filter((event): event is UiEvent => event !== null)
    .sort((a, b) => a.orderKey.localeCompare(b.orderKey))
}

function parseApiDateTime(value: string | null): { date: string; time: string; orderKey: string } | null {
  if (!value) return null

  const directMatch = value.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/)
  if (directMatch) {
    const date = directMatch[1]
    const time = directMatch[2]
    return { date, time, orderKey: `${date}T${time}` }
  }

  const normalized = value.includes("T") ? value : value.replace(" ", "T")
  const dateObj = new Date(normalized)
  if (Number.isNaN(dateObj.getTime())) return null

  return {
    date: formatYmd(dateObj),
    time: dateObj.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
    orderKey: dateObj.toISOString(),
  }
}

function mapImpact(rawImpact: string | null): UiImpact {
  const value = (rawImpact || "").toLowerCase()
  if (value.includes("high") || value === "3" || value.includes("critical")) return "Yuksek"
  if (value.includes("medium") || value === "2" || value.includes("med")) return "Orta"
  return "Dusuk"
}

function formatMetric(value: number | null, unit: string | null): string {
  if (value === null || value === undefined) return ""
  const numberText = Number.isInteger(value) ? value.toString() : value.toFixed(2)
  return `${numberText}${unit || ""}`
}

function formatDateLabel(dateValue: string) {
  const date = new Date(`${dateValue}T00:00:00`)
  return date.toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
  })
}

function formatYmd(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}
