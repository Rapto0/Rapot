"use client"

import { useMemo, useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type EventImpact = "Düşük" | "Orta" | "Yüksek"
type EventRegion = "TR" | "EU" | "UK" | "USA" | "JP"

type CalendarEvent = {
  id: number
  date: string
  time: string
  region: EventRegion
  impact: EventImpact
  title: string
  actual: string
  forecast: string
  previous: string
}

const CALENDAR_EVENTS: CalendarEvent[] = [
  { id: 1, date: "2026-02-24", time: "10:00", region: "TR", impact: "Orta", title: "Yabancı turist sayısı", actual: "4.5%", forecast: "3.2%", previous: "2.1%" },
  { id: 2, date: "2026-02-24", time: "10:30", region: "EU", impact: "Yüksek", title: "Almanya imalat PMI", actual: "45.4", forecast: "43.7", previous: "43.3" },
  { id: 3, date: "2026-02-24", time: "12:00", region: "UK", impact: "Orta", title: "İngiltere hizmet PMI", actual: "53.8", forecast: "53.2", previous: "53.4" },
  { id: 4, date: "2026-02-24", time: "16:45", region: "USA", impact: "Yüksek", title: "S&P Global hizmet PMI", actual: "52.9", forecast: "51.0", previous: "51.4" },
  { id: 5, date: "2026-02-24", time: "18:00", region: "USA", impact: "Düşük", title: "Richmond imalat endeksi", actual: "-15", forecast: "-7", previous: "-11" },
  { id: 6, date: "2026-02-25", time: "08:00", region: "JP", impact: "Orta", title: "BoJ faiz kararı", actual: "", forecast: "-0.10%", previous: "-0.10%" },
  { id: 7, date: "2026-02-25", time: "10:00", region: "TR", impact: "Yüksek", title: "TCMB faiz kararı", actual: "", forecast: "45.00%", previous: "42.50%" },
  { id: 8, date: "2026-02-25", time: "16:30", region: "USA", impact: "Yüksek", title: "GSYİH (çeyreklik)", actual: "", forecast: "2.0%", previous: "4.9%" },
]

const impactOrder: EventImpact[] = ["Düşük", "Orta", "Yüksek"]

export default function CalendarPage() {
  const [selectedDate, setSelectedDate] = useState<string>("all")
  const [selectedImpact, setSelectedImpact] = useState<EventImpact | "all">("all")

  const dates = useMemo(() => Array.from(new Set(CALENDAR_EVENTS.map((event) => event.date))), [])

  const filteredEvents = useMemo(() => {
    return CALENDAR_EVENTS.filter((event) => {
      if (selectedDate !== "all" && event.date !== selectedDate) return false
      if (selectedImpact !== "all" && event.impact !== selectedImpact) return false
      return true
    })
  }, [selectedDate, selectedImpact])

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="label-uppercase">Takvim</div>
        <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Ekonomik takvim</h1>
        <p className="mt-1 text-xs text-muted-foreground">Piyasa etkisi yüksek veri ve karar akışı.</p>
      </section>

      <section className="border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center gap-3">
          <FilterBlock
            title="Tarih"
            options={[["all", "Tümü"], ...dates.map((date) => [date, formatDateLabel(date)] as [string, string])]}
            value={selectedDate}
            onChange={setSelectedDate}
          />
          <FilterBlock
            title="Etki"
            options={[["all", "Tümü"], ...impactOrder.map((value) => [value, value] as [string, string])]}
            value={selectedImpact}
            onChange={(value) => setSelectedImpact(value as EventImpact | "all")}
          />
        </div>
      </section>

      <section className="border border-border bg-surface">
        <div className="grid grid-cols-[80px_80px_110px_1fr_100px_100px_100px] border-b border-border px-3 py-2 text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
          <span>Saat</span>
          <span>Bölge</span>
          <span>Etki</span>
          <span>Olay</span>
          <span className="text-right">Güncel</span>
          <span className="text-right">Tahmin</span>
          <span className="text-right">Önceki</span>
        </div>

        {filteredEvents.length === 0 ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">Kayıt bulunamadı.</div>
        ) : (
          <div className="divide-y divide-border">
            {filteredEvents.map((event) => (
              <div key={event.id} className="grid grid-cols-[80px_80px_110px_1fr_100px_100px_100px] items-center gap-2 px-3 py-2">
                <span className="mono-numbers text-xs text-foreground">{event.time}</span>
                <span className="text-xs text-muted-foreground">{event.region}</span>
                <span
                  className={cn(
                    "signal-badge w-fit",
                    event.impact === "Yüksek" ? "signal-sell" : event.impact === "Orta" ? "signal-neutral" : "border border-border bg-base text-muted-foreground"
                  )}
                >
                  {event.impact}
                </span>
                <span className="truncate text-xs text-foreground">{event.title}</span>
                <span className="mono-numbers text-right text-xs text-foreground">{event.actual || "--"}</span>
                <span className="mono-numbers text-right text-xs text-muted-foreground">{event.forecast || "--"}</span>
                <span className="mono-numbers text-right text-xs text-muted-foreground">{event.previous || "--"}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function FilterBlock({
  title,
  options,
  value,
  onChange,
}: {
  title: string
  options: [string, string][]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">{title}</span>
      <div className="flex items-center gap-1">
        {options.map(([optionValue, label]) => (
          <Button
            key={optionValue}
            type="button"
            size="sm"
            variant={value === optionValue ? "default" : "outline"}
            onClick={() => onChange(optionValue)}
          >
            {label}
          </Button>
        ))}
      </div>
    </div>
  )
}

function formatDateLabel(dateValue: string) {
  const date = new Date(`${dateValue}T00:00:00`)
  return date.toLocaleDateString("tr-TR", {
    day: "2-digit",
    month: "short",
  })
}
