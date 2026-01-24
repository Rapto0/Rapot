"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AIAnalysisWidget } from "@/components/dashboard/ai-analysis-widget"
import { cn } from "@/lib/utils"
import { useDashboardStore } from "@/lib/stores"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { useQuery } from "@tanstack/react-query"
import { fetchTicker, fetchCandles, fetchAIAnalysis } from "@/lib/api/client"
import { Loader2, ExternalLink, TrendingUp, TrendingDown, Activity, BrainCircuit, AlertCircle } from "lucide-react"

export function SidebarDetail() {
    const { selectedSymbol } = useDashboardStore()

    // Determine market type
    const isCrypto = selectedSymbol.endsWith("USDT")
    const marketType = isCrypto ? "Kripto" : "BIST"

    // Crypto Data (Live WebSocket)
    const cryptoPrices = useBinanceTicker(isCrypto ? [selectedSymbol] : [])
    const cryptoData = isCrypto ? cryptoPrices[selectedSymbol] : null

    // BIST Ticker Data (General list)
    const { data: bistTickerData } = useQuery({
        queryKey: ['ticker'],
        queryFn: fetchTicker,
        enabled: !isCrypto,
        refetchInterval: 15000,
        select: (data) => data.find(t => t.symbol === selectedSymbol)
    })

    // Fallback: Specific Symbol Data (if not in general ticker list)
    // We use fetchCandles(1) to get the latest price if ticker fails
    const { data: specificSymbolData, isLoading: isSpecificLoading } = useQuery({
        queryKey: ['latest_price', selectedSymbol],
        queryFn: async () => {
            const response = await fetchCandles(selectedSymbol, marketType, isCrypto ? "1h" : "1d", 2)
            if (response.candles && response.candles.length > 0) {
                const latest = response.candles[response.candles.length - 1]
                const prev = response.candles.length > 1 ? response.candles[response.candles.length - 2] : null
                return {
                    price: latest.close,
                    change: prev ? ((latest.close - prev.close) / prev.close) * 100 : 0
                }
            }
            return null
        },
        enabled: !isCrypto && !bistTickerData, // Only fetch if not crypto and not found in ticker
        refetchInterval: 30000
    })

    // AI Analysis Data
    const { data: analysis, isLoading: analysisLoading, isError: analysisError } = useQuery({
        queryKey: ['ai_analysis', selectedSymbol],
        queryFn: () => fetchAIAnalysis(selectedSymbol, marketType),
        enabled: !!selectedSymbol,
        staleTime: 1000 * 60 * 5, // 5 minutes
    })

    // Unified Data Resolution
    let currentPrice = null
    let currentChange = null

    if (isCrypto) {
        currentPrice = cryptoData?.price
        currentChange = cryptoData?.change
    } else {
        // Prefer ticker stream, fallback to specific fetch
        if (bistTickerData) {
            currentPrice = bistTickerData.price
            currentChange = bistTickerData.changePercent // API returns 'changePercent' as number
        } else if (specificSymbolData) {
            currentPrice = specificSymbolData.price
            currentChange = specificSymbolData.change
        }
    }

    // Loading State
    // It is loading if we are waiting for data AND we don't have it yet
    const isLoading = (
        (isCrypto && !cryptoData) ||
        (!isCrypto && !bistTickerData && isSpecificLoading && !specificSymbolData)
    )

    return (
        <div className="flex flex-1 flex-col bg-[#1e222d] border-t border-[#2a2e39]">
            {/* Header Area */}
            <div className="border-b border-[#2a2e39] px-4 py-3">
                <div className="flex justify-between items-start">
                    <div className="flex items-center gap-2">
                        {/* Flag/Icon */}
                        <div className={cn(
                            "flex h-5 w-5 items-center justify-center rounded-sm overflow-hidden text-[10px] font-bold",
                            isCrypto ? "bg-[#f7931a] text-white" : "bg-white text-black"
                        )}>
                            {isCrypto ? "₿" : "🇹🇷"}
                        </div>
                        <div>
                            <h3 className="text-lg font-bold text-[#d1d4dc] leading-none">{selectedSymbol}</h3>
                            <p className="text-xs text-[#787b86] mt-1">
                                {isCrypto ? `${selectedSymbol.replace('USDT', '')} / Tether` : "Borsa İstanbul"}
                            </p>
                        </div>
                    </div>
                    <div className="flex h-5 items-center gap-1.5 rounded-full bg-[#089981]/10 px-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-[#089981] animate-pulse" />
                        <span className="text-[10px] font-medium text-[#089981]">Piyasa açık</span>
                    </div>
                </div>

                <div className="mt-4">
                    {isLoading ? (
                        <div className="flex items-center gap-2">
                            <Loader2 className="h-6 w-6 animate-spin text-[#787b86]" />
                            <span className="text-sm text-[#787b86]">Yükleniyor...</span>
                        </div>
                    ) : (
                        <>
                            <span className="text-4xl font-bold text-[#d1d4dc] tracking-tight tabular-nums">
                                {currentPrice?.toLocaleString('tr-TR', {
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: isCrypto ? 4 : 2
                                })}
                            </span>
                            <div className="flex items-center gap-2 mt-1">
                                <span className={cn(
                                    "text-sm font-medium tabular-nums",
                                    (currentChange || 0) >= 0 ? "text-[#089981]" : "text-[#f23645]"
                                )}>
                                    {(currentChange || 0) >= 0 ? "+" : ""}
                                    {((currentPrice || 0) * ((currentChange || 0) / 100)).toFixed(2)}
                                </span>
                                <span className={cn(
                                    "text-sm font-medium tabular-nums",
                                    (currentChange || 0) >= 0 ? "text-[#089981]" : "text-[#f23645]"
                                )}>
                                    ({(currentChange || 0) >= 0 ? "+" : ""}
                                    {(currentChange || 0).toFixed(2)}%)
                                </span>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Bottom Tabs */}
            <Tabs defaultValue="performance" className="flex flex-col flex-1">
                <div className="p-2 border-b border-[#2a2e39]">
                    <TabsList className="grid w-full grid-cols-2 bg-[#131722] h-8">
                        <TabsTrigger value="performance" className="text-xs h-7 data-[state=active]:bg-[#2a2e39] data-[state=active]:text-[#d1d4dc] text-[#787b86]">Performans</TabsTrigger>
                        <TabsTrigger value="ai" className="text-xs h-7 data-[state=active]:bg-[#2a2e39] data-[state=active]:text-[#d1d4dc] text-[#787b86]">AI Analizi</TabsTrigger>
                    </TabsList>
                </div>

                {/* Performance Content */}
                <TabsContent value="performance" className="flex-1 mt-0">
                    <ScrollArea className="h-full">
                        <div className="p-4 grid grid-cols-3 gap-2">
                            <PerformanceCard period="1H" value="+2.4%" positive={true} />
                            <PerformanceCard period="1A" value="-1.2%" positive={false} />
                            <PerformanceCard period="YB" value="+15.8%" positive={true} />
                        </div>
                    </ScrollArea>
                </TabsContent>

                {/* AI Analysis Tab */}
                <TabsContent value="ai" className="h-full mt-0">
                    {analysisLoading ? (
                        <AIAnalysisWidget symbol={selectedSymbol} isLoading={true} />
                    ) : analysisError ? (
                        <div className="flex flex-col items-center justify-center h-48 text-[#ef5350]">
                            <AlertCircle className="h-8 w-8 mb-2" />
                            <p className="text-sm">Analiz hatası</p>
                        </div>
                    ) : (
                        <AIAnalysisWidget
                            symbol={selectedSymbol}
                            isLoading={false}
                            data={analysis?.structured_analysis}
                        />
                    )}
                </TabsContent>
            </Tabs>
        </div>
    )
}

function PerformanceCard({ period, value, positive }: { period: string; value: string; positive: boolean }) {
    return (
        <div className="flex flex-col rounded border border-[#2a2e39] bg-[#131722] p-2">
            <span className="text-[10px] text-[#787b86] uppercase">{period}</span>
            <span className={cn(
                "text-sm font-medium tabular-nums",
                positive ? "text-[#089981]" : "text-[#f23645]"
            )}>{value}</span>
        </div>
    )
}
