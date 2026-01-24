"use client"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const FILTERS = ["Ekonomik", "Kazanç", "Osilatörler", "Temettüler", "Halka arz"]

export function FilterTabs() {
    return (
        <div className="flex items-center gap-2 p-4 border-b border-[#2a2e39] bg-[#131722]">
            {FILTERS.map((filter, index) => (
                <Button
                    key={filter}
                    variant="ghost"
                    size="sm"
                    className={cn(
                        "rounded-full px-4 h-8 text-xs font-medium transition-colors",
                        index === 0
                            ? "bg-[#2a2e39] text-[#d1d4dc] hover:bg-[#2a2e39]"
                            : "text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]"
                    )}
                >
                    {filter}
                </Button>
            ))}

            <div className="ml-auto flex items-center gap-2">
                <Button variant="outline" size="sm" className="h-7 text-xs border-[#2a2e39] text-[#d1d4dc] bg-transparent hover:bg-[#2a2e39]">
                    Filtreleri Temizle
                </Button>
            </div>
        </div>
    )
}
