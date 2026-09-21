"use client"

import { useQuery } from "@tanstack/react-query"
import { fetchGlobalIndices } from "@/lib/api/client"
import { MARKET_REFRESH_MS, normalizeMarketQuotes, type MarketQuote } from "@/lib/market-feed"

export async function loadMarketSnapshot(symbols: string[], signal: AbortSignal): Promise<Record<string, MarketQuote>> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (signal.aborted) cancel()
  else signal.addEventListener("abort", cancel, { once: true })
  // A stalled request must not leave the page showing an endless loading state.
  const timeout = setTimeout(cancel, 60_000)
  try {
    const chunks: string[][] = []
    for (let index = 0; index < symbols.length; index += 30) {
      chunks.push(symbols.slice(index, index + 30))
    }
    const responses = await Promise.all(chunks.map(async (chunk) =>
      normalizeMarketQuotes(await fetchGlobalIndices(chunk, { signal: controller.signal }), chunk)
    ))
    return Object.assign({}, ...responses)
  } finally {
    controller.abort()
    clearTimeout(timeout)
    signal.removeEventListener("abort", cancel)
  }
}

export function useMarketSnapshot(symbols: string[]) {
  return useQuery({
    queryKey: ["home-market-snapshot", symbols],
    queryFn: ({ signal }) => loadMarketSnapshot(symbols, signal),
    refetchInterval: MARKET_REFRESH_MS,
    staleTime: MARKET_REFRESH_MS,
    refetchOnWindowFocus: true,
    retry: false,
  })
}
