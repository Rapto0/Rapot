"use client"

import { useEffect, useMemo, useState, type ComponentType, type KeyboardEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Search, ArrowRight, LayoutDashboard, CalendarDays, LineChart, Activity } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { fetchGlobalIndices, type GlobalIndexData } from "@/lib/api/client"
import { cn } from "@/lib/utils"

export default function LandingPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [marketData, setMarketData] = useState<Record<string, GlobalIndexData>>({})
  const btcTicker = useBinanceTicker(["BTCUSDT"])

  useEffect(() => {
    const loadIndices = async () => {
      const data = await fetchGlobalIndices(["^GSPC", "^NDX", "XU100.IS"])
      const next: Record<string, GlobalIndexData> = {}
      for (const item of data) {
        next[item.symbol] = item
      }
      setMarketData(next)
    }

    loadIndices()
    const timer = setInterval(loadIndices, 60_000)
    return () => clearInterval(timer)
  }, [])

  const btcPrice = btcTicker.BTCUSDT?.price ?? null
  const btcChange = btcTicker.BTCUSDT?.change ?? null

  const marketRows = useMemo(
    () => [
      {
        label: "S&P 500",
        value: marketData["^GSPC"]?.regularMarketPrice,
        change: marketData["^GSPC"]?.regularMarketChangePercent,
      },
      {
        label: "NASDAQ 100",
        value: marketData["^NDX"]?.regularMarketPrice,
        change: marketData["^NDX"]?.regularMarketChangePercent,
      },
      {
        label: "BTCUSDT",
        value: btcPrice,
        change: btcChange,
      },
      {
        label: "BIST 100",
        value: marketData["XU100.IS"]?.regularMarketPrice,
        change: marketData["XU100.IS"]?.regularMarketChangePercent,
      },
    ],
    [btcChange, btcPrice, marketData]
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
            <h1 className="max-w-3xl text-2xl font-semibold tracking-[-0.02em] md:text-[30px]">
              Kripto ve BIST için veri odaklı izleme, analiz ve sinyal akışı
            </h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Piyasa hareketlerini tek ekrandan takip et, sembol ara ve doğrudan grafik görünümüne geç.
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

      <section className="grid grid-cols-1 gap-2 border border-border bg-surface p-2 md:grid-cols-4">
        {marketRows.map((item) => (
          <MarketStrip key={item.label} label={item.label} value={item.value} change={item.change} />
        ))}
      </section>

      <section className="grid grid-cols-1 gap-2 md:grid-cols-2 lg:grid-cols-4">
        <QuickLinkCard
          href="/dashboard"
          title="Dashboard"
          description="Canlı chart + indikatör + izleme listesi"
          icon={LayoutDashboard}
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

  return (
    <div className="border border-border bg-base px-3 py-2">
      <div className="label-uppercase mb-1">{label}</div>
      <div className="mono-numbers text-lg font-semibold">
        {typeof value === "number" ? value.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) : "--"}
      </div>
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
