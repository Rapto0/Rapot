"use client"

import { DateNavigator } from "@/components/calendar/date-navigator"
import { FilterTabs } from "@/components/calendar/filter-tabs"
import { CalendarEventRow } from "@/components/calendar/event-row"
import { ScrollArea } from "@/components/ui/scroll-area"

const EVENTS = [
    { time: "10:00", country: "TR", volatility: 2, title: "Yabancı Turist Sayısı (Yıllık)", actual: "4.5%", forecast: "3.2%", previous: "2.1%" },
    { time: "10:30", country: "EU", volatility: 3, title: "Almanya İmalat PMI", actual: "45.4", forecast: "43.7", previous: "43.3" },
    { time: "11:00", country: "EU", volatility: 2, title: "Euro Bölgesi Bileşik PMI", actual: "47.9", forecast: "48.0", previous: "47.6" },
    { time: "12:00", country: "UK", volatility: 3, title: "İngiltere Hizmet PMI", actual: "53.8", forecast: "53.2", previous: "53.4" },
    { time: "15:30", country: "USA", volatility: 1, title: "Chicago Fed Ulusal Aktivite Endeksi", actual: "0.02", forecast: "-0.10", previous: "0.03" },
    { time: "16:45", country: "USA", volatility: 3, title: "S&P Global İmalat PMI", actual: "50.3", forecast: "47.9", previous: "47.9" },
    { time: "16:45", country: "USA", volatility: 3, title: "S&P Global Hizmet PMI", actual: "52.9", forecast: "51.0", previous: "51.4" },
    { time: "18:00", country: "USA", volatility: 2, title: "Richmond İmalat Endeksi", actual: "-15", forecast: "-7", previous: "-11" },
    { time: "21:00", country: "USA", volatility: 1, title: "2 Yıllık Tahvil İhalesi", actual: "4.365%", forecast: "", previous: "4.314%" }
]

export default function CalendarPage() {
    return (
        <div className="flex h-screen w-full flex-col bg-[#131722] text-[#d1d4dc] overflow-hidden">
            {/* Header */}
            <div className="bg-[#131722] pt-4 px-6 pb-2">
                <h1 className="text-2xl font-bold">Ekonomik Takvim</h1>
                <p className="text-sm text-[#787b86] mt-1">Küresel piyasaları etkileyebilecek önemli ekonomik olaylar.</p>
            </div>

            {/* Controls */}
            <DateNavigator />
            <FilterTabs />

            {/* Header for List */}
            <div className="flex items-center py-2 px-4 bg-[#1e222d] border-b border-[#2a2e39] text-xs font-bold text-[#787b86] uppercase tracking-wider">
                <div className="w-16">Saat</div>
                <div className="w-24">Ülke</div>
                <div className="flex-1">Olay</div>
                <div className="w-24 text-right">Güncel</div>
                <div className="w-24 text-right">Tahmin</div>
                <div className="w-24 text-right">Önceki</div>
            </div>

            {/* Event List */}
            <ScrollArea className="flex-1 bg-[#131722]">
                <div className="flex flex-col">
                    <div className="sticky top-0 z-10 bg-[#131722] py-2 px-4 border-b border-[#2a2e39]">
                        <span className="text-sm font-bold text-[#d1d4dc]">Çarşamba, 23 Ocak</span>
                    </div>
                    {EVENTS.map((event, index) => (
                        <CalendarEventRow key={index} {...event} volatility={event.volatility as 1 | 2 | 3} />
                    ))}

                    <div className="sticky top-0 z-10 bg-[#131722] py-2 px-4 border-b border-[#2a2e39] mt-4">
                        <span className="text-sm font-bold text-[#d1d4dc]">Perşembe, 24 Ocak</span>
                    </div>
                    {/* Mock events for next day */}
                    <CalendarEventRow time="08:00" country="JP" volatility={2} title="BoJ Faiz Oranı Kararı" actual="" forecast="-0.10%" previous="-0.10%" />
                    <CalendarEventRow time="10:00" country="TR" volatility={3} title="TCMB Faiz Kararı" actual="" forecast="45.00%" previous="42.50%" />
                    <CalendarEventRow time="16:30" country="USA" volatility={3} title="GSYİH (Çeyreklik)" actual="" forecast="2.0%" previous="4.9%" />
                </div>
            </ScrollArea>
        </div>
    )
}
