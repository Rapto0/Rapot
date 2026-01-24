"use client"

import { NavRail } from "@/components/tradingview/nav-rail"
import { FilterBar } from "@/components/tradingview/filter-bar"
import { ScreenerTable } from "@/components/tradingview/screener-table"
import { RightSidebar } from "@/components/tradingview/right-sidebar"

export default function TradingViewPage() {
    return (
        <div className="flex h-screen w-full bg-[#131722] text-[#d1d4dc] overflow-hidden">
            {/*
                Grid Layout:
                - 1fr: Main Content (Filters + Table)
                - 360px: Right Sidebar (Watchlist + Detail Widget)
                - 50px: Nav Rail (Far right)

                Note: TradingView usually puts the Nav Rail on the far right or far left.
                The prompt asked for "Far Right Rail".
             */}
            <div className="flex flex-1 overflow-hidden">
                {/* Main Content Area */}
                <div className="flex flex-1 flex-col overflow-hidden border-r border-[#2a2e39]">
                    <FilterBar />
                    <ScreenerTable />

                    {/* Status Bar */}
                    <div className="flex h-8 items-center justify-between border-t border-[#2a2e39] bg-[#1e222d] px-3 py-1 text-xs">
                        <div className="flex items-center gap-4">
                            <span className="flex items-center gap-1.5">
                                <span className="h-2 w-2 rounded-full bg-[#089981]"></span>
                                Piyasa Açık
                            </span>
                            <span className="text-[#787b86]">1562 Sembol Tarandı</span>
                        </div>
                        <div className="flex items-center gap-4 text-[#787b86]">
                            <span>Gecikme: 24ms</span>
                            <span>Bağlantı: Stabil</span>
                        </div>
                    </div>
                </div>

                {/* Right Sidebar - Hidden on mobile/tablet */}
                <div className="hidden xl:block h-full">
                    <RightSidebar />
                </div>
            </div>

            {/* Far Right Navigation Rail - Hidden on mobile */}
            <div className="hidden md:block">
                <NavRail />
            </div>
        </div>
    )
}
