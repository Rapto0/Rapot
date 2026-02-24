"use client"

import { AdvancedChartPage } from "@/components/charts/advanced-chart"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

function ChartPageContent() {
  const searchParams = useSearchParams()
  const symbol = searchParams.get("symbol") || "THYAO"
  const market = (searchParams.get("market") as "BIST" | "Kripto") || "BIST"

  return <AdvancedChartPage initialSymbol={symbol} initialMarket={market} />
}

export default function ChartPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-[420px] items-center justify-center border border-border bg-surface text-xs text-muted-foreground">
          Grafik yükleniyor...
        </div>
      }
    >
      <ChartPageContent />
    </Suspense>
  )
}
