"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { mockCandlestickData } from "@/lib/mock-data"
import { Badge } from "@/components/ui/badge"

export function TradingChart() {
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        if (!chartContainerRef.current) return

        // Dynamically import to avoid SSR issues
        import("lightweight-charts").then(({ createChart, ColorType, CandlestickSeries }) => {
            if (!chartContainerRef.current) return

            // Create chart
            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: "#161b22" },
                    textColor: "#8b949e",
                },
                grid: {
                    vertLines: { color: "#21262d" },
                    horzLines: { color: "#21262d" },
                },
                width: chartContainerRef.current.clientWidth,
                height: 400,
                crosshair: {
                    mode: 1,
                    vertLine: {
                        color: "#2962ff",
                        width: 1,
                        style: 2,
                        labelBackgroundColor: "#2962ff",
                    },
                    horzLine: {
                        color: "#2962ff",
                        width: 1,
                        style: 2,
                        labelBackgroundColor: "#2962ff",
                    },
                },
                rightPriceScale: {
                    borderColor: "#30363d",
                },
                timeScale: {
                    borderColor: "#30363d",
                    timeVisible: true,
                    secondsVisible: false,
                },
            })

            // Add candlestick series - using v5 API
            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: "#00c853",
                downColor: "#ff3d00",
                borderDownColor: "#ff3d00",
                borderUpColor: "#00c853",
                wickDownColor: "#ff3d00",
                wickUpColor: "#00c853",
            })

            // Convert and set data
            const formattedData = mockCandlestickData.map((item) => ({
                time: item.time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }))

            candlestickSeries.setData(formattedData)

            // Note: Markers API changed in lightweight-charts v5
            // Signal markers would require custom primitives implementation

            // Fit content
            chart.timeScale().fitContent()

            setIsLoading(false)

            // Handle resize
            const handleResize = () => {
                if (chartContainerRef.current) {
                    chart.applyOptions({
                        width: chartContainerRef.current.clientWidth,
                    })
                }
            }

            window.addEventListener("resize", handleResize)

            // Cleanup
            return () => {
                window.removeEventListener("resize", handleResize)
                chart.remove()
            }
        })
    }, [])

    const lastCandle = mockCandlestickData[mockCandlestickData.length - 1]
    const prevCandle = mockCandlestickData[mockCandlestickData.length - 2]
    const priceChange = lastCandle.close - prevCandle.close
    const priceChangePercent = (priceChange / prevCandle.close) * 100

    return (
        <Card className="col-span-full lg:col-span-8">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-3">
                    <CardTitle className="text-base font-semibold">THYAO</CardTitle>
                    <Badge variant="bist">BIST</Badge>
                </div>
                <div className="flex items-center gap-3">
                    <span className="text-xl font-bold">
                        ₺{lastCandle.close.toFixed(2)}
                    </span>
                    <span
                        className={`text-sm font-medium ${priceChange >= 0 ? "text-profit" : "text-loss"
                            }`}
                    >
                        {priceChange >= 0 ? "+" : ""}
                        {priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)
                    </span>
                </div>
            </CardHeader>
            <CardContent className="p-0">
                <div
                    ref={chartContainerRef}
                    className="relative w-full"
                    style={{ minHeight: 400 }}
                >
                    {isLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-card">
                            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    )
}
