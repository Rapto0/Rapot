"use client"

import { cn } from "@/lib/utils"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"

const DATES = [
    { day: "Çar", date: "16", economic: 42, earnings: 15, dividend: 88, active: false },
    { day: "Per", date: "17", economic: 38, earnings: 12, dividend: 92, active: false },
    { day: "Cum", date: "18", economic: 25, earnings: 8, dividend: 45, active: false },
    { day: "Pzt", date: "21", economic: 56, earnings: 22, dividend: 110, active: false },
    { day: "Sal", date: "22", economic: 48, earnings: 18, dividend: 95, active: false },
    { day: "Çar", date: "23", economic: 45, earnings: 31, dividend: 105, active: true }, // Active day
    { day: "Per", date: "24", economic: 39, earnings: 14, dividend: 85, active: false },
    { day: "Cum", date: "25", economic: 30, earnings: 10, dividend: 60, active: false },
    { day: "Pzt", date: "28", economic: 52, earnings: 20, dividend: 100, active: false },
]

export function DateNavigator() {
    return (
        <div className="w-full border-b border-[#2a2e39] bg-[#131722]">
            <ScrollArea className="w-full whitespace-nowrap">
                <div className="flex w-max p-4 gap-2">
                    {DATES.map((item, index) => (
                        <div
                            key={index}
                            className={cn(
                                "flex flex-col items-center justify-center min-w-[100px] p-2 rounded cursor-pointer border transition-colors",
                                item.active
                                    ? "bg-[#2a2e39] border-[#2962ff]"
                                    : "bg-transparent border-[#2a2e39] hover:bg-[#2a2e39]/50"
                            )}
                        >
                            <div className="flex items-baseline gap-1 mb-1">
                                <span className="text-xs text-[#787b86]">{item.day}</span>
                                <span className={cn("text-lg font-bold", item.active ? "text-[#d1d4dc]" : "text-[#787b86]")}>
                                    {item.date}
                                </span>
                            </div>
                            <div className="flex flex-col gap-0.5 w-full">
                                <div className="flex justify-between items-center text-[10px]">
                                    <span className="text-[#787b86]">Eko</span>
                                    <span className="font-medium text-[#d1d4dc]">{item.economic}</span>
                                </div>
                                <div className="flex justify-between items-center text-[10px]">
                                    <span className="text-[#787b86]">Kaz</span>
                                    <span className="font-medium text-[#d1d4dc]">{item.earnings}</span>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
                <ScrollBar orientation="horizontal" />
            </ScrollArea>
        </div>
    )
}
