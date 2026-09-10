import { AdvancedChartPage } from "@/components/charts/advanced-chart"
import { resolveChartSelection, type ChartSearchParams } from "@/lib/chart-route"

interface ChartPageProps {
  searchParams?: Promise<ChartSearchParams>
}

export default async function ChartPage({ searchParams }: ChartPageProps) {
  const { symbol, market } = resolveChartSelection(await searchParams)

  return (
    <div className="h-full min-h-0">
      <AdvancedChartPage initialSymbol={symbol} initialMarket={market} />
    </div>
  )
}
