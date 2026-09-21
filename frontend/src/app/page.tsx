"use client"

import { useEffect, useState, type ComponentType } from "react"
import Link from "next/link"
import { CalendarDays, LineChart, Activity, History, Bell, Brain } from "lucide-react"
import { SymbolSearch } from "@/components/dashboard/symbol-search"
import { MarketCategoryPanel } from "@/components/dashboard/market-category"
import { useBinanceTickerFeed } from "@/lib/hooks/use-binance-ticker"
import { useMarketSnapshot } from "@/lib/hooks/use-market-snapshot"
import { describeMarketRequest, describeTickerFeed } from "@/lib/market-feed"

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
      { id: "AAPL", label: "Apple (AAPL)", source: "indices", feedSymbol: "AAPL" },
      { id: "TSLA", label: "TSLA", source: "indices", feedSymbol: "TSLA" },
      { id: "GOOGL", label: "GOOGL", source: "indices", feedSymbol: "GOOGL" },
      { id: "VIX", label: "VIX Korku Endeksi", source: "indices", feedSymbol: "^VIX" },
    ],
  },
  {
    id: "commodities-fx",
    label: "Emtia ve Döviz",
    description: "Emtia, DXY ve USD/TRY özeti",
    items: [
      { id: "XAUUSD", label: "XAUUSD", source: "indices", feedSymbol: "XAUUSD=X" },
      { id: "XAGUSD", label: "XAGUSD", source: "indices", feedSymbol: "XAGUSD=X" },
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
export default function LandingPage() {
  const market = useMarketSnapshot(INDEX_SYMBOLS)
  const crypto = useBinanceTickerFeed(BINANCE_SYMBOLS)
  const [clock, setClock] = useState({ now: 0, startedAt: 0 })

  useEffect(() => {
    const startedAt = Date.now()
    const tick = () => setClock({ now: Date.now(), startedAt })
    tick()
    const timer = setInterval(tick, 5_000)
    document.addEventListener("visibilitychange", tick)
    return () => {
      clearInterval(timer)
      document.removeEventListener("visibilitychange", tick)
    }
  }, [])

  const categorizedMarketRows = LIVE_MARKET_CATEGORIES.map((category) => {
    const streaming = category.id === "crypto"
    const rows = category.items.map((item) => {
      const live = streaming ? crypto.prices[item.feedSymbol] : undefined
      const snapshot = streaming ? undefined : market.data?.[item.feedSymbol.toUpperCase()]
      return {
        key: item.id, label: item.label,
        value: live?.price ?? snapshot?.value,
        change: live?.change ?? snapshot?.change,
        receivedAt: streaming ? crypto.receivedAtBySymbol[item.feedSymbol] : market.dataUpdatedAt,
      }
    })
    const notice = streaming ? describeTickerFeed({
      status: crypto.status, receivedAt: rows.map((row) => row.receivedAt),
      now: clock.now, startedAt: clock.startedAt, total: rows.length,
    }) : describeMarketRequest({
      receivedAt: market.dataUpdatedAt, now: clock.now,
      available: rows.filter((row) => row.value !== undefined).length, total: rows.length,
      isError: market.isError, isFetching: market.isFetching, isPaused: market.fetchStatus === "paused",
    })
    return { ...category, rows, notice, streaming }
  })

  return (
    <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-[1680px] flex-col gap-4 p-4 md:p-5">
      <section className="border border-border bg-surface p-5">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="label-uppercase">Rapot Terminal</div>
            <h1 className="max-w-3xl text-xl font-semibold tracking-[-0.02em] md:text-2xl">
              Piyasalara genel bakış
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Piyasa özetlerini takip et. BIST veya kripto sembolü seçerek grafiğini aç.
            </p>
          </div>

          <div className="w-full min-w-0 max-w-xl">
            <SymbolSearch />
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {categorizedMarketRows.map((category) => (
          <MarketCategoryPanel
            key={category.id}
            {...category}
            now={clock.now}
            receivedAt={market.dataUpdatedAt}
            onRefresh={category.streaming ? crypto.reconnect : () => { void market.refetch({ cancelRefetch: false }) }}
            refreshing={category.streaming ? crypto.status === "connecting" : market.isFetching}
          />
        ))}
      </section>

      <section aria-labelledby="quick-links-heading" className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <h2 id="quick-links-heading" className="sr-only">Hızlı erişim</h2>
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
        <h2 className="label-uppercase mb-2">Verileri okurken</h2>
        <p>
          Süreler, tarayıcının son mesajı veya yanıtı aldığı zamanı gösterir; borsadaki işlem zamanı değildir.
          BIST, ABD, emtia ve döviz özetleri son mevcut günlük veriyi kullanır; fiyatlar gecikmeli olabilir.
          Akış veya yenileme kesilirse son alınan fiyatlar uyarıyla birlikte gösterilir.
        </p>
      </section>
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
      <h3 className="mb-1 text-sm font-semibold">{title}</h3>
      <p className="text-xs text-muted-foreground">{description}</p>
    </Link>
  )
}
