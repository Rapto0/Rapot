"use client"

import { cn } from "@/lib/utils"
import { SidebarWatchlist } from "./sidebar-watchlist"
import { SidebarDetail } from "./sidebar-detail"
import { useDashboardStore } from "@/lib/stores"
import { RecentSignals } from "@/components/dashboard/recent-signals"
import { ScrollArea } from "@/components/ui/scroll-area"
import { EconomicCalendar } from "@/components/dashboard/economic-calendar"

export function RightSidebar() {
    const { activeSidebarTab } = useDashboardStore()

    return (
        <div className="flex h-full w-[360px] flex-col border-l border-[#2a2e39] bg-[#131722]">
            {activeSidebarTab === 'watchlist' && (
                <>
                    <SidebarWatchlist />
                    <SidebarDetail />
                </>
            )}

            {activeSidebarTab === 'signals' && (
                <div className="flex flex-col h-full">
                    <div className="p-3 border-b border-[#2a2e39]">
                        <h3 className="font-semibold text-[#d1d4dc]">Son Sinyaller</h3>
                    </div>
                    <ScrollArea className="flex-1">
                        <RecentSignals compact />
                    </ScrollArea>
                </div>
            )}

            {activeSidebarTab === 'news' && (
                <EmptySidebarState
                    title="Haberler"
                    description="Piyasa haberleri ve ekonomik takvim çok yakında burada olacak."
                    icon="📰"
                />
            )}

            {activeSidebarTab === 'data' && (
                <EmptySidebarState
                    title="Veri Penceresi"
                    description="Seçili hisse için detaylı teknik veriler (RSI, MACD, Hacim vb.) burada gösterilecek."
                    icon="📊"
                />
            )}

            {activeSidebarTab === 'calendar' && (
                <EconomicCalendar />
            )}
        </div>
    )
}

function EmptySidebarState({ title, description, icon }: { title: string, description: string, icon: string }) {
    return (
        <div className="flex flex-col items-center justify-center h-full p-6 text-center text-[#787b86]">
            <div className="text-4xl mb-4">{icon}</div>
            <h3 className="text-lg font-medium text-[#d1d4dc] mb-2">{title}</h3>
            <p className="text-sm">{description}</p>
        </div>
    )
}

function WatchlistItem({ symbol, price, change }: { symbol: string; price: string; change: number }) {
    const isPositive = change >= 0
    return (
        <div className="flex cursor-pointer items-center justify-between px-3 py-2 hover:bg-[#2a2e39] group">
            <div className="flex flex-col">
                <span className="text-sm font-medium text-[#d1d4dc] group-hover:text-blue-400">{symbol}</span>
                <span className="text-xs text-[#787b86]">Döviz</span>
            </div>
            <div className="text-right">
                <div className="text-sm font-mono text-[#d1d4dc]">{price}</div>
                <div className={cn("text-xs font-mono", isPositive ? "text-[#089981]" : "text-[#f23645]")}>
                    {isPositive ? "+" : ""}{change}%
                </div>
            </div>
        </div>
    )
}

function StatCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded border border-[#2a2e39] bg-[#131722] p-2">
            <span className="block text-[10px] text-[#787b86]">{label}</span>
            <span className="block text-sm font-medium text-[#d1d4dc]">{value}</span>
        </div>
    )
}
