"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { X } from "lucide-react"
import { IconButton } from "@/components/ui/icon-button"
import { createChartTimeFormatters, type ChartTimeZone } from "@/lib/chart-time"
import type { Candle } from "@/lib/indicators"
import type { WorkerPaneSeriesResult } from "@/lib/types/indicator-worker"
import {
    chartColors,
    deduplicateByTime,
    findNearestSeriesPointByTime,
    formatTime,
    parseChartTimeToUnix,
    type ActiveIndicator,
} from "./chart-constants"

export interface IndicatorPaneProps {
    indicator: ActiveIndicator
    candles: Candle[]
    precomputedSeries: WorkerPaneSeriesResult | null
    onRemove: () => void
    mainChartRef: React.MutableRefObject<any>
    hoveredUnixTime: number | null
    timeZone: ChartTimeZone
    showTimeScale: boolean
    onChartReady?: (indicatorId: string, chart: any) => void
}

export function IndicatorPane({
    indicator,
    candles,
    precomputedSeries,
    onRemove,
    mainChartRef,
    hoveredUnixTime,
    timeZone,
    showTimeScale,
    onChartReady,
}: IndicatorPaneProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<any>(null)
    const timeFormatters = useMemo(() => createChartTimeFormatters(timeZone), [timeZone])
    const timeFormattersRef = useRef(timeFormatters)
    useEffect(() => {
        timeFormattersRef.current = timeFormatters
        chartRef.current?.applyOptions({
            localization: { locale: "tr-TR", timeFormatter: timeFormatters.timeFormatter },
            timeScale: { tickMarkFormatter: timeFormatters.tickMarkFormatter },
        })
    }, [timeFormatters])
    const primarySeriesRef = useRef<any>(null)
    const primarySeriesPointsRef = useRef<Array<{ timeKey: number; rawTime: string | number; value: number }>>([])
    const isSyncingRef = useRef(false)
    const isDisposedRef = useRef(false)
    const [paneHeight, setPaneHeight] = useState(120)
    const [hoveredValue, setHoveredValue] = useState<number | null>(null)
    const resizeStartYRef = useRef(0)
    const resizeStartHeightRef = useRef(120)
    const paneHeightRef = useRef(120)
    const lastHoverSyncUnixRef = useRef<number | null>(null)
    const lastHoverValueRef = useRef<number | null>(null)
    const hoverSyncRafRef = useRef<number | null>(null)

    const candleSignature = useMemo(() => {
        if (candles.length === 0) return "empty"
        const first = candles[0]?.time || ""
        const last = candles[candles.length - 1]?.time || ""
        return `${candles.length}:${first}:${last}`
    }, [candles])

    useEffect(() => {
        paneHeightRef.current = paneHeight
    }, [paneHeight])

    const startResize = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
        event.preventDefault()
        event.currentTarget.setPointerCapture?.(event.pointerId)

        const pointerId = event.pointerId
        resizeStartYRef.current = event.clientY
        resizeStartHeightRef.current = paneHeight

        const handlePointerMove = (moveEvent: PointerEvent) => {
            if (moveEvent.pointerId !== pointerId) return
            const delta = moveEvent.clientY - resizeStartYRef.current
            const nextHeight = Math.max(84, Math.min(360, resizeStartHeightRef.current - delta))
            setPaneHeight(nextHeight)
        }

        const handlePointerUp = (upEvent: PointerEvent) => {
            if (upEvent.pointerId !== pointerId) return
            window.removeEventListener("pointermove", handlePointerMove)
            window.removeEventListener("pointerup", handlePointerUp)
            window.removeEventListener("pointercancel", handlePointerUp)
        }

        window.addEventListener("pointermove", handlePointerMove)
        window.addEventListener("pointerup", handlePointerUp)
        window.addEventListener("pointercancel", handlePointerUp)
    }, [paneHeight])

    useEffect(() => {
        if (!containerRef.current || candles.length === 0) return

        isDisposedRef.current = false

        import("lightweight-charts").then(({ createChart, ColorType, LineSeries, HistogramSeries, CrosshairMode }) => {
            if (!containerRef.current || isDisposedRef.current) return

            if (chartRef.current) {
                try {
                    chartRef.current.remove()
                } catch {
                    // Chart already disposed
                }
                chartRef.current = null
            }

            const chart = createChart(containerRef.current, {
                layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: chartColors.text, fontSize: 10 },
                grid: { vertLines: { color: chartColors.grid }, horzLines: { color: chartColors.grid } },
                width: containerRef.current.clientWidth,
                height: paneHeightRef.current,
                rightPriceScale: {
                    borderColor: chartColors.grid,
                    minimumWidth: 64,
                    scaleMargins: { top: 0.22, bottom: showTimeScale ? 0.2 : 0.16 },
                },
                timeScale: {
                    visible: showTimeScale,
                    borderColor: chartColors.grid,
                    timeVisible: true,
                    secondsVisible: false,
                    rightOffset: 12,
                    barSpacing: 6,
                    minBarSpacing: 2,
                    tickMarkFormatter: timeFormattersRef.current.tickMarkFormatter,
                },
                localization: { locale: "tr-TR", timeFormatter: timeFormattersRef.current.timeFormatter },
                crosshair: {
                    mode: CrosshairMode.Normal,
                    vertLine: { color: chartColors.crosshair, width: 1, style: 0 },
                    horzLine: { color: chartColors.crosshair, width: 1, style: 0 },
                },
                handleScroll: {
                    mouseWheel: false,
                    pressedMouseMove: false,
                    horzTouchDrag: false,
                    vertTouchDrag: false,
                },
                handleScale: {
                    axisPressedMouseMove: false,
                    mouseWheel: false,
                    pinch: false,
                },
            })

            let series: any = null

            const setPrimarySeriesPoints = (line: Array<{ time: string | number; value: number }>) => {
                primarySeriesPointsRef.current = line
                    .map((point) => ({
                        rawTime: point.time,
                        timeKey: typeof point.time === "number" ? point.time : parseChartTimeToUnix(point.time),
                        value: point.value,
                    }))
                    .sort((a, b) => a.timeKey - b.timeKey)
            }

            const candleTimeline = deduplicateByTime(
                candles.map((item) => ({ time: formatTime(item.time) }))
            ).map((item) => item.time)

            const alignLineToTimeline = (line: Array<{ time: string | number; value: number }>) => {
                if (candleTimeline.length === 0) return line as Array<{ time: string | number } | { time: string | number; value: number }>
                const valueByTime = new Map<number, number>()
                for (const point of line) {
                    const timeKey = typeof point.time === "number" ? point.time : parseChartTimeToUnix(point.time)
                    valueByTime.set(timeKey, point.value)
                }
                return candleTimeline.map((time) => {
                    const timeKey = typeof time === "number" ? time : parseChartTimeToUnix(time)
                    const value = valueByTime.get(timeKey)
                    if (value === undefined) {
                        return { time }
                    }
                    return { time, value }
                })
            }

            const alignHistogramToTimeline = (histogram: Array<{ time: string | number; value: number; color: string }>) => {
                if (candleTimeline.length === 0) return histogram as Array<{ time: string | number } | { time: string | number; value: number; color: string }>
                const valueByTime = new Map<number, { value: number; color: string }>()
                for (const point of histogram) {
                    const timeKey = typeof point.time === "number" ? point.time : parseChartTimeToUnix(point.time)
                    valueByTime.set(timeKey, { value: point.value, color: point.color })
                }
                return candleTimeline.map((time) => {
                    const timeKey = typeof time === "number" ? time : parseChartTimeToUnix(time)
                    const value = valueByTime.get(timeKey)
                    if (!value) {
                        return { time }
                    }
                    return { time, value: value.value, color: value.color }
                })
            }

            if (indicator.id === "rsi") {
                series = chart.addSeries(LineSeries, { color: chartColors.indicators.rsi, lineWidth: 2, priceScaleId: "right" })
                let lineData: Array<{ time: string | number; value: number }> = []
                if (precomputedSeries?.kind === "line") {
                    lineData = deduplicateByTime(
                        precomputedSeries.line.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                }
                series.setData(alignLineToTimeline(lineData) as any)
                setPrimarySeriesPoints(lineData)
            } else if (indicator.id === "macd") {
                const macdSeries = chart.addSeries(LineSeries, { color: chartColors.indicators.macd, lineWidth: 2 })
                const signalSeries = chart.addSeries(LineSeries, { color: chartColors.indicators.macdSignal, lineWidth: 2 })
                const histSeries = chart.addSeries(HistogramSeries, { color: chartColors.indicators.macdHistogram })

                let macdLine: Array<{ time: string | number; value: number }> = []
                let signalLine: Array<{ time: string | number; value: number }> = []
                let histogram: Array<{ time: string | number; value: number; color: string }> = []

                if (precomputedSeries?.kind === "macd") {
                    macdLine = deduplicateByTime(
                        precomputedSeries.macd.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                    signalLine = deduplicateByTime(
                        precomputedSeries.signal.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                    histogram = deduplicateByTime(
                        precomputedSeries.histogram.map((point) => ({
                            time: formatTime(point.time),
                            value: point.value,
                            color: point.color,
                        }))
                    )
                }

                macdSeries.setData(alignLineToTimeline(macdLine) as any)
                signalSeries.setData(alignLineToTimeline(signalLine) as any)
                histSeries.setData(alignHistogramToTimeline(histogram) as any)
                series = macdSeries
                setPrimarySeriesPoints(macdLine)
            } else if (indicator.id === "wr") {
                series = chart.addSeries(LineSeries, { color: chartColors.indicators.wr, lineWidth: 2 })
                let lineData: Array<{ time: string | number; value: number }> = []
                if (precomputedSeries?.kind === "line") {
                    lineData = deduplicateByTime(
                        precomputedSeries.line.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                }
                series.setData(alignLineToTimeline(lineData) as any)
                setPrimarySeriesPoints(lineData)
            } else if (indicator.id === "cci") {
                series = chart.addSeries(LineSeries, { color: chartColors.indicators.cci, lineWidth: 2 })
                let lineData: Array<{ time: string | number; value: number }> = []
                if (precomputedSeries?.kind === "line") {
                    lineData = deduplicateByTime(
                        precomputedSeries.line.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                }
                series.setData(alignLineToTimeline(lineData) as any)
                setPrimarySeriesPoints(lineData)
            }

            chartRef.current = chart
            primarySeriesRef.current = series
            onChartReady?.(indicator.id, chart)

            const syncWithMain = () => {
                if (isDisposedRef.current || !mainChartRef.current || isSyncingRef.current) return
                try {
                    const mainTimeScale = mainChartRef.current.timeScale()
                    const logicalRange = mainTimeScale.getVisibleLogicalRange?.() || null
                    const visibleRange = mainTimeScale.getVisibleRange?.() || null
                    if ((visibleRange || logicalRange) && chartRef.current) {
                        isSyncingRef.current = true
                        const paneTimeScale = chartRef.current.timeScale()
                        if (logicalRange && typeof paneTimeScale.setVisibleLogicalRange === "function") {
                            paneTimeScale.setVisibleLogicalRange(logicalRange)
                        } else if (visibleRange && typeof paneTimeScale.setVisibleRange === "function") {
                            paneTimeScale.setVisibleRange(visibleRange)
                        }
                        isSyncingRef.current = false
                    }
                } catch {
                    // Chart disposed or not ready
                }
            }

            let mainTimeScale: any = null

            if (mainChartRef.current) {
                try {
                    mainTimeScale = mainChartRef.current.timeScale()
                    mainTimeScale.subscribeVisibleLogicalRangeChange(syncWithMain)
                    syncWithMain()
                } catch {
                    // Main chart not ready
                }
            }

            const handleResize = () => {
                if (containerRef.current && chartRef.current && !isDisposedRef.current) {
                    try {
                        chartRef.current.applyOptions({
                            width: containerRef.current.clientWidth,
                            height: paneHeightRef.current,
                        })
                    } catch {
                        // Chart disposed
                    }
                }
            }
            window.addEventListener("resize", handleResize)

            return () => {
                isDisposedRef.current = true
                window.removeEventListener("resize", handleResize)

                if (mainTimeScale) {
                    try { mainTimeScale.unsubscribeVisibleLogicalRangeChange(syncWithMain) } catch { /* ignore */ }
                }

                if (chartRef.current) {
                    try {
                        chartRef.current.remove()
                    } catch {
                        // Already disposed
                    }
                    chartRef.current = null
                }
                primarySeriesRef.current = null
                primarySeriesPointsRef.current = []
            }
        })
    }, [indicator, candleSignature, mainChartRef, onChartReady, candles, precomputedSeries, showTimeScale])

    useEffect(() => {
        if (!containerRef.current || !chartRef.current || isDisposedRef.current) return
        try {
            chartRef.current.applyOptions({
                width: containerRef.current.clientWidth,
                height: paneHeight,
                rightPriceScale: {
                    scaleMargins: { top: 0.22, bottom: showTimeScale ? 0.2 : 0.16 },
                },
                timeScale: {
                    visible: showTimeScale,
                },
            })
        } catch {
            // Chart disposed
        }
    }, [paneHeight, showTimeScale])

    useEffect(() => {
        if (!chartRef.current || !primarySeriesRef.current) return

        if (hoverSyncRafRef.current !== null) {
            window.cancelAnimationFrame(hoverSyncRafRef.current)
            hoverSyncRafRef.current = null
        }

        if (hoveredUnixTime === null) {
            lastHoverSyncUnixRef.current = null
            lastHoverValueRef.current = null
            setHoveredValue((prev) => (prev === null ? prev : null))
            if (typeof chartRef.current.clearCrosshairPosition === "function") {
                try { chartRef.current.clearCrosshairPosition() } catch { /* ignore */ }
            }
            return
        }

        if (lastHoverSyncUnixRef.current === hoveredUnixTime) {
            return
        }
        lastHoverSyncUnixRef.current = hoveredUnixTime

        hoverSyncRafRef.current = window.requestAnimationFrame(() => {
            const nearest = findNearestSeriesPointByTime(primarySeriesPointsRef.current, hoveredUnixTime)
            if (!nearest) return

            if (lastHoverValueRef.current !== nearest.value) {
                lastHoverValueRef.current = nearest.value
                setHoveredValue(nearest.value)
            }

            if (typeof chartRef.current.setCrosshairPosition === "function") {
                try {
                    chartRef.current.setCrosshairPosition(nearest.value, hoveredUnixTime as any, primarySeriesRef.current)
                } catch {
                    // Ignore crosshair sync errors
                }
            }
        })
    }, [hoveredUnixTime, indicator.id, candleSignature])

    useEffect(() => {
        return () => {
            if (hoverSyncRafRef.current !== null) {
                window.cancelAnimationFrame(hoverSyncRafRef.current)
                hoverSyncRafRef.current = null
            }
        }
    }, [])

    return (
        <div className="relative border-t border-border/30">
            <div
                onPointerDown={startResize}
                className="group relative z-20 h-3 w-full cursor-row-resize touch-none select-none border-y border-border/60 bg-border/50 hover:border-primary/70 hover:bg-primary/25"
                title="Panel yüksekliğini ayarlamak için sürükleyin"
            >
                <div className="pointer-events-none absolute left-1/2 top-1/2 h-1 w-16 -translate-x-1/2 -translate-y-1/2 rounded-full bg-muted-foreground/70 group-hover:bg-primary/90" />
            </div>
            <div className="flex items-center justify-between px-4 py-1 bg-muted/10">
                <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-muted-foreground">{indicator.meta.shortName}</span>
                    {hoveredValue !== null && (
                        <span className="text-xs font-semibold text-foreground/90 mono-numbers">
                            {hoveredValue.toFixed(2)}
                        </span>
                    )}
                </div>
                <IconButton onClick={onRemove} className="text-muted-foreground hover:text-loss" label={`${indicator.meta.shortName} panelini kaldır`}>
                    <X className="h-3 w-3" />
                </IconButton>
            </div>
            <div ref={containerRef} className="w-full overflow-hidden" style={{ height: `${paneHeight}px` }} />
        </div>
    )
}
