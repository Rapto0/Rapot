"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { useQuery } from "@tanstack/react-query"
import { fetchCandles } from "@/lib/api/client"
import { useDashboardStore } from "@/lib/stores"

interface TradingChartProps {
    symbol?: string
}

export function TradingChart({ symbol: propSymbol }: TradingChartProps) {
    const { selectedSymbol } = useDashboardStore()
    const symbol = propSymbol || selectedSymbol || "THYAO"

    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)

    // Fetch real candle data
    const { data: candles, isLoading } = useQuery({
        queryKey: ['candles', symbol],
        queryFn: (() => fetchCandles(symbol, '1d', 200)),
        refetchInterval: 60000,
    })

    useEffect(() => {
        if (!chartContainerRef.current) return

        // Dynamically import to avoid SSR issues
        import("lightweight-charts").then(({ createChart, ColorType, CandlestickSeries }) => {
            if (!chartContainerRef.current) return

            // Create chart if not exists
            if (!chartInstance.current) {
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
                    rightPriceScale: {
                        borderColor: "#30363d",
                    },
                    timeScale: {
                        borderColor: "#30363d",
                        timeVisible: true,
                        secondsVisible: false,
                    },
                })

                // Add candlestick series
                const candlestickSeries = chart.addSeries(CandlestickSeries, {
                    upColor: "#00c853",
                    downColor: "#ff3d00",
                    borderDownColor: "#ff3d00",
                    borderUpColor: "#00c853",
                    wickDownColor: "#ff3d00",
                    wickUpColor: "#00c853",
                })

                chartInstance.current = chart
                seriesInstance.current = candlestickSeries

                // Handle resize
                const handleResize = () => {
                    if (chartContainerRef.current && chartInstance.current) {
                        chartInstance.current.applyOptions({
                            width: chartContainerRef.current.clientWidth,
                        })
                    }
                }
                window.addEventListener("resize", handleResize)
            }
        })

        // Cleanup not strictly necessary as refs persist, but good practice if component unmounts
        return () => {
            if (chartInstance.current) {
                // chartInstance.current.remove() // Keeping it simple to avoid recreation issues in strict mode
            }
        }
    }, [])

    // Update data when candles change
    useEffect(() => {
        if (candles && seriesInstance.current && candles.length > 0) {
            const formattedData = candles.map((item) => ({
                time: item.time,
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }))

            // Sort by time just in case
            formattedData.sort((a, b) => (new Date(a.time).getTime() - new Date(b.time).getTime()))

            try {
                seriesInstance.current.setData(formattedData)
                chartInstance.current?.timeScale().fitContent()
            } catch (e) {
                console.error("Chart update error", e)
            }
        }
    }, [candles])

    return (
        <Card className="col-span-full lg:col-span-8">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
                <div className="flex items-center gap-3">
                    <CardTitle className="text-base font-semibold">{symbol}</CardTitle>
                    <Badge variant="outline" className="bg-blue-500/20 text-blue-400 border-transparent">
                        BIST
                    </Badge>
                </div>
                {isLoading && <div className="text-xs text-muted-foreground animate-pulse">Yükleniyor...</div>}
                {!isLoading && candles && candles.length > 0 && (
                    <div className="flex items-center gap-3">
                        <span className="text-xl font-bold">
                            ₺{candles[candles.length - 1].close.toFixed(2)}
                        </span>
                        {/* Calculate change from previous candle */}
                        {candles.length > 1 && (() => {
                            const current = candles[candles.length - 1].close
                            const prev = candles[candles.length - 2].close
                            const change = current - prev
                            const percent = (change / prev) * 100
                            const isPositive = change >= 0

                            return (
                                <span className={`text-sm font-medium ${isPositive ? 'text-profit' : 'text-loss'}`}>
                                    {isPositive ? '+' : ''}{change.toFixed(2)} ({isPositive ? '+' : ''}{percent.toFixed(2)}%)
                                </span>
                            )
                        })()}
                    </div>
                )}
            </CardHeader>
            <CardContent className="p-0">
                <div
                    ref={chartContainerRef}
                    className="relative w-full"
                    style={{ minHeight: "400px" }}
                >
                    {/* Placeholder or loading state could go here */}
                </div>
            </CardContent>
        </Card>
    )
}
