import { AdvancedChartPage } from "@/components/charts/advanced-chart"

interface ChartPageProps {
  searchParams?: {
    symbol?: string | string[]
    market?: string | string[]
  }
}

const pickFirst = (value: string | string[] | undefined): string | undefined =>
  Array.isArray(value) ? value[0] : value

export default function ChartPage({ searchParams }: ChartPageProps) {
  const symbol = (pickFirst(searchParams?.symbol) || "THYAO").toUpperCase()
  const marketParam = pickFirst(searchParams?.market)
  const market: "BIST" | "Kripto" = marketParam === "Kripto" ? "Kripto" : "BIST"

  return (
    <div className="h-full min-h-0">
      <AdvancedChartPage initialSymbol={symbol} initialMarket={market} />
    </div>
  )
}
