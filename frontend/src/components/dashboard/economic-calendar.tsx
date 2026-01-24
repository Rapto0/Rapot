"use client"

import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Filter, RefreshCcw, AlertCircle } from "lucide-react"
import { format, addDays, isSameDay, parseISO } from "date-fns"
import { tr } from "date-fns/locale"

// Types
interface CalendarEvent {
    id: string
    time: string
    country: string
    countryFlag: string
    currency: string
    importance: "High" | "Medium" | "Low"
    event: string
    actual?: string
    forecast?: string
    previous?: string
    rawTime: string // Filtering for sorting
}

interface FinnhubEvent {
    country: string
    event: string
    impact: string
    time: string // "2024-01-24 14:30:00"
    actual: number | null
    estimate: number | null
    previous: number | null
    unit: string
    currency: string
}

const COUNTRY_FLAGS: Record<string, string> = {
    US: "🇺🇸",
    EU: "🇪🇺",
    TR: "🇹🇷",
    CN: "🇨🇳",
    JP: "🇯🇵",
    GB: "🇬🇧",
    DE: "🇩🇪",
    FR: "🇫🇷",
    IT: "🇮🇹",
    CA: "🇨🇦",
    AU: "🇦🇺",
    CH: "🇨🇭",
}

const IMPORTANCE_MAP: Record<string, "High" | "Medium" | "Low"> = {
    low: "Low",
    medium: "Medium",
    high: "High",
}

export function EconomicCalendar() {
    const [selectedDate, setSelectedDate] = useState<Date>(new Date())
    const [activeTab, setActiveTab] = useState<"economic" | "earnings">("economic")

    // Generate next 14 days
    const days = useMemo(() => {
        return Array.from({ length: 14 }).map((_, i) => {
            const date = addDays(new Date(), i)
            return {
                date: date,
                dayName: format(date, "EEE", { locale: tr }),
                dayNumber: format(date, "d"),
                fullDate: format(date, "yyyy-MM-dd"),
            }
        })
    }, [])

    // Fetch Data
    const { data: events, isLoading, isError, refetch } = useQuery({
        queryKey: ['calendar', activeTab, days[0].fullDate, days[days.length - 1].fullDate],
        queryFn: async () => {
            if (activeTab !== 'economic') return [] // Only economic supported for now

            const from = days[0].fullDate
            const to = days[days.length - 1].fullDate
            const res = await fetch(`http://localhost:8000/api/calendar?from_date=${from}&to_date=${to}`)

            if (!res.ok) throw new Error("Veri çekilemedi")

            const data: FinnhubEvent[] = await res.json()

            return data.map((item, index) => {
                const date = parseISO(item.time)
                return {
                    id: `${item.event}-${index}`,
                    time: format(date, "HH:mm"),
                    rawTime: item.time,
                    country: item.country,
                    countryFlag: COUNTRY_FLAGS[item.country] || "🌍",
                    currency: item.currency || item.country, // Fallback
                    importance: IMPORTANCE_MAP[item.impact] || "Low",
                    event: item.event,
                    actual: item.actual !== null ? `${item.actual}${item.unit}` : "",
                    forecast: item.estimate !== null ? `${item.estimate}${item.unit}` : "",
                    previous: item.previous !== null ? `${item.previous}${item.unit}` : "",
                } as CalendarEvent
            }).sort((a, b) => a.rawTime.localeCompare(b.rawTime))
        },
        staleTime: 1000 * 60 * 5, // 5 minutes
    })

    // Filter events for selected date
    const dailyEvents = useMemo(() => {
        if (!events) return []
        return events.filter(event => {
            const eventDate = parseISO(event.rawTime)
            return isSameDay(eventDate, selectedDate)
        })
    }, [events, selectedDate])

    // Mock counts for UI visuals (optional, or could calculate real counts)
    const getDayCounts = (date: Date) => {
        if (!events) return { ecoCount: 0 }
        const count = events.filter(e => isSameDay(parseISO(e.rawTime), date)).length
        return { ecoCount: count }
    }

    return (
        <div className="flex flex-col h-full bg-[#131722]">
            {/* Header */}
            <div className="px-4 py-3 border-b border-[#2a2e39] flex justify-between items-center">
                <div>
                    <h3 className="font-bold text-[#d1d4dc] text-lg">Ekonomik Takvim</h3>
                    <p className="text-xs text-[#787b86] mt-0.5">Küresel piyasaları etkileyebilecek önemli olaylar.</p>
                </div>
                <Button variant="ghost" size="icon" onClick={() => refetch()} title="Yenile">
                    <RefreshCcw className={cn("h-4 w-4 text-[#787b86]", isLoading && "animate-spin")} />
                </Button>
            </div>

            {/* Date Selector */}
            <div className="overflow-x-auto no-scrollbar border-b border-[#2a2e39]">
                <div className="flex p-2 gap-1.5 min-w-max">
                    {days.map((day, i) => {
                        const isActive = isSameDay(day.date, selectedDate)
                        const counts = getDayCounts(day.date)
                        return (
                            <button
                                key={i}
                                onClick={() => setSelectedDate(day.date)}
                                className={cn(
                                    "flex flex-col items-center justify-center p-2 rounded-md min-w-[60px] border transition-colors",
                                    isActive
                                        ? "bg-[#2a2e39] border-[#2962ff] text-[#d1d4dc]"
                                        : "bg-transparent border-[#2a2e39] text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]"
                                )}
                            >
                                <span className="text-xs font-medium">{day.dayName} <span className="text-sm font-bold">{day.dayNumber}</span></span>
                                <div className="flex gap-1 mt-1 text-[9px]">
                                    <span className={cn(isActive ? "text-blue-400" : "text-[#787b86]")}>
                                        {counts.ecoCount > 0 ? `${counts.ecoCount} Olay` : '-'}
                                    </span>
                                </div>
                            </button>
                        )
                    })}
                </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 p-2 border-b border-[#2a2e39] overflow-x-auto no-scrollbar">
                <TabButton label="Ekonomik" active={activeTab === "economic"} onClick={() => setActiveTab("economic")} />
                <TabButton label="Kazanç (Yakında)" active={activeTab === "earnings"} onClick={() => { }} />
                <div className="ml-auto">
                    <Button variant="ghost" size="icon" className="h-6 w-6 text-[#787b86]">
                        <Filter className="h-3 w-3" />
                    </Button>
                </div>
            </div>

            {/* Table Header */}
            <div className="flex items-center px-4 py-2 bg-[#1e222d] border-b border-[#2a2e39] text-[10px] font-semibold text-[#787b86]">
                <div className="w-12">SAAT</div>
                <div className="w-8 text-center">ÜLKE</div>
                <div className="flex-1 px-2">OLAY</div>
                <div className="w-12 text-right">GÜNCEL</div>
                <div className="w-12 text-right">TAHMİN</div>
                <div className="w-12 text-right hidden lg:block">ÖNCEKİ</div>
            </div>

            {/* Event List */}
            <ScrollArea className="flex-1">
                {isLoading && (
                    <div className="flex flex-col items-center justify-center py-10 text-[#787b86]">
                        <RefreshCcw className="h-8 w-8 animate-spin mb-2" />
                        <p>Yükleniyor...</p>
                    </div>
                )}

                {isError && (
                    <div className="flex flex-col items-center justify-center py-10 text-[#ef5350]">
                        <AlertCircle className="h-8 w-8 mb-2" />
                        <p>Veri yüklenemedi. API anahtarınızı kontrol edin.</p>
                    </div>
                )}

                {!isLoading && !isError && dailyEvents.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-10 text-[#787b86]">
                        <p>Bugün için planlanmış ekonomik olay bulunamadı.</p>
                    </div>
                )}

                <div className="divide-y divide-[#2a2e39]">
                    {dailyEvents.map((event) => (
                        <div key={event.id} className="flex items-center px-4 py-3 hover:bg-[#2a2e39] transition-colors cursor-pointer group">
                            {/* Time & Importance */}
                            <div className="w-12 flex flex-col justify-center">
                                <span className="text-[#d1d4dc] text-xs font-medium font-mono">{event.time}</span>
                                <div className="flex gap-0.5 mt-1">
                                    <div className={cn("h-1 w-1 rounded-full", event.importance === "High" ? "bg-[#f23645]" : "bg-[#2a2e39]")} />
                                    <div className={cn("h-1 w-1 rounded-full", event.importance === "High" || event.importance === "Medium" ? "bg-[#f23645]" : "bg-[#2a2e39]")} />
                                    <div className={cn("h-1 w-1 rounded-full bg-[#f23645]")} />
                                </div>
                            </div>

                            {/* Country */}
                            <div className="w-8 flex justify-center text-lg">
                                {event.countryFlag}
                            </div>

                            {/* Event Name */}
                            <div className="flex-1 px-2 min-w-0">
                                <p className="text-[#d1d4dc] text-xs font-medium truncate group-hover:text-[#2962ff] transition-colors" title={event.event}>
                                    {event.event}
                                </p>
                                <p className="text-[#787b86] text-[10px]">{event.currency}</p>
                            </div>

                            {/* Values */}
                            <div className="w-12 text-right">
                                <span className={cn(
                                    "text-xs font-mono font-medium",
                                    event.actual ? "text-[#089981]" : "text-[#787b86]"
                                )}>{event.actual || "-"}</span>
                            </div>
                            <div className="w-12 text-right">
                                <span className="text-[#d1d4dc] text-xs font-mono">{event.forecast}</span>
                            </div>
                            <div className="w-12 text-right hidden lg:block">
                                <span className="text-[#787b86] text-xs font-mono">{event.previous}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </ScrollArea>
        </div>
    )
}

function TabButton({ label, active, onClick }: { label: string, active?: boolean, onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className={cn(
                "px-3 py-1 text-xs font-medium rounded-full transition-colors whitespace-nowrap",
                active
                    ? "bg-[#2a2e39] text-[#d1d4dc]"
                    : "text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]"
            )}
        >
            {label}
        </button>
    )
}
