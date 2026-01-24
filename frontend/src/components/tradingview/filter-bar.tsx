"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { Search, SlidersHorizontal, ChevronDown, RefreshCcw, MoreVertical } from "lucide-react"

export function FilterBar() {
    return (
        <div className="flex flex-col border-b border-[#2a2e39] bg-[#131722]">
            {/* Top Toolbar */}
            <div className="flex items-center justify-between px-3 py-2">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-medium text-[#d1d4dc]">Hisse Senedi Takipçisi</h2>
                    <div className="flex items-center gap-1">
                        <FilterBadge label="Türkiye" active />
                        <FilterBadge label="İzleme Listesi" />
                        <FilterBadge label="Endeks" />
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    <div className="relative">
                        <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-[#787b86]" />
                        <Input
                            placeholder="Ara..."
                            className="h-8 w-48 border-[#2a2e39] bg-[#1e222d] pl-8 text-xs text-[#d1d4dc] placeholder:text-[#50535e] focus-visible:ring-1 focus-visible:ring-[#2962ff] focus-visible:ring-offset-0"
                        />
                    </div>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-[#d1d4dc] hover:bg-[#2a2e39]">
                        <SlidersHorizontal className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-[#d1d4dc] hover:bg-[#2a2e39]">
                        <RefreshCcw className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            <Separator className="bg-[#2a2e39]" />

            {/* Quick Filters */}
            <div className="flex items-center gap-2 px-3 py-2 overflow-x-auto no-scrollbar">
                <Button variant="outline" size="sm" className="h-7 gap-1 rounded-md border-[#2a2e39] bg-transparent px-3 text-xs font-normal text-[#d1d4dc] hover:bg-[#2a2e39] hover:text-[#d1d4dc]">
                    Fiyat
                    <ChevronDown className="h-3 w-3 text-[#787b86]" />
                </Button>
                <Button variant="outline" size="sm" className="h-7 gap-1 rounded-md border-[#2a2e39] bg-transparent px-3 text-xs font-normal text-[#d1d4dc] hover:bg-[#2a2e39] hover:text-[#d1d4dc]">
                    Değişim %
                    <ChevronDown className="h-3 w-3 text-[#787b86]" />
                </Button>
                <Button variant="outline" size="sm" className="h-7 gap-1 rounded-md border-[#2a2e39] bg-transparent px-3 text-xs font-normal text-[#d1d4dc] hover:bg-[#2a2e39] hover:text-[#d1d4dc]">
                    Hacim
                    <ChevronDown className="h-3 w-3 text-[#787b86]" />
                </Button>
                <Button variant="outline" size="sm" className="h-7 gap-1 rounded-md border-[#2a2e39] bg-transparent px-3 text-xs font-normal text-[#d1d4dc] hover:bg-[#2a2e39] hover:text-[#d1d4dc]">
                    Piyasa Değeri
                    <ChevronDown className="h-3 w-3 text-[#787b86]" />
                </Button>
                <Button variant="outline" size="sm" className="h-7 gap-1 rounded-md border-[#2a2e39] bg-transparent px-3 text-xs font-normal text-[#d1d4dc] hover:bg-[#2a2e39] hover:text-[#d1d4dc]">
                    RSI (14)
                    <ChevronDown className="h-3 w-3 text-[#787b86]" />
                </Button>
                <div className="ml-auto">
                    <Button variant="ghost" size="sm" className="h-7 text-[#2962ff] hover:text-[#2962ff] hover:bg-[#2962ff]/10">
                        Filtreler
                    </Button>
                </div>
            </div>
        </div>
    )
}

function FilterBadge({ label, active }: { label: string; active?: boolean }) {
    return (
        <Badge
            variant="outline"
            className={`
                cursor-pointer border-transparent px-2 py-0.5 text-xs font-medium hover:bg-[#2a2e39]
                ${active ? 'text-[#2962ff] bg-[#2962ff]/10' : 'text-[#787b86]'}
            `}
        >
            {label}
        </Badge>
    )
}
