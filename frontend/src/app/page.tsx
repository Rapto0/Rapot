"use client"

import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, ArrowRight, TrendingUp, Globe, BarChart3, Newspaper } from "lucide-react"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { fetchGlobalIndices, type GlobalIndexData } from "@/lib/api/client"
import { GlobalTicker } from "@/components/dashboard/global-ticker"
import { useEffect, useState, KeyboardEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"

export default function LandingPage() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")

  // 1. Live Crypto Data (Client-side WebSocket)
  const cryptoPrices = useBinanceTicker(["BTCUSDT"])

  // 2. Live Market Data (Server Action -> Client State)
  const [marketData, setMarketData] = useState<Record<string, GlobalIndexData>>({})

  useEffect(() => {
    const fetchIndices = async () => {
      const data = await fetchGlobalIndices(["^GSPC", "^NDX", "XU100.IS"])
      const map: Record<string, GlobalIndexData> = {}
      data.forEach(item => map[item.symbol] = item)
      setMarketData(map)
    }
    fetchIndices()
    const interval = setInterval(fetchIndices, 60000)
    return () => clearInterval(interval)
  }, [])

  // Handle search - navigate to chart page with symbol
  const handleSearch = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && searchQuery.trim()) {
      const symbol = searchQuery.trim().toUpperCase()
      // Determine market type based on symbol
      const marketType = symbol.includes("USDT") || symbol.includes("BTC") || symbol.includes("ETH")
        ? "Kripto"
        : "BIST"
      router.push(`/chart?symbol=${encodeURIComponent(symbol)}&market=${marketType}`)
    }
  }

  // Helper to format values
  const btcPrice = cryptoPrices["BTCUSDT"]?.price
    ? cryptoPrices["BTCUSDT"].price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : "---"
  const btcChange = cryptoPrices["BTCUSDT"]?.change
    ? `${cryptoPrices["BTCUSDT"].change > 0 ? '+' : ''}${cryptoPrices["BTCUSDT"].change.toFixed(2)}%`
    : "---"

  // Navigate to chart with specific symbol
  const navigateToChart = (symbol: string, market: string) => {
    router.push(`/chart?symbol=${encodeURIComponent(symbol)}&market=${market}`)
  }

  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-[#131722] text-[#d1d4dc] -m-4">
      {/* Global Ticker - Only on Homepage */}
      <GlobalTicker />

      {/* Main Content */}
      <div className="p-4 md:p-8">
      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center py-20 md:py-32 text-center relative overflow-hidden min-h-[600px]">
        {/* Background Image - Rapot.png */}
        <div className="absolute inset-0 z-0">
          <img
            src="/Rapot.png"
            alt="Rapot Background"
            className="w-full h-full object-cover"
          />
          {/* Gradient overlay for text readability */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#131722]/30 via-[#131722]/50 to-[#131722] pointer-events-none" />
        </div>

        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight z-10 mb-6 drop-shadow-2xl">
          Piyasalarla aranızı <br className="hidden md:block" />
          <span className="text-white drop-shadow-[0_0_15px_rgba(255,100,50,0.5)]">düzeltin</span>
        </h1>

        <p className="text-lg md:text-xl text-[#d1d4dc] max-w-2xl mb-10 z-10 px-4 drop-shadow-md">
          Dünyanın en popüler grafik platformu ve işlemci sosyal ağına katılın.
          Piyasaları takip edin, analiz yapın ve işlem stratejilerinizi geliştirin.
        </p>

        {/* Search Bar - Functional */}
        <div className="relative w-full max-w-xl z-10 px-4">
          <div className="relative group">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[#787b86] h-5 w-5 group-focus-within:text-[#2962ff] transition-colors" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
              className="w-full h-14 pl-12 pr-4 rounded-full bg-[#1e222d] border-[#2a2e39] text-lg text-[#d1d4dc] placeholder:text-[#50535e] focus-visible:ring-2 focus-visible:ring-[#2962ff] shadow-lg transition-all"
              placeholder="Sembol, parite veya işlem çifti arayın... (Enter ile ara)"
            />
          </div>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 mt-8 z-10">
          <Link href="/chart">
            <Button size="lg" className="h-12 px-8 rounded-full bg-[#2962ff] hover:bg-[#1e53e5] text-white text-base">
              Grafikleri Keşfet
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
          <Link href="/calendar">
            <Button size="lg" variant="outline" className="h-12 px-8 rounded-full border-[#d1d4dc] text-[#d1d4dc] hover:bg-[#d1d4dc] hover:text-[#131722] bg-transparent text-base">
              Ekonomik Takvim
            </Button>
          </Link>
        </div>
      </section>

      {/* Market Summary Grid - Clickable Cards */}
      <section className="max-w-7xl mx-auto w-full py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MarketCard
            title="S&P 500"
            value={marketData["^GSPC"]?.regularMarketPrice.toLocaleString('en-US') || "---"}
            change={marketData["^GSPC"] ? `${marketData["^GSPC"].regularMarketChangePercent > 0 ? '+' : ''}${marketData["^GSPC"].regularMarketChangePercent.toFixed(2)}%` : "---"}
            isPositive={(marketData["^GSPC"]?.regularMarketChangePercent || 0) > 0}
            icon={Globe}
            onClick={() => navigateToChart("SPY", "BIST")}
          />
          <MarketCard
            title="Nasdaq 100"
            value={marketData["^NDX"]?.regularMarketPrice.toLocaleString('en-US') || "---"}
            change={marketData["^NDX"] ? `${marketData["^NDX"].regularMarketChangePercent > 0 ? '+' : ''}${marketData["^NDX"].regularMarketChangePercent.toFixed(2)}%` : "---"}
            isPositive={(marketData["^NDX"]?.regularMarketChangePercent || 0) > 0}
            icon={BarChart3}
            onClick={() => navigateToChart("QQQ", "BIST")}
          />
          <MarketCard
            title="Bitcoin"
            value={btcPrice}
            change={btcChange}
            isPositive={!btcChange.startsWith("-") && btcChange !== "---"}
            icon={TrendingUp}
            onClick={() => navigateToChart("BTCUSDT", "Kripto")}
          />
          <MarketCard
            title="BIST 100"
            value={marketData["XU100.IS"]?.regularMarketPrice.toLocaleString('tr-TR') || "---"}
            change={marketData["XU100.IS"] ? `${marketData["XU100.IS"].regularMarketChangePercent > 0 ? '+' : ''}${marketData["XU100.IS"].regularMarketChangePercent.toFixed(2)}%` : "---"}
            isPositive={(marketData["XU100.IS"]?.regularMarketChangePercent || 0) > 0}
            icon={Newspaper}
            onClick={() => navigateToChart("XU100", "BIST")}
          />
        </div>
      </section>

      {/* Features Section */}
      <section className="max-w-7xl mx-auto w-full py-20 px-4">
        <h2 className="text-3xl font-bold mb-12 text-center text-[#d1d4dc]">Neden Rapot?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            title="Profesyonel Grafikler"
            description="TradingView altyapısını kullanan gelişmiş grafik kütüphanesi ile teknik analizin sınırlarını zorlayın."
          />
          <FeatureCard
            title="Gerçek Zamanlı Veri"
            description="BIST ve Kripto piyasalarından anlık veri akışı ile hiçbir fırsatı kaçırmayın."
          />
          <FeatureCard
            title="Topluluk Odaklı"
            description="Binlerce yatırımcı ile fikirlerinizi paylaşın, stratejileri tartışın ve birlikte kazanın."
          />
        </div>
      </section>
      </div>
    </div>
  )
}

interface MarketCardProps {
  title: string
  value: string
  change: string
  isPositive: boolean
  icon: React.ComponentType<{ className?: string }>
  onClick?: () => void
}

function MarketCard({ title, value, change, isPositive, icon: Icon, onClick }: MarketCardProps) {
  return (
    <div
      onClick={onClick}
      className="flex flex-col p-6 rounded-2xl bg-[#1e222d] border border-[#2a2e39] hover:border-[#2962ff] transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className="p-2 rounded-lg bg-[#2a2e39] group-hover:bg-[#2962ff]/10 group-hover:text-[#2962ff] transition-colors">
          <Icon className="h-6 w-6" />
        </div>
        <span className={`text-sm font-bold px-2 py-1 rounded ${isPositive ? 'bg-[#089981]/10 text-[#089981]' : 'bg-[#f23645]/10 text-[#f23645]'}`}>
          {change}
        </span>
      </div>
      <h3 className="text-muted-foreground text-sm font-medium mb-1">{title}</h3>
      <p className="text-2xl font-bold text-[#d1d4dc]">{value}</p>
    </div>
  )
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="text-center p-6">
      <h3 className="text-xl font-bold text-[#d1d4dc] mb-3">{title}</h3>
      <p className="text-[#787b86] leading-relaxed">{description}</p>
    </div>
  )
}
