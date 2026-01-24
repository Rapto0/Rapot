"use client"

import { cn } from "@/lib/utils"
import { BarChart3 } from "lucide-react"

interface EventRowProps {
    time: string
    country: string
    volatility: 1 | 2 | 3
    title: string
    actual?: string
    forecast?: string
    previous?: string
}

export function CalendarEventRow({ time, country, volatility, title, actual, forecast, previous }: EventRowProps) {
    // Determine colors based on actual vs forecast
    const getActualColor = () => {
        if (!actual || !forecast) return "text-[#d1d4dc]"

        // Remove non-numeric characters for comparison (except dot and minus)
        const actVal = parseFloat(actual.replace(/[^0-9.-]/g, ""))
        const forVal = parseFloat(forecast.replace(/[^0-9.-]/g, ""))

        if (isNaN(actVal) || isNaN(forVal)) return "text-[#d1d4dc]"

        if (actVal > forVal) return "text-[#089981]"
        if (actVal < forVal) return "text-[#f23645]"
        return "text-[#d1d4dc]"
    }

    return (
        <div className="flex items-center py-3 px-4 hover:bg-[#2a2e39] border-b border-[#2a2e39] transition-colors group">
            {/* Time */}
            <div className="w-16 text-sm text-[#d1d4dc] font-mono">{time}</div>

            {/* Country & Volatility */}
            <div className="w-24 flex items-center gap-3">
                <span className="text-lg">{country === "USA" ? "🇺🇸" : country === "EU" ? "🇪🇺" : country === "JP" ? "🇯🇵" : country === "TR" ? "🇹🇷" : "🇬🇧"}</span>
                <div className="flex items-end gap-[1px] h-3">
                    {[1, 2, 3].map((level) => (
                        <div
                            key={level}
                            className={cn(
                                "w-1 rounded-sm",
                                volatility >= level ? "bg-[#d1d4dc]" : "bg-[#2a2e39]",
                                level === 1 && "h-1.5",
                                level === 2 && "h-2.5",
                                level === 3 && "h-3.5"
                            )}
                        />
                    ))}
                </div>
            </div>

            {/* Title */}
            <div className="flex-1 font-medium text-[#d1d4dc] text-sm group-hover:text-blue-400 cursor-pointer">
                {title}
            </div>

            {/* Data Columns */}
            <div className="w-24 text-right font-mono text-sm font-bold tabular-nums">
                <span className={getActualColor()}>{actual || "—"}</span>
            </div>
            <div className="w-24 text-right font-mono text-sm text-[#d1d4dc] tabular-nums">
                {forecast || "—"}
            </div>
            <div className="w-24 text-right font-mono text-sm text-[#787b86] tabular-nums">
                {previous || "—"}
            </div>
        </div>
    )
}
