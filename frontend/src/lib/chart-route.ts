export interface ChartSearchParams {
  symbol?: string | string[]
  market?: string | string[]
}

const firstValue = (value: string | string[] | undefined): string | undefined => {
  const first = Array.isArray(value) ? value[0] : value
  return typeof first === "string" ? first.trim() : undefined
}

export function resolveChartSelection(params: ChartSearchParams = {}): {
  symbol: string
  market: "BIST" | "Kripto"
} {
  const market = firstValue(params.market)?.toLowerCase() === "kripto" ? "Kripto" : "BIST"
  const symbol = firstValue(params.symbol)?.toUpperCase() ?? ""

  return {
    // This validates URL syntax, not whether a symbol is listed by the provider.
    symbol: /^[A-Z0-9]{1,32}$/.test(symbol) ? symbol : market === "Kripto" ? "BTCUSDT" : "THYAO",
    market,
  }
}
