import { KPICards, MiniStats } from "@/components/dashboard/kpi-cards"
import { TradingChart } from "@/components/dashboard/trading-chart"
import { RecentSignals } from "@/components/dashboard/recent-signals"
import { MarketOverview, OpenPositions } from "@/components/dashboard/market-overview"

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Piyasa durumu ve işlem özeti
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <KPICards />

      {/* Main Grid - Bento Layout */}
      <div className="grid gap-4 lg:grid-cols-12">
        {/* Trading Chart - Takes 8 cols */}
        <TradingChart />

        {/* Recent Signals - Takes 4 cols */}
        <RecentSignals />
      </div>

      {/* Bottom Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* Market Overview Charts */}
        <div className="lg:col-span-2">
          <MarketOverview />
        </div>

        {/* Open Positions */}
        <OpenPositions />
      </div>

      {/* Mini Stats */}
      <div className="max-w-xs">
        <MiniStats />
      </div>
    </div>
  )
}
