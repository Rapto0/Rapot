"use client"

import { useEffect, useMemo, useState, type ComponentType, type KeyboardEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Search, ArrowRight, CalendarDays, LineChart, Activity, History, Bell, Brain } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { fetchGlobalIndices, type GlobalIndexData } from "@/lib/api/client"
import { cn } from "@/lib/utils"

type MarketFeedSource = "binance" | "indices"

interface MarketInstrument {
  id: string
  label: string
  source: MarketFeedSource
  feedSymbol: string
}

interface MarketCategory {
  id: string
  label: string
  description: string
  items: MarketInstrument[]
}

const LIVE_MARKET_CATEGORIES: MarketCategory[] = [
  {
    id: "crypto",
    label: "Kripto",
    description: "Canlı Binance akışı",
    items: [
      { id: "BTCUSDT", label: "BTCUSDT", source: "binance", feedSymbol: "BTCUSDT" },
      { id: "ETHUSDT", label: "ETHUSDT", source: "binance", feedSymbol: "ETHUSDT" },
      { id: "BNBUSDT", label: "BNBUSDT", source: "binance", feedSymbol: "BNBUSDT" },
      { id: "SOLUSDT", label: "SOLUSDT", source: "binance", feedSymbol: "SOLUSDT" },
    ],
  },
  {
    id: "bist",
    label: "BIST",
    description: "Türkiye endeks ve hisseleri",
    items: [
      { id: "XU100", label: "XU100", source: "indices", feedSymbol: "XU100.IS" },
      { id: "ASELS", label: "ASELS", source: "indices", feedSymbol: "ASELS.IS" },
      { id: "TUPRS", label: "TUPRS", source: "indices", feedSymbol: "TUPRS.IS" },
      { id: "THYAO", label: "THYAO", source: "indices", feedSymbol: "THYAO.IS" },
    ],
  },
  {
    id: "us-market",
    label: "ABD Piyasaları",
    description: "ABD endeks, hisse ve volatilite",
    items: [
      { id: "NASDAQ100", label: "NASDAQ 100", source: "indices", feedSymbol: "^NDX" },
      { id: "SP500", label: "S&P 500", source: "indices", feedSymbol: "^GSPC" },
      { id: "NVDA", label: "NVDA", source: "indices", feedSymbol: "NVDA" },
      { id: "AAPL", label: "AAPLE (AAPL)", source: "indices", feedSymbol: "AAPL" },
      { id: "TSLA", label: "TSLA", source: "indices", feedSymbol: "TSLA" },
      { id: "GOOGL", label: "GOOGL", source: "indices", feedSymbol: "GOOGL" },
      { id: "VIX", label: "VIX Korku Endeksi", source: "indices", feedSymbol: "^VIX" },
    ],
  },
  {
    id: "commodities-fx",
    label: "Emtia ve Döviz",
    description: "Spot emtia, DXY ve USD/TRY",
    items: [
      { id: "XAUUSD", label: "Spot Altın", source: "indices", feedSymbol: "XAUUSD=X" },
      { id: "XAGUSD", label: "Spot Gümüş", source: "indices", feedSymbol: "XAGUSD=X" },
      { id: "OIL", label: "Spot Petrol", source: "indices", feedSymbol: "CL=F" },
      { id: "DXY", label: "DXY", source: "indices", feedSymbol: "DX-Y.NYB" },
      { id: "USDTRY", label: "Dolar/TL", source: "indices", feedSymbol: "TRY=X" },
    ],
  },
]

const BINANCE_SYMBOLS = LIVE_MARKET_CATEGORIES.flatMap((category) =>
  category.items.filter((item) => item.source === "binance").map((item) => item.feedSymbol)
)

const INDEX_SYMBOLS = LIVE_MARKET_CATEGORIES.flatMap((category) =>
  category.items.filter((item) => item.source === "indices").map((item) => item.feedSymbol)
)

function chunkSymbols(symbols: string[], size: number): string[][] {
  const chunks: string[][] = []
  for (let index = 0; index < symbols.length; index += size) {
    chunks.push(symbols.slice(index, index + size))
  }
  return chunks
}

export default function LandingPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [marketData, setMarketData] = useState<Record<string, GlobalIndexData>>({})
  const cryptoTicker = useBinanceTicker(BINANCE_SYMBOLS)

  useEffect(() => {
    const loadIndices = async () => {
      try {
        const chunks = chunkSymbols(INDEX_SYMBOLS, 10)
        const responses = await Promise.all(chunks.map((chunk) => fetchGlobalIndices(chunk)))
        const next: Record<string, GlobalIndexData> = {}

        for (const item of responses.flat()) {
          next[item.symbol.toUpperCase()] = item
        }

        setMarketData(next)
      } catch (error) {
        console.error("Market indices load error:", error)
      }
    }

    loadIndices()
    const timer = setInterval(loadIndices, 30_000)
    return () => clearInterval(timer)
  }, [])

  const categorizedMarketRows = useMemo(
    () =>
      LIVE_MARKET_CATEGORIES.map((category) => ({
        ...category,
        rows: category.items.map((item) => {
          if (item.source === "binance") {
            const live = cryptoTicker[item.feedSymbol]
            return {
              key: item.id,
              label: item.label,
              value: live?.price,
              change: live?.change,
            }
          }

          const live = marketData[item.feedSymbol.toUpperCase()]
          return {
            key: item.id,
            label: item.label,
            value: live?.regularMarketPrice,
            change: live?.regularMarketChangePercent,
          }
        }),
      })),
    [cryptoTicker, marketData]
  )

  const handleSearch = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key !== "Enter") return

    const symbol = searchQuery.trim().toUpperCase()
    if (!symbol) return

    const market = symbol.includes("USDT") || symbol.includes("BTC") || symbol.includes("ETH") ? "Kripto" : "BIST"
    router.push(`/chart?symbol=${encodeURIComponent(symbol)}&market=${market}`)
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-[1680px] flex-col gap-4 p-4 md:p-5">
      <section className="border border-border bg-surface p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="label-uppercase">Rapot Terminal</div>
            <h1 className="max-w-3xl text-xl font-semibold tracking-[-0.02em] md:text-2xl">
              Kripto, BIST, ABD ve emtia tarafında veri odaklı izleme, analiz ve sinyal akışı
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Canlı fiyatları kategori bazlı takip et, sembol ara ve doğrudan grafik görünümüne geç.
            </p>
          </div>

          <div className="w-full max-w-xl">
            <label className="label-uppercase mb-2 block">Sembol Arama</label>
            <div className="relative flex items-center gap-2">
              <Search className="pointer-events-none absolute left-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                onKeyDown={handleSearch}
                className="h-9 pl-9"
                placeholder="Örn: BTCUSDT, THYAO"
              />
              <Button
                type="button"
                className="h-9 shrink-0"
                onClick={() => {
                  const symbol = searchQuery.trim().toUpperCase()
                  if (!symbol) return
                  const market = symbol.includes("USDT") || symbol.includes("BTC") || symbol.includes("ETH") ? "Kripto" : "BIST"
                  router.push(`/chart?symbol=${encodeURIComponent(symbol)}&market=${market}`)
                }}
              >
                Aç
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {categorizedMarketRows.map((category) => (
          <article key={category.id} className="border border-border bg-surface p-3">
            <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.04)] pb-2">
              <div>
                <div className="label-uppercase">{category.label}</div>
                <p className="mt-1 text-[10px] text-muted-foreground">{category.description}</p>
              </div>
              <span className="mono-numbers text-[10px] text-muted-foreground">{category.rows.length} enstrüman</span>
            </div>

            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {category.rows.map((item) => (
                <MarketStrip key={item.key} label={item.label} value={item.value} change={item.change} />
              ))}
            </div>
          </article>
        ))}
      </section>

      <section className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <QuickLinkCard
          href="/trades"
          title="İşlemler"
          description="Açık ve kapalı pozisyon kayıtları"
          icon={History}
        />
        <QuickLinkCard
          href="/signals"
          title="Sinyaller"
          description="Canlı sinyal akışı ve filtreler"
          icon={Bell}
        />
        <QuickLinkCard
          href="/ai"
          title="AI"
          description="AI terminali ve analiz arşivi"
          icon={Brain}
        />
        <QuickLinkCard
          href="/chart"
          title="Gelişmiş Grafik"
          description="Sembol bazlı teknik analiz ekranı"
          icon={LineChart}
        />
        <QuickLinkCard
          href="/scanner"
          title="Piyasa Tarayıcı"
          description="BIST ve Kripto tarama sonuçları"
          icon={Activity}
        />
        <QuickLinkCard
          href="/calendar"
          title="Ekonomik Takvim"
          description="Yaklaşan veri ve olay takibi"
          icon={CalendarDays}
        />
      </section>

      <section className="border border-border bg-surface p-4 text-xs text-muted-foreground">
        <div className="label-uppercase mb-2">Not</div>
        <p>
          Renkler yalnızca veri anlamı için kullanılır. Pozitif değerler yeşil, negatif değerler kırmızı olarak gösterilir.
        </p>
      </section>
    </div>
  )
}

function MarketStrip({
  label,
  value,
  change,
}: {
  label: string
  value: number | null | undefined
  change: number | null | undefined
}) {
  const hasChange = typeof change === "number"
  const isPositive = (change ?? 0) >= 0
  const formattedValue =
    typeof value === "number"
      ? Math.abs(value) >= 1000
        ? value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })
        : Math.abs(value) >= 1
          ? value.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          : value.toLocaleString("tr-TR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })
      : "--"

  return (
    <div className="border border-border bg-base px-3 py-2">
      <div className="label-uppercase mb-1">{label}</div>
      <div className="mono-numbers text-lg font-semibold">{formattedValue}</div>
      <div className={cn("mono-numbers text-xs", hasChange ? (isPositive ? "text-profit" : "text-loss") : "text-muted-foreground")}>
        {hasChange ? `${isPositive ? "+" : ""}${(change ?? 0).toFixed(2)}%` : "--"}
      </div>
    </div>
  )
}

function QuickLinkCard({
  href,
  title,
  description,
  icon: Icon,
}: {
  href: string
  title: string
  description: string
  icon: ComponentType<{ className?: string }>
}) {
  return (
    <Link href={href} className="group border border-border bg-surface p-4 transition-colors hover:bg-raised">
      <div className="mb-3 flex h-8 w-8 items-center justify-center border border-border bg-base text-muted-foreground group-hover:text-foreground">
        <Icon className="h-4 w-4" />
      </div>
      <h2 className="mb-1 text-sm font-semibold">{title}</h2>
      <p className="text-xs text-muted-foreground">{description}</p>
    </Link>
  )
}
