export const MARKET_REFRESH_MS = 10_000
export const MARKET_STALE_MS = 30_000

export interface MarketQuote {
  value: number
  change?: number
}

export interface FeedNotice {
  label: string
  description: string
  warning: boolean
  loading: boolean
}

export function finiteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value)
}

// A successful request may omit symbols. Never reuse an omitted symbol from an
// older response, or coerce null/string prices into plausible numbers.
export function normalizeMarketQuotes(payload: unknown, symbols: readonly string[]) {
  if (!Array.isArray(payload)) throw new Error("Geçersiz piyasa yanıtı")
  const requested = new Set(symbols.map((symbol) => symbol.toUpperCase()))
  const quotes: Record<string, MarketQuote> = {}
  for (const item of payload) {
    if (!item || typeof item !== "object" || typeof item.symbol !== "string") continue
    const symbol = item.symbol.toUpperCase()
    if (!requested.has(symbol) || !finiteNumber(item.regularMarketPrice)) continue
    quotes[symbol] = {
      value: item.regularMarketPrice,
      ...(finiteNumber(item.regularMarketChangePercent)
        ? { change: item.regularMarketChangePercent } : {}),
    }
  }
  return quotes
}

export function receivedAge(receivedAt: number | undefined, now: number): string {
  if (!receivedAt || !now) return "Henüz alınmadı"
  const seconds = Math.max(0, Math.floor((now - receivedAt) / 1000))
  if (seconds < 10) return "Az önce"
  if (seconds < 60) return `${seconds} sn önce`
  if (seconds < 3600) return `${Math.floor(seconds / 60)} dk önce`
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} sa önce`
  return `${Math.floor(seconds / 86_400)} gün önce`
}

export function isFeedStale(receivedAt: number | undefined, now: number): boolean {
  return !!receivedAt && now - receivedAt >= MARKET_STALE_MS
}

export function describeMarketRequest({
  receivedAt, now, available, total, isError, isFetching, isPaused,
}: {
  receivedAt: number
  now: number
  available: number
  total: number
  isError: boolean
  isFetching: boolean
  isPaused: boolean
}): FeedNotice {
  const previous = available > 0 ? "Son alınan fiyatlar gösteriliyor." : "Fiyatlar alınamadı."
  if (isPaused) return {
    label: "Bağlantı bekleniyor", description: `${previous} Bağlantı gelince tekrar denenecek.`,
    warning: true, loading: false,
  }
  if (isError) return {
    label: "Yenilenemedi", description: `${previous} Yeniden deneyebilirsiniz.`,
    warning: true, loading: isFetching,
  }
  if (!receivedAt) return {
    label: "Yükleniyor", description: "Piyasa özeti alınıyor.", warning: false, loading: true,
  }
  if (isFeedStale(receivedAt, now)) return {
    label: "Yenileme gecikti", description: `${previous} Yeni yanıt bekleniyor.`,
    warning: true, loading: isFetching,
  }
  if (available < total) return {
    label: available === 0 ? "Veri yok" : "Eksik veri",
    description: available === 0
      ? "Bu grupta gösterilebilecek fiyat dönmedi. Yeniden deneyebilirsiniz."
      : `${total - available} enstrümanın fiyatı yanıt içinde yok.`,
    warning: true, loading: isFetching,
  }
  return {
    label: "Veri alındı",
    description: "10 saniyede bir kontrol edilir; fiyatlar gecikmeli olabilir.",
    warning: false, loading: isFetching,
  }
}

export function describeTickerFeed({ status, receivedAt, now, total, startedAt = 0 }: {
  status: "connecting" | "connected" | "reconnecting" | "offline" | "paused"
  receivedAt: Array<number | undefined>
  now: number
  total: number
  startedAt?: number
}): FeedNotice {
  const available = receivedAt.filter((value): value is number => !!value)
  if (status === "reconnecting" || status === "offline" || status === "paused") return {
    label: status === "reconnecting" ? "Yeniden bağlanıyor" : "Akış kesildi",
    description: available.length ? "Son alınan fiyatlar gösteriliyor." : "Bağlantı kurulunca fiyatlar görünecek.",
    warning: true, loading: false,
  }
  if (status === "connecting" || available.length === 0) {
    if (startedAt && now - startedAt >= MARKET_STALE_MS) return {
      label: "Veri alınamadı", description: "Henüz geçerli fiyat gelmedi. Bağlantıyı yenileyebilirsiniz.",
      warning: true, loading: false,
    }
    return {
      label: status === "connecting" ? "Bağlanıyor" : "Veri bekleniyor",
      description: "Binance akışından fiyat bekleniyor.", warning: false, loading: true,
    }
  }
  if (available.some((value) => isFeedStale(value, now))) return {
    label: "Akış gecikti", description: "Bazı fiyatlar için 30 saniyedir yeni veri alınmadı.",
    warning: true, loading: false,
  }
  if (available.length < total) return {
    label: "Eksik veri", description: `${total - available.length} enstrüman için veri bekleniyor.`,
    warning: true, loading: false,
  }
  return {
    label: "Akış alınıyor", description: "Binance fiyat akışından veri geliyor.",
    warning: false, loading: false,
  }
}
