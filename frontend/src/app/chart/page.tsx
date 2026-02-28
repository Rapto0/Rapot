"use client"

import { AdvancedChartPage } from "@/components/charts/advanced-chart"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

function ChartPageContent() {
  const searchParams = useSearchParams()
  const symbol = searchParams.get("symbol") || "THYAO"
  const market = (searchParams.get("market") as "BIST" | "Kripto") || "BIST"

  return (
    <div className="h-full min-h-0">
      <AdvancedChartPage initialSymbol={symbol} initialMarket={market} />
    </div>
  )
}

export default function ChartPage() {
  return (
    <div className="h-full min-h-0">
      <Suspense
        fallback={
          <div className="flex h-full min-h-[420px] items-center justify-center border border-border bg-surface text-xs text-muted-foreground">
            Grafik yükleniyor...
          </div>
        }
      >
        <ChartPageContent />
      </Suspense>
    </div>
  )
}
