"use client"

import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"
import { fetchGlobalIndices } from "@/lib/api/client"
import { finiteNumber, MARKET_REFRESH_MS, normalizeMarketQuotes, type MarketQuote } from "@/lib/market-feed"
import { useSession } from "./use-session"

const SNAPSHOT_KEY = "private-market-snapshot"
const QUOTE_REUSE_MS = 120_000

function useSnapshotSession() {
  const session = useSession()
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
  const sessionKey = session ? `${session.user.username}:${session.expiresAt}` : "guest"
  return { allowed, sessionKey }
}

function recentMarketQuotes(client: QueryClient, sessionKey: string, symbols: string[]) {
  const now = Date.now()
  const remaining = new Set(symbols)
  const prices: Record<string, MarketQuote> = {}
  const queries = client.getQueryCache().findAll({ queryKey: [SNAPSHOT_KEY, sessionKey] })
    .sort((a, b) => b.state.dataUpdatedAt - a.state.dataUpdatedAt)
  for (const { queryKey, state: { data, dataUpdatedAt } } of queries) {
    if (!dataUpdatedAt || now - dataUpdatedAt > QUOTE_REUSE_MS) break
    const requested = queryKey[2]
    if (!Array.isArray(requested) || !data) continue
    const quotes = data as Record<string, MarketQuote>
    for (const symbol of requested) {
      // A newer successful response owns this symbol even if it supplied no price.
      if (!remaining.delete(symbol)) continue
      const quote = quotes[symbol]
      if (finiteNumber(quote?.value)) prices[symbol] = {
        ...quote,
        state: "stale",
        message: quote.state !== "ok" && quote.message ? quote.message : "Bu oturumda alınan son fiyat",
      }
    }
    if (!remaining.size) break
  }
  return Object.keys(prices).length ? prices : undefined
}

export async function loadMarketSnapshot(symbols: string[], signal: AbortSignal): Promise<Record<string, MarketQuote>> {
  const controller = new AbortController()
  const cancel = () => controller.abort()
  if (signal.aborted) cancel()
  else signal.addEventListener("abort", cancel, { once: true })
  // A stalled request must not leave the page showing an endless loading state.
  const timeout = setTimeout(cancel, 60_000)
  try {
    const chunks: string[][] = []
    for (let index = 0; index < symbols.length; index += 50) {
      chunks.push(symbols.slice(index, index + 50))
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

export function useMarketSnapshot(symbols: string[], refreshMs = MARKET_REFRESH_MS) {
  const { allowed, sessionKey } = useSnapshotSession()
  const client = useQueryClient()
  const requested = [...new Set(symbols.map(symbol => symbol.trim().toUpperCase()).filter(Boolean))].sort()
  return useQuery({
    queryKey: [SNAPSHOT_KEY, sessionKey, requested],
    queryFn: ({ signal }) => loadMarketSnapshot(requested, signal),
    initialData: () => allowed && requested.length ? recentMarketQuotes(client, sessionKey, requested) : undefined,
    // Carry-over values survive a failed refresh. Their age must not defer a real read.
    initialDataUpdatedAt: 0,
    refetchInterval: refreshMs,
    staleTime: refreshMs,
    refetchOnWindowFocus: true,
    retry: false,
    enabled: allowed && requested.length > 0,
  })
}

export function useLastMarketQuote(symbol: string) {
  const { allowed, sessionKey } = useSnapshotSession()
  const client = useQueryClient()
  return allowed && symbol ? recentMarketQuotes(client, sessionKey, [symbol])?.[symbol] : undefined
}
