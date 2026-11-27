"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import dynamic from "next/dynamic"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import type { ISeriesApi, Time } from "lightweight-charts"
import {
    fetchBistSymbols,
    fetchCryptoSymbols,
    fetchEconomicCalendar,
    fetchTicker,
} from "@/lib/api/client"
import { useBinanceTickerFeed } from "@/lib/hooks/use-binance-ticker"
import { useChartCandles } from "@/lib/hooks/use-chart-candles"
import { useLastMarketQuote, useMarketSnapshot } from "@/lib/hooks/use-market-snapshot"
import { useSession } from "@/lib/hooks/use-session"
import { finiteNumber } from "@/lib/market-feed"
import { MarketDataStatus } from "@/components/market-data-status"
import { BORSAPY_INTERVALS, borsapyVolumeWarning, mergeBorsapyCandles } from "@/lib/api/borsapy-chart-api"
import { paintPriceBars, type PriceBar } from "@/lib/chart-price-series"
import { ServerWatchlistPanel } from "./server-watchlist-panel"
import { ChartDataError, hasDisplayableCandles } from "./chart-data-error"
import { chartTimeZone, createChartTimeFormatters } from "@/lib/chart-time"
import { cn } from "@/lib/utils"
import { ActionDialog } from "@/components/ui/action-dialog"
import { IconButton } from "@/components/ui/icon-button"
import { useToast } from "@/components/ui/toast"
import {
    AVAILABLE_INDICATORS,
    type Candle,
    type IndicatorParamSchema,
} from "@/lib/indicators"
import type {
    IndicatorWorkerComputeRequest,
    IndicatorWorkerComputeResponse,
    WorkerIndicatorDescriptor,
} from "@/lib/types/indicator-worker"
import {
    Search,
    TrendingUp,
    TrendingDown,
    Clock,
    BarChart3,
    Maximize2,
    Minimize2,
    ChevronDown,
    X,
    Zap,
    PanelRightOpen,
    PanelRightClose,
    LineChart,
    Pencil,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Trash2,
    Settings2,
    Eye,
    EyeOff,
    Bell,
    Share2,
    Copy,
    FolderOpen,
    Upload,
    ArrowUpRight,
} from "lucide-react"
import {
    ALARM_INDICATOR_OPTIONS,
    ALARM_TIMEFRAME_OPTIONS,
    type WatchlistAlarmRule,
} from "@/lib/watchlist-alarms"
import {
    subscribeAlarmRuleStorage,
    updateAlarmRuleStorage,
    type AlarmRuleChange,
} from "@/lib/alarm-rule-storage"
import {
    ACTIVE_WATCHLIST_STORAGE_KEY,
    BIST_ALLOWED_TIMEFRAMES,
    CRYPTO_WATCHLIST,
    DEFAULT_WATCHLISTS,
    DEV_PERF_ENABLED,
    DEV_PERF_THROTTLE_MS,
    INDICATOR_SETTINGS_STORAGE_KEY,
    QUICK_TIMEFRAMES,
    TIMEFRAME_CATEGORIES,
    WATCHLIST_PANEL_STORAGE_KEY,
    WATCHLIST_STORAGE_KEY,
    WATCHLIST_UTILITY_CALENDAR_REFRESH_MS,
    WATCHLIST_UTILITY_ITEMS,
    buildMarkerHash,
    buildUtilityCalendarItems,
    chartColors,
    formatTime,
    getDefaultActiveIndicators,
    getTimeframeStepSeconds,
    makeWatchlistId,
    normalizeHorzTimeToUnix,
    parseChartTimeToUnix,
    symbolRow,
    type ActiveIndicator,
    type MarketType,
    type PersistedActiveIndicator,
    type RightUtilityPanelId,
    type SignalMarker,
    type WatchlistDialogState,
    type WatchlistModel,
    type WatchlistRow,
    type WatchlistSymbolRow,
    type WorkerComputationState,
} from "./chart-constants"

const CustomIndicatorPanel = dynamic(
    () => import("@/components/indicators/custom-indicator-panel").then((mod) => mod.CustomIndicatorPanel),
    { ssr: false }
)

const ChartDrawingTools = dynamic(
    () => import("./chart-drawing-tools").then((mod) => mod.ChartDrawingTools),
    { ssr: false }
)

const IndicatorPane = dynamic(
    () => import("./indicator-pane").then((mod) => mod.IndicatorPane),
    { ssr: false }
)

const EMPTY_CANDLES: Candle[] = []
const EMPTY_WORKER_RESULT: WorkerComputationState = {
    requestId: 0, computeMs: 0, panes: {}, overlays: { combo: [], hunter: [] },
}
const INITIAL_BIST_CANDLES = 160

interface ChartPageProps {
    initialSymbol?: string
    initialMarket?: MarketType
    signals?: SignalMarker[]
    showSignals?: boolean
    showWatchlist?: boolean
}

export function AdvancedChartPage({
    initialSymbol = "THYAO",
    initialMarket = "BIST",
    signals = [],
    showSignals = true,
    showWatchlist = true,
}: ChartPageProps) {
    const { addToast } = useToast()
    // Basic state
    const [symbol, setSymbol] = useState(initialSymbol)
    const [marketType, setMarketType] = useState<MarketType>(initialMarket)
    const timeFormatters = useMemo(() => createChartTimeFormatters(chartTimeZone(marketType)), [marketType])
    const timeFormattersRef = useRef(timeFormatters)
    const [timeframe, setTimeframe] = useState("1d")
    const session = useSession()
    const useBorsapy = marketType === "BIST"
    const canUseBorsapy = Boolean(session?.user.is_admin && !session.user.disabled)
    const bistTimeframes = useBorsapy ? BORSAPY_INTERVALS : BIST_ALLOWED_TIMEFRAMES
    const [showSymbolSearch, setShowSymbolSearch] = useState(false)
    const [showTimeframeMenu, setShowTimeframeMenu] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [isFullscreen, setIsFullscreen] = useState(false)
    const isFullscreenRef = useRef(isFullscreen)
    const [showRightPanel, setShowRightPanel] = useState(showWatchlist)
    const [watchlists, setWatchlists] = useState<WatchlistModel[]>(() => DEFAULT_WATCHLISTS)
    const [activeWatchlistId, setActiveWatchlistId] = useState<string>(DEFAULT_WATCHLISTS[0]?.id || "")
    const [showWatchlistSwitcher, setShowWatchlistSwitcher] = useState(false)
    const [showWatchlistMenu, setShowWatchlistMenu] = useState(false)
    const [activeUtilityPanel, setActiveUtilityPanel] = useState<RightUtilityPanelId | null>("alerts")
    const [watchlistsHydrated, setWatchlistsHydrated] = useState(false)
    const [watchlistSource, setWatchlistSource] = useState<"server" | "local">("server")
    const [watchlistNotice, setWatchlistNotice] = useState<string | null>(null)
    const [watchlistDialog, setWatchlistDialog] = useState<WatchlistDialogState>(null)
    const [serverClockLabel, setServerClockLabel] = useState("--")
    const [watchlistAlarmRules, setWatchlistAlarmRules] = useState<WatchlistAlarmRule[]>([])
    // Indicator state
    const [showIndicatorSearch, setShowIndicatorSearch] = useState(false)
    const [indicatorSearchQuery, setIndicatorSearchQuery] = useState("")
    const [activeIndicators, setActiveIndicators] = useState<ActiveIndicator[]>(() => getDefaultActiveIndicators())
    const [editingIndicatorId, setEditingIndicatorId] = useState<string | null>(null)
    const [draftIndicatorParams, setDraftIndicatorParams] = useState<Record<string, number>>({})
    const [indicatorStateHydrated, setIndicatorStateHydrated] = useState(false)

    // Drawing interactions are independent of market-data acquisition.
    const [activeTool, setActiveTool] = useState<'none' | 'drawing'>('none')
    const [drawingPanelOpen, setDrawingPanelOpen] = useState(false)
    const [overlayRenderNonce, setOverlayRenderNonce] = useState(0)
    const [hoveredUnixTime, setHoveredUnixTime] = useState<number | null>(null)

    // Chart ready state
    const [chartReady, setChartReady] = useState(false)

    // Crosshair data
    const [crosshairData, setCrosshairData] = useState<{
        scope: string
        time: unknown
        open: number
        high: number
        low: number
        close: number
        volume: number | null
    } | null>(null)
    const [workerResult, setWorkerResult] = useState<(WorkerComputationState & { scope: string }) | null>(null)

    // Refs
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)
    const markersInstance = useRef<any>(null) // v5 markers primitive
    const lastCrosshairUnixRef = useRef<number | null>(null)
    const activeToolRef = useRef<'none' | 'drawing'>('none')
    const lastMarkersHashRef = useRef<string>("")
    const plottedPriceRef = useRef<{
        series: ISeriesApi<"Candlestick">; scope: string; bars: PriceBar[]; volumes: Map<number, number | null>
    } | null>(null)
    const fullscreenContainerRef = useRef<HTMLDivElement>(null)
    const lastRouteSelectionRef = useRef<{ symbol: string; market: MarketType }>({
        symbol: initialSymbol.trim().toUpperCase(),
        market: initialMarket,
    })
    const indicatorChartsRef = useRef<Map<string, any>>(new Map())
    const overlaySyncRafRef = useRef<number | null>(null)
    const hasProjectedDrawingsRef = useRef(false)
    const indicatorWorkerRef = useRef<Worker | null>(null)
    const latestWorkerRequestIdRef = useRef(0)
    const latestWorkerScopeRef = useRef("")
    const pendingWorkerDispatchTimerRef = useRef<number | null>(null)
    const perfLogRef = useRef<Record<string, number>>({})

    const syncIndicatorPanesToMainRange = useCallback(() => {
        if (!chartInstance.current) return
        const mainTimeScale = chartInstance.current.timeScale?.()
        if (!mainTimeScale) return
        const logicalRange = mainTimeScale.getVisibleLogicalRange?.() || null
        const visibleRange = mainTimeScale.getVisibleRange?.() || null
        if (!logicalRange && !visibleRange) return

        indicatorChartsRef.current.forEach((paneChart) => {
            try {
                const paneTimeScale = paneChart.timeScale?.()
                if (!paneTimeScale) return
                if (logicalRange && typeof paneTimeScale.setVisibleLogicalRange === "function") {
                    paneTimeScale.setVisibleLogicalRange(logicalRange)
                    return
                }
                if (visibleRange && typeof paneTimeScale.setVisibleRange === "function") {
                    paneTimeScale.setVisibleRange(visibleRange)
                }
            } catch {
                // Ignore stale indicator chart handles.
            }
        })
    }, [])

    // Register indicator chart for crosshair + time-range sync
    const registerIndicatorChart = useCallback((id: string, chart: any) => {
        indicatorChartsRef.current.set(id, chart)
        syncIndicatorPanesToMainRange()
    }, [syncIndicatorPanesToMainRange])

    const showWatchlistToast = useCallback((message: string) => {
        setWatchlistNotice(message)
    }, [])

    const logPerf = useCallback((key: string, payload: Record<string, unknown>) => {
        if (!DEV_PERF_ENABLED) return
        const now = performance.now()
        const last = perfLogRef.current[key] || 0
        if (now - last < DEV_PERF_THROTTLE_MS) return
        perfLogRef.current[key] = now
        console.debug(`[chart-perf] ${key}`, payload)
    }, [])

    const requestOverlayProjectionRefresh = useCallback(() => {
        if (overlaySyncRafRef.current !== null) {
            return
        }
        overlaySyncRafRef.current = window.requestAnimationFrame(() => {
            overlaySyncRafRef.current = null
            setOverlayRenderNonce((value) => value + 1)
        })
    }, [])

    // Keep chart state in sync when route query changes on the same /chart page.
    useEffect(() => {
        const nextSymbol = initialSymbol?.trim().toUpperCase()
        if (!nextSymbol) return

        const previousRouteSelection = lastRouteSelectionRef.current
        if (
            previousRouteSelection.symbol === nextSymbol &&
            previousRouteSelection.market === initialMarket
        ) {
            return
        }

        lastRouteSelectionRef.current = { symbol: nextSymbol, market: initialMarket }
        setSymbol(nextSymbol)
        setMarketType(initialMarket)
        setShowSymbolSearch(false)
        setSearchQuery("")
    }, [initialSymbol, initialMarket])

    const availableTimeframeCategories = useMemo(() => {
        if (marketType !== "BIST") return TIMEFRAME_CATEGORIES
        return TIMEFRAME_CATEGORIES
            .map((category) => ({
                ...category,
                items: category.items.filter((item) => bistTimeframes.has(item.value)),
            }))
            .filter((category) => category.items.length > 0)
    }, [marketType, bistTimeframes])

    const availableQuickTimeframes = useMemo(() => {
        if (marketType !== "BIST") return QUICK_TIMEFRAMES
        return QUICK_TIMEFRAMES.filter((item) => bistTimeframes.has(item.value))
    }, [marketType, bistTimeframes])

    useEffect(() => {
        if (marketType !== "BIST") return
        if (bistTimeframes.has(timeframe)) return
        setTimeframe("1d")
    }, [marketType, timeframe, bistTimeframes])

    useEffect(() => {
        activeToolRef.current = activeTool
    }, [activeTool])

    const onDrawingMode = useCallback((active: boolean) => setActiveTool(active ? "drawing" : "none"), [])
    const onDrawingCountChange = useCallback((count: number) => { hasProjectedDrawingsRef.current = count > 0 }, [])

    useEffect(() => {
        const updateClock = () => setServerClockLabel(new Date().toLocaleString("tr-TR"))
        updateClock()
        const timer = window.setInterval(updateClock, 1000)
        return () => window.clearInterval(timer)
    }, [])

    useEffect(() => () => {
        if (overlaySyncRafRef.current !== null) window.cancelAnimationFrame(overlaySyncRafRef.current)
    }, [])

    useEffect(() => {
        if (!watchlistNotice) return
        const timer = setTimeout(() => setWatchlistNotice(null), 2800)
        return () => clearTimeout(timer)
    }, [watchlistNotice])

    useEffect(() => {
        if (typeof window === "undefined") {
            setWatchlistsHydrated(true)
            return
        }

        try {
            const rawWatchlists = window.localStorage.getItem(WATCHLIST_STORAGE_KEY)
            if (rawWatchlists) {
                const parsed = JSON.parse(rawWatchlists) as unknown
                if (Array.isArray(parsed)) {
                    const restored = parsed
                        .map((candidate): WatchlistModel | null => {
                            if (!candidate || typeof candidate !== "object") return null
                            const item = candidate as Partial<WatchlistModel>
                            if (typeof item.id !== "string" || typeof item.name !== "string") return null
                            const rows = Array.isArray(item.rows)
                                ? item.rows
                                      .map((row): WatchlistRow | null => {
                                          if (!row || typeof row !== "object") return null
                                          const maybeRow = row as Partial<WatchlistRow>
                                          if (maybeRow.kind === "section" && typeof (maybeRow as any).title === "string") {
                                              return {
                                                  kind: "section",
                                                  id: typeof (maybeRow as any).id === "string" ? (maybeRow as any).id : makeWatchlistId((maybeRow as any).title),
                                                  title: (maybeRow as any).title,
                                              }
                                          }
                                          if (
                                              maybeRow.kind === "symbol" &&
                                              typeof (maybeRow as any).rawSymbol === "string" &&
                                              ((maybeRow as any).marketType === "BIST" || (maybeRow as any).marketType === "Kripto")
                                          ) {
                                              return {
                                                  kind: "symbol",
                                                  rawSymbol: (maybeRow as any).rawSymbol.toUpperCase(),
                                                  marketType: (maybeRow as any).marketType,
                                              }
                                          }
                                          return null
                                      })
                                      .filter((row): row is WatchlistRow => row !== null)
                                : []

                            return {
                                id: item.id,
                                name: item.name,
                                alarmsEnabled: item.alarmsEnabled === true,
                                notes: typeof item.notes === "string" ? item.notes : "",
                                rows,
                            }
                        })
                        .filter((item): item is WatchlistModel => item !== null)
                    if (restored.length > 0) {
                        setWatchlists(restored)
                    }
                }
            }

            const storedActiveId = window.localStorage.getItem(ACTIVE_WATCHLIST_STORAGE_KEY)
            if (storedActiveId) {
                setActiveWatchlistId(storedActiveId)
            }

            const storedPanel = window.localStorage.getItem(WATCHLIST_PANEL_STORAGE_KEY)
            if (
                storedPanel === "alerts" ||
                storedPanel === "notes" ||
                storedPanel === "calendar" ||
                storedPanel === "layout" ||
                storedPanel === "help"
            ) {
                setActiveUtilityPanel(storedPanel)
            }

        } catch (error) {
            console.error("Watchlist state could not be restored:", error)
        } finally {
            setWatchlistsHydrated(true)
        }
    }, [])

    useEffect(() => {
        if (!watchlistsHydrated || typeof window === "undefined") return
        window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlists))
        window.localStorage.setItem(ACTIVE_WATCHLIST_STORAGE_KEY, activeWatchlistId)
        if (activeUtilityPanel) {
            window.localStorage.setItem(WATCHLIST_PANEL_STORAGE_KEY, activeUtilityPanel)
        } else {
            window.localStorage.removeItem(WATCHLIST_PANEL_STORAGE_KEY)
        }
    }, [watchlists, activeWatchlistId, activeUtilityPanel, watchlistsHydrated])

    useEffect(() => {
        return subscribeAlarmRuleStorage((result) => {
            if (result.ok) setWatchlistAlarmRules(result.rules)
            else setWatchlistNotice("Alarm kuralları tarayıcıdan okunamadı. Kaydedilmiş veriler değiştirilmedi.")
        })
    }, [])

    useEffect(() => {
        if (watchlists.length === 0) return
        if (!watchlists.some((watchlist) => watchlist.id === activeWatchlistId)) {
            setActiveWatchlistId(watchlists[0].id)
        }
    }, [watchlists, activeWatchlistId])

    useEffect(() => {
        if (typeof window === "undefined") {
            setIndicatorStateHydrated(true)
            return
        }

        try {
            const rawState = window.localStorage.getItem(INDICATOR_SETTINGS_STORAGE_KEY)
            if (!rawState) {
                return
            }

            const parsedState = JSON.parse(rawState) as unknown
            if (!Array.isArray(parsedState)) {
                return
            }

            const restoredIndicators: ActiveIndicator[] = parsedState
                .map((entry): ActiveIndicator | null => {
                    if (!entry || typeof entry !== "object") {
                        return null
                    }

                    const candidate = entry as Partial<PersistedActiveIndicator>
                    if (typeof candidate.id !== "string") {
                        return null
                    }

                    const meta = AVAILABLE_INDICATORS.find((indicator) => indicator.id === candidate.id)
                    if (!meta) {
                        return null
                    }

                    const params: Record<string, number> = { ...meta.defaultParams }
                    if (candidate.params && typeof candidate.params === "object") {
                        for (const [key, value] of Object.entries(candidate.params as Record<string, unknown>)) {
                            if (typeof value === "number" && Number.isFinite(value)) {
                                params[key] = value
                            }
                        }
                    }

                    return {
                        id: candidate.id,
                        meta,
                        params,
                        visible: candidate.visible !== false,
                    }
                })
                .filter((indicator): indicator is ActiveIndicator => indicator !== null)

            if (restoredIndicators.length > 0 || parsedState.length === 0) {
                setActiveIndicators(restoredIndicators)
            }
        } catch (error) {
            console.error("Indicator settings could not be restored:", error)
        } finally {
            setIndicatorStateHydrated(true)
        }
    }, [])

    useEffect(() => {
        if (!indicatorStateHydrated || typeof window === "undefined") {
            return
        }

        try {
            const stateToPersist: PersistedActiveIndicator[] = activeIndicators.map((indicator) => ({
                id: indicator.id,
                params: indicator.params,
                visible: indicator.visible,
            }))
            window.localStorage.setItem(INDICATOR_SETTINGS_STORAGE_KEY, JSON.stringify(stateToPersist))
        } catch (error) {
            console.error("Indicator settings could not be saved:", error)
        }
    }, [activeIndicators, indicatorStateHydrated])

    const { history, stream: chartStream, streamEnabled, historySupported, scope: chartScope } =
        useChartCandles(symbol, marketType, timeframe, canUseBorsapy, session?.user.username, session?.expiresAt)
    const {
        data: candlesResponse,
        isError: isCandlesError,
        error: candlesError,
        isFetching: isCandlesFetching,
        refetch: refetchCandles,
    } = history
    const isCandlesLoading = historySupported && history.isPending

    const candlesErrorMessage =
        candlesError instanceof Error ? candlesError.message : "Grafik verisi alinamadi."

    // Fetch BIST symbols for search
    const { data: bistSymbols } = useQuery({
        queryKey: ['bist-symbols'],
        queryFn: ({ signal }) => fetchBistSymbols(signal),
        staleTime: 300000,
        enabled: canUseBorsapy,
    })

    // Fetch all Binance USDT pairs
    const { data: binanceSymbols } = useQuery({
        queryKey: ['binance-symbols'],
        queryFn: async () => (await fetchCryptoSymbols()).symbols,
        staleTime: 3600000,
        enabled: canUseBorsapy,
    })

    // Fetch BIST tickers for watchlist
    const { data: bistTickers, refetch: refetchTickers } = useQuery({
        queryKey: ['watchlist-ticker', session?.user.username, session?.expiresAt],
        queryFn: fetchTicker,
        refetchInterval: 30000,
        enabled: canUseBorsapy && showRightPanel && watchlistSource === "local",
    })

    const activeWatchlistBistSymbolsForQuery = useMemo(() => {
        const activeWatchlistForQuery =
            watchlists.find((watchlist) => watchlist.id === activeWatchlistId) || watchlists[0] || null
        if (!activeWatchlistForQuery) return [] as string[]

        const set = new Set<string>()
        for (const row of activeWatchlistForQuery.rows) {
            if (row.kind === "symbol" && row.marketType === "BIST") {
                set.add(`${row.rawSymbol.toUpperCase()}.IS`)
            }
        }
        return Array.from(set).slice(0, 50)
    }, [watchlists, activeWatchlistId])

    const { data: activeWatchlistBistQuotes, refetch: refetchActiveWatchlistBistQuotes } =
        useMarketSnapshot(canUseBorsapy && showRightPanel && watchlistSource === "local" ? activeWatchlistBistSymbolsForQuery : [])

    const utilityCalendarRange = useMemo(() => {
        const now = new Date()
        const from = now.toISOString().slice(0, 10)
        const toDate = new Date(now)
        toDate.setDate(toDate.getDate() + 7)
        const to = toDate.toISOString().slice(0, 10)
        return { from, to }
    }, [])

    const {
        data: utilityCalendarResponse,
        isFetching: isUtilityCalendarFetching,
        dataUpdatedAt: utilityCalendarUpdatedAt,
        refetch: refetchUtilityCalendar,
    } = useQuery({
        queryKey: ['chart-watchlist-calendar', session?.user.username, session?.expiresAt, utilityCalendarRange.from, utilityCalendarRange.to],
        queryFn: ({ signal }) =>
            fetchEconomicCalendar({
                from_date: utilityCalendarRange.from,
                to_date: utilityCalendarRange.to,
            }, { signal }),
        refetchInterval: WATCHLIST_UTILITY_CALENDAR_REFRESH_MS,
        staleTime: 30_000,
        enabled: canUseBorsapy,
    })

    const watchlistCryptoSymbols = useMemo(() => {
        const symbols = new Set<string>()
        for (const list of showRightPanel && watchlistSource === "local" ? watchlists.filter(item => item.id === activeWatchlistId) : []) {
            for (const row of list.rows) {
                if (row.kind === "symbol" && row.marketType === "Kripto") {
                    symbols.add(row.rawSymbol.toUpperCase())
                }
            }
        }
        if (marketType === "Kripto") {
            symbols.add(symbol.toUpperCase())
        }
        return Array.from(symbols)
    }, [watchlists, activeWatchlistId, showRightPanel, watchlistSource, marketType, symbol])

    // Live crypto prices for watchlist
    const cryptoFeed = useBinanceTickerFeed(watchlistCryptoSymbols, {
        paused: !canUseBorsapy,
        flushIntervalMs: 320,
    })
    const cryptoPrices = cryptoFeed.prices

    const hasFullHistory = useMemo(() => hasDisplayableCandles(candlesResponse?.candles ?? EMPTY_CANDLES), [candlesResponse?.candles])
    const candles: Candle[] = useMemo(() => {
        if (!historySupported) return EMPTY_CANDLES
        const historyCandles = hasFullHistory ? candlesResponse?.candles ?? EMPTY_CANDLES : EMPTY_CANDLES
        const merged = streamEnabled
            ? mergeBorsapyCandles(historyCandles, chartStream.data?.candles ?? [])
            : historyCandles
        const rawCandles = streamEnabled && !hasFullHistory ? merged.slice(-INITIAL_BIST_CANDLES) : merged
        if (rawCandles.length === 0) return EMPTY_CANDLES

        const deduped = new Map<number, Candle>()
        for (const candle of rawCandles) {
            const unix = parseChartTimeToUnix(candle.time)
            deduped.set(unix, candle)
        }

        return Array.from(deduped.entries())
            .sort((a, b) => a[0] - b[0])
            .map((entry) => entry[1])
    }, [historySupported, hasFullHistory, candlesResponse?.candles, streamEnabled, chartStream.data?.candles])
    // Query keys include symbol, market, timeframe and session; only this selection's
    // merged history/stream may keep a failed refresh from covering the chart.
    const hasChartCandles = useMemo(() => hasDisplayableCandles(candles), [candles])
    const previewOnly = hasChartCandles && !hasFullHistory
    const calculationCandles = hasFullHistory ? candles : EMPTY_CANDLES
    const workerComputationState = hasFullHistory && workerResult?.scope === chartScope
        ? workerResult : EMPTY_WORKER_RESULT
    const volumeWarning = useBorsapy && hasChartCandles
        ? borsapyVolumeWarning(candlesResponse?.volume_quality, chartStream.data?.volume_quality) : null
    const dataSource = previewOnly ? chartStream.data?.source || "TradingView / Borsapy" : candlesResponse?.source || "loading"

    const signalsSignature = useMemo(() => {
        if (!showSignals || signals.length === 0) return "signals-off"
        const first = signals[0]
        const last = signals[signals.length - 1]
        return `${signals.length}:${first.time}:${first.type}:${last.time}:${last.type}`
    }, [signals, showSignals])

    const markerIndicatorSignature = useMemo(() => {
        const tracked = activeIndicators
            .filter((indicator) => indicator.id === "combo" || indicator.id === "hunter")
            .map((indicator) => {
                const params = Object.entries(indicator.params)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, value]) => `${key}=${value}`)
                    .join(",")
                return `${indicator.id}:${indicator.visible ? "1" : "0"}:${params}`
            })
            .sort()
        return tracked.join("|")
    }, [activeIndicators])

    const workerIndicators = useMemo<WorkerIndicatorDescriptor[]>(() => (
        activeIndicators
            .map((indicator) => ({
                id: indicator.id,
                params: indicator.params,
                visible: indicator.visible,
                isOverlay: indicator.meta.isOverlay,
            }))
            .sort((a, b) => a.id.localeCompare(b.id))
    ), [activeIndicators])

    const workerIndicatorSignature = useMemo(
        () => workerIndicators
            .map((indicator) => {
                const params = Object.entries(indicator.params)
                    .sort(([a], [b]) => a.localeCompare(b))
                    .map(([key, value]) => `${key}=${value}`)
                    .join(",")
                return `${indicator.id}:${indicator.visible ? "1" : "0"}:${indicator.isOverlay ? "overlay" : "pane"}:${params}`
            })
            .join("|"),
        [workerIndicators]
    )

    const workerOverlaySignature = useMemo(() => {
        const combo = workerComputationState.overlays.combo
        const hunter = workerComputationState.overlays.hunter
        const comboFirst = combo[0]
        const comboLast = combo[combo.length - 1]
        const hunterFirst = hunter[0]
        const hunterLast = hunter[hunter.length - 1]
        return [
            `combo:${combo.length}:${comboFirst?.time || ""}:${comboFirst?.signal || ""}:${comboLast?.time || ""}:${comboLast?.signal || ""}`,
            `hunter:${hunter.length}:${hunterFirst?.time || ""}:${hunterFirst?.signal || ""}:${hunterLast?.time || ""}:${hunterLast?.signal || ""}`,
        ].join("|")
    }, [workerComputationState.overlays.combo, workerComputationState.overlays.hunter])

    useEffect(() => {
        if (typeof window === "undefined") return
        let worker: Worker | null = null
        try {
            worker = new Worker(new URL("../../workers/indicator-worker.ts", import.meta.url), { type: "module" })
            indicatorWorkerRef.current = worker
        } catch (error) {
            console.error("Indicator worker could not be started:", error)
            indicatorWorkerRef.current = null
            return
        }

        worker.onmessage = (event: MessageEvent<IndicatorWorkerComputeResponse>) => {
            const message = event.data
            if (!message || message.type !== "compute-indicators-result") {
                return
            }
            if (message.requestId !== latestWorkerRequestIdRef.current) {
                return
            }
            setWorkerResult({
                scope: latestWorkerScopeRef.current,
                requestId: message.requestId,
                computeMs: message.computeMs,
                panes: message.panes,
                overlays: message.overlays,
            })
            logPerf("indicator-worker", {
                requestId: message.requestId,
                computeMs: Number(message.computeMs.toFixed(2)),
                paneCount: Object.keys(message.panes).length,
                comboSignals: message.overlays.combo.length,
                hunterSignals: message.overlays.hunter.length,
            })
        }

        worker.onerror = (error) => {
            console.error("Indicator worker error:", error)
        }

        return () => {
            if (pendingWorkerDispatchTimerRef.current !== null) {
                window.clearTimeout(pendingWorkerDispatchTimerRef.current)
                pendingWorkerDispatchTimerRef.current = null
            }
            worker?.terminate()
            indicatorWorkerRef.current = null
        }
    }, [logPerf])

    useEffect(() => {
        if (!indicatorWorkerRef.current) return

        if (pendingWorkerDispatchTimerRef.current !== null) {
            window.clearTimeout(pendingWorkerDispatchTimerRef.current)
            pendingWorkerDispatchTimerRef.current = null
        }

        const requestId = ++latestWorkerRequestIdRef.current
        latestWorkerScopeRef.current = chartScope
        if (!calculationCandles.length) return
        pendingWorkerDispatchTimerRef.current = window.setTimeout(() => {
            const worker = indicatorWorkerRef.current
            if (!worker) return

            const message: IndicatorWorkerComputeRequest = {
                type: "compute-indicators",
                requestId,
                candles: calculationCandles,
                indicators: workerIndicators,
            }
            worker.postMessage(message)
        }, 60)

        return () => {
            if (pendingWorkerDispatchTimerRef.current !== null) {
                window.clearTimeout(pendingWorkerDispatchTimerRef.current)
                pendingWorkerDispatchTimerRef.current = null
            }
        }
    }, [calculationCandles, chartScope, workerIndicators, workerIndicatorSignature])

    // Calculate price info
    const candleClose = candles.at(-1)?.close
    const candlePrice = finiteNumber(candleClose) ? candleClose : undefined
    const prevPrice = candles.at(-2)?.close
    const lastBistPrice = useLastMarketQuote(useBorsapy && canUseBorsapy && candlePrice == null ? `${symbol.toUpperCase()}.IS` : "")
    const lastBistPriceTime = timeFormatters.timeFormatter(lastBistPrice?.provider_time)
    const cryptoSymbol = symbol.toUpperCase()
    const cryptoPrice = marketType === "Kripto" ? cryptoPrices[cryptoSymbol]?.price : undefined
    const cryptoTime = cryptoFeed.sourceTimeBySymbol[cryptoSymbol]
    const cryptoPriceTime = cryptoTime ? timeFormatters.timeFormatter(cryptoTime / 1000) : ""
    const cryptoReceivedAt = cryptoFeed.receivedAtBySymbol[cryptoSymbol]
    const cryptoReceivedTime = cryptoReceivedAt ? timeFormatters.timeFormatter(cryptoReceivedAt / 1000) : ""
    const livePrice = cryptoPrice ?? candlePrice ?? lastBistPrice?.value
    const priceChange = finiteNumber(candlePrice) && finiteNumber(prevPrice) && prevPrice > 0
        ? candlePrice - prevPrice : undefined
    const priceChangePercent = priceChange != null && prevPrice
        ? (priceChange / prevPrice) * 100 : lastBistPrice?.change
    const isPositive = (priceChangePercent ?? 0) >= 0

    // OHLCV display data
    const currentCrosshair = crosshairData?.scope === chartScope ? crosshairData : null
    const displayOHLCV = currentCrosshair ?? candles.at(-1)

    const visibleOverlayIndicators = useMemo(
        () => activeIndicators.filter(ind => ind.meta.isOverlay && ind.visible),
        [activeIndicators]
    )

    const visiblePanelIndicators = useMemo(
        () => activeIndicators.filter(ind => !ind.meta.isOverlay && ind.visible),
        [activeIndicators]
    )

    const showMainTimeScale = !hasFullHistory || visiblePanelIndicators.length === 0
    const showMainTimeScaleRef = useRef(showMainTimeScale)

    // Adding a pane only moves the time axis; keep the populated main series and zoom.
    useEffect(() => {
        showMainTimeScaleRef.current = showMainTimeScale
        chartInstance.current?.applyOptions({
            timeScale: { visible: showMainTimeScale },
            rightPriceScale: { scaleMargins: { top: 0.05, bottom: showMainTimeScale ? 0.05 : 0.2 } },
        })
    }, [showMainTimeScale])

    // Handle fullscreen toggle
    const toggleFullscreen = useCallback(() => {
        if (!document.fullscreenElement) {
            fullscreenContainerRef.current?.requestFullscreen?.()
            setIsFullscreen(true)
        } else {
            document.exitFullscreen?.()
            setIsFullscreen(false)
        }
    }, [])

    // Listen for fullscreen change
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement)
        }
        document.addEventListener('fullscreenchange', handleFullscreenChange)
        return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
    }, [])

    useEffect(() => {
        timeFormattersRef.current = timeFormatters
        chartInstance.current?.applyOptions({
            localization: { locale: "tr-TR", timeFormatter: timeFormatters.timeFormatter },
            timeScale: { tickMarkFormatter: timeFormatters.tickMarkFormatter },
        })
    }, [timeFormatters])

    useEffect(() => {
        isFullscreenRef.current = isFullscreen
        if (chartContainerRef.current) chartInstance.current?.applyOptions({
            width: chartContainerRef.current.clientWidth,
            height: isFullscreen ? window.innerHeight - 120 : 500,
        })
    }, [isFullscreen])

    // Create/update chart
    useEffect(() => {
        const container = chartContainerRef.current
        if (!container) return
        let disposed = false
        let cleanup: (() => void) | undefined

        import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode, CandlestickSeries }) => {
            if (disposed) return
            const chart = createChart(container, {
                layout: {
                    background: { type: ColorType.Solid, color: chartColors.background },
                    textColor: chartColors.text,
                    fontSize: 12,
                },
                grid: {
                    vertLines: { color: chartColors.grid },
                    horzLines: { color: chartColors.grid },
                },
                width: container.clientWidth,
                height: isFullscreenRef.current ? window.innerHeight - 120 : 500,
                rightPriceScale: {
                    borderColor: chartColors.grid,
                    // Keep main price labels away from the indicator pane border.
                    scaleMargins: { top: 0.05, bottom: showMainTimeScaleRef.current ? 0.05 : 0.2 },
                    minimumWidth: 64,
                },
                timeScale: {
                    visible: showMainTimeScaleRef.current,
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
                    vertLine: {
                        color: chartColors.crosshair,
                        width: 1,
                        style: 0,
                        labelBackgroundColor: chartColors.crosshairLabel,
                    },
                    horzLine: {
                        color: chartColors.crosshair,
                        width: 1,
                        style: 0,
                        labelBackgroundColor: chartColors.crosshairLabel,
                    },
                },
                handleScroll: {
                    mouseWheel: true,
                    pressedMouseMove: true,
                    horzTouchDrag: true,
                    vertTouchDrag: true,
                },
                handleScale: {
                    axisPressedMouseMove: true,
                    mouseWheel: true,
                    pinch: true,
                },
                kineticScroll: {
                    mouse: true,
                    touch: true,
                },
            })

            // Candlestick series
            const candlestickSeries = chart.addSeries(CandlestickSeries, {
                upColor: chartColors.bullish,
                downColor: chartColors.bearish,
                borderDownColor: chartColors.bearish,
                borderUpColor: chartColors.bullish,
                wickDownColor: chartColors.bearish,
                wickUpColor: chartColors.bullish,
            })

            // Crosshair move handler
            chart.subscribeCrosshairMove((param) => {
                // While drawing tools are active, skip crosshair state churn.
                if (activeToolRef.current !== "none") {
                    return
                }

                const hoverUnix = param.time ? normalizeHorzTimeToUnix(param.time) : null

                if (hoverUnix === null || !param.seriesData.size) {
                    if (lastCrosshairUnixRef.current !== null) {
                        lastCrosshairUnixRef.current = null
                        setCrosshairData(null)
                    }
                    setHoveredUnixTime((prev) => (prev === null ? prev : null))
                    return
                }

                if (hoverUnix === lastCrosshairUnixRef.current) {
                    return
                }
                lastCrosshairUnixRef.current = hoverUnix
                setHoveredUnixTime((prev) => (prev === hoverUnix ? prev : hoverUnix))

                const candleData = param.seriesData.get(candlestickSeries)
                const plotted = plottedPriceRef.current
                if (plotted && candleData && 'open' in candleData) {
                    setCrosshairData({
                        scope: plotted.scope,
                        time: param.time,
                        open: candleData.open,
                        high: candleData.high,
                        low: candleData.low,
                        close: candleData.close,
                        volume: plotted.volumes.get(hoverUnix) ?? null,
                    })
                } else {
                    setCrosshairData(null)
                }
            })

            chartInstance.current = chart
            seriesInstance.current = candlestickSeries
            setChartReady(true)

            const handleVisibleRangeChange = () => {
                // Skip expensive React re-renders while there are no custom drawings to project.
                if (!hasProjectedDrawingsRef.current) {
                    syncIndicatorPanesToMainRange()
                    return
                }
                syncIndicatorPanesToMainRange()
                requestOverlayProjectionRefresh()
            }
            chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleRangeChange)

            // Handle resize
            const handleResize = () => {
                chart.applyOptions({
                    width: container.clientWidth,
                    height: isFullscreenRef.current ? window.innerHeight - 120 : 500,
                })
            }
            window.addEventListener("resize", handleResize)

            cleanup = () => {
                chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange)
                window.removeEventListener("resize", handleResize)
                // Clean up markers primitive
                if (markersInstance.current) {
                    try {
                        markersInstance.current.detach()
                    } catch {
                        // Ignore
                    }
                    markersInstance.current = null
                }
                chart.remove()
                chartInstance.current = null
                seriesInstance.current = null
                plottedPriceRef.current = null
            }
        })
        return () => {
            disposed = true
            cleanup?.()
        }
    }, [requestOverlayProjectionRefresh, syncIndicatorPanesToMainRange])

    // Paint prices independently of marker and indicator preparation.
    useEffect(() => {
        const series = seriesInstance.current as ISeriesApi<"Candlestick"> | null
        const chart = chartInstance.current
        if (!chartReady || !series || !chart) return
        const updateStart = performance.now()
        const previous = plottedPriceRef.current
        const sameSelection = previous?.series === series && previous.scope === chartScope
        if (!sameSelection) {
            markersInstance.current?.detach()
            markersInstance.current = null
            lastMarkersHashRef.current = ""
            lastCrosshairUnixRef.current = null
        }
        const bars = candles.map(({ time, open, high, low, close }) => ({
            time: formatTime(time) as Time, open, high, low, close,
        }))
        paintPriceBars(series, chart.timeScale(), previous?.bars ?? [], bars, sameSelection)
        plottedPriceRef.current = { series, scope: chartScope, bars,
            volumes: new Map(candles.map(candle => [parseChartTimeToUnix(candle.time), candle.volume])) }
        syncIndicatorPanesToMainRange()
        requestOverlayProjectionRefresh()
        logPerf("main-chart-update", {
            ms: Number((performance.now() - updateStart).toFixed(2)),
            candles: bars.length,
        })
    }, [chartReady, chartScope, candles, logPerf, requestOverlayProjectionRefresh, syncIndicatorPanesToMainRange])

    useEffect(() => {
        const series = seriesInstance.current
        if (!chartReady || !candles.length || !series) return
        let cancelled = false

        // Dynamic import for v5 markers API
        import("lightweight-charts").then(({ createSeriesMarkers }) => {
            if (cancelled || seriesInstance.current !== series || plottedPriceRef.current?.scope !== chartScope) return

            try {
                // Add signal markers (including Combo/Hunter overlays)
                const shouldSkipHeavyMarkerOps = activeToolRef.current !== "none"
                if (!shouldSkipHeavyMarkerOps) {
                    const markers: Array<{
                        time: string | number
                        position: "belowBar" | "aboveBar"
                        shape: "arrowUp" | "arrowDown"
                        color: string
                        text: string
                        size: number
                    }> = []

                    // Original signals
                    if (showSignals && signals.length > 0) {
                        signals.forEach((signal) => {
                            markers.push({
                                time: formatTime(signal.time),
                                position: signal.type === 'AL' ? 'belowBar' : 'aboveBar',
                                shape: signal.type === 'AL' ? 'arrowUp' : 'arrowDown',
                                color: signal.type === 'AL' ? chartColors.bullish : chartColors.bearish,
                                text: signal.type,
                                size: 2,
                            })
                        })
                    }

                    // Combo overlay markers
                    const comboIndicator = activeIndicators.find(i => i.id === 'combo' && i.visible)
                    if (comboIndicator) {
                        const comboSignals = workerComputationState.overlays.combo
                        comboSignals.forEach((sig) => {
                            markers.push({
                                time: formatTime(sig.time),
                                position: sig.signal === 'AL' ? 'belowBar' : 'aboveBar',
                                shape: sig.signal === 'AL' ? 'arrowUp' : 'arrowDown',
                                color: sig.signal === 'AL' ? '#00e676' : '#ff5252',
                                text: sig.signal === 'AL' ? 'DİP' : 'SAT',
                                size: 2,
                            })
                        })
                    }

                    // Hunter overlay markers
                    const hunterIndicator = activeIndicators.find(i => i.id === 'hunter' && i.visible)
                    if (hunterIndicator) {
                        const hunterSignals = workerComputationState.overlays.hunter
                        hunterSignals.forEach((sig) => {
                            markers.push({
                                time: formatTime(sig.time),
                                position: sig.signal === 'AL' ? 'belowBar' : 'aboveBar',
                                shape: sig.signal === 'AL' ? 'arrowUp' : 'arrowDown',
                                color: sig.signal === 'AL' ? '#76ff03' : '#ff1744',
                                text: sig.signal === 'AL' ? 'DİP' : 'TEPE',
                                size: 2,
                            })
                        })
                    }

                    if (seriesInstance.current) {
                        try {
                            // Sort markers by time (required for v5)
                            const sortedMarkers = [...markers].sort((a, b) => {
                                const timeA = typeof a.time === 'number' ? a.time : parseChartTimeToUnix(a.time)
                                const timeB = typeof b.time === 'number' ? b.time : parseChartTimeToUnix(b.time)
                                return timeA - timeB
                            })

                            const nextMarkersHash = buildMarkerHash(sortedMarkers)
                            if (nextMarkersHash !== lastMarkersHashRef.current) {
                                // Remove existing markers primitive if any
                                if (markersInstance.current) {
                                    try {
                                        markersInstance.current.detach()
                                    } catch {
                                        // Ignore detach errors
                                    }
                                    markersInstance.current = null
                                }

                                // Create new markers primitive (v5 API)
                                if (sortedMarkers.length > 0) {
                                    markersInstance.current = createSeriesMarkers(seriesInstance.current, sortedMarkers)
                                }
                                lastMarkersHashRef.current = nextMarkersHash
                            }
                        } catch (e) {
                            console.error('Error setting markers:', e)
                        }
                    }
                }

            } catch (e) {
                console.error("Chart update error:", e)
            }
        })
        return () => { cancelled = true }
    }, [candles.length, signals, showSignals, activeIndicators, chartReady, chartScope, signalsSignature, markerIndicatorSignature, activeTool, workerComputationState.requestId, workerOverlaySignature, workerComputationState.overlays.combo, workerComputationState.overlays.hunter])

    // Add indicator
    const addIndicator = useCallback((indicatorId: string) => {
        const meta = AVAILABLE_INDICATORS.find(i => i.id === indicatorId)
        if (!meta) return
        if (activeIndicators.some(i => i.id === indicatorId)) return

        setActiveIndicators(prev => [...prev, {
            id: indicatorId,
            meta,
            params: { ...meta.defaultParams },
            visible: true,
        }])
        setShowIndicatorSearch(false)
        setIndicatorSearchQuery("")
    }, [activeIndicators])

    // Remove indicator
    const removeIndicator = useCallback((indicatorId: string) => {
        setActiveIndicators(prev => prev.filter(i => i.id !== indicatorId))
        if (editingIndicatorId === indicatorId) {
            setEditingIndicatorId(null)
            setDraftIndicatorParams({})
        }
    }, [editingIndicatorId])

    const toggleIndicatorVisibility = useCallback((indicatorId: string) => {
        setActiveIndicators(prev => prev.map(ind =>
            ind.id === indicatorId ? { ...ind, visible: !ind.visible } : ind
        ))
    }, [])

    const openIndicatorSettings = useCallback((indicatorId: string) => {
        const indicator = activeIndicators.find((ind) => ind.id === indicatorId)
        if (!indicator || !indicator.meta.paramSchema || indicator.meta.paramSchema.length === 0) {
            return
        }
        setEditingIndicatorId(indicatorId)
        setDraftIndicatorParams({ ...indicator.params })
    }, [activeIndicators])

    const closeIndicatorSettings = useCallback(() => {
        setEditingIndicatorId(null)
        setDraftIndicatorParams({})
    }, [])

    const updateDraftIndicatorParam = useCallback((key: string, value: number) => {
        if (!Number.isFinite(value)) {
            return
        }
        setDraftIndicatorParams(prev => ({ ...prev, [key]: value }))
    }, [])

    const resetDraftIndicatorParams = useCallback(() => {
        const indicator = activeIndicators.find((ind) => ind.id === editingIndicatorId)
        if (!indicator) {
            return
        }
        setDraftIndicatorParams({ ...indicator.meta.defaultParams })
    }, [activeIndicators, editingIndicatorId])

    const applyIndicatorSettings = useCallback(() => {
        if (!editingIndicatorId) {
            return
        }
        setActiveIndicators(prev => prev.map((indicator) => {
            if (indicator.id !== editingIndicatorId) {
                return indicator
            }
            return {
                ...indicator,
                params: { ...indicator.meta.defaultParams, ...draftIndicatorParams },
            }
        }))
        setEditingIndicatorId(null)
        setDraftIndicatorParams({})
    }, [draftIndicatorParams, editingIndicatorId])

    // Symbol selection
    const handleSymbolSelect = (sym: string, market: MarketType) => {
        setSymbol(sym)
        setMarketType(market)
        setShowSymbolSearch(false)
        setSearchQuery("")
    }

    // Get current timeframe label
    const currentTimeframeLabel = useMemo(() => {
        for (const cat of TIMEFRAME_CATEGORIES) {
            const found = cat.items.find(tf => tf.value === timeframe)
            if (found) return found.label
        }
        return timeframe
    }, [timeframe])

    // Filter symbols for search
    const filteredSymbols = useMemo(() => {
        const bistList = (bistSymbols?.symbols || []).map(s => ({
            symbol: s, name: s, market: "BIST" as const
        }))
        const cryptoList = (binanceSymbols || CRYPTO_WATCHLIST).map((s: string) => ({
            symbol: s, name: s.replace('USDT', ''), market: "Kripto" as const
        }))
        const allSymbols = [...bistList, ...cryptoList]
        if (!searchQuery) return allSymbols.slice(0, 30)
        return allSymbols.filter(s =>
            s.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
            s.name.toLowerCase().includes(searchQuery.toLowerCase())
        ).slice(0, 30)
    }, [searchQuery, bistSymbols, binanceSymbols])

    // Filter indicators for search
    const filteredIndicators = useMemo(() => {
        if (!indicatorSearchQuery) return AVAILABLE_INDICATORS
        return AVAILABLE_INDICATORS.filter(i =>
            i.name.toLowerCase().includes(indicatorSearchQuery.toLowerCase()) ||
            i.shortName.toLowerCase().includes(indicatorSearchQuery.toLowerCase())
        )
    }, [indicatorSearchQuery])

    const editingIndicator = useMemo(
        () => activeIndicators.find(ind => ind.id === editingIndicatorId) || null,
        [activeIndicators, editingIndicatorId]
    )

    const activeWatchlist = useMemo(
        () => watchlists.find((watchlist) => watchlist.id === activeWatchlistId) || watchlists[0] || null,
        [watchlists, activeWatchlistId]
    )

    const cryptoQuoteMap = useMemo(() => {
        const map = new Map<string, { priceText: string; change: number }>()
        for (const [sym, payload] of Object.entries(cryptoPrices)) {
            map.set(sym, {
                priceText: payload?.price ? payload.price.toFixed(2) : "---",
                change: payload?.change ?? Number.NaN,
            })
        }
        return map
    }, [cryptoPrices])

    const bistQuoteMap = useMemo(() => {
        const map = new Map<string, { priceText: string; change: number; status?: string; providerTime?: string | null }>()
        for (const ticker of bistTickers || []) {
            const quote = {
                status: ticker.message || ticker.source || "Borsapy / TradingView",
                providerTime: ticker.provider_time,
                priceText: ticker.price?.toFixed(2) || "---",
                change: ticker.changePercent ?? Number.NaN,
            }
            map.set(ticker.symbol.toUpperCase(), quote)
            map.set(ticker.name.toUpperCase(), quote)
        }
        for (const [raw, quote] of Object.entries(activeWatchlistBistQuotes ?? {})) {
            const normalized = raw.endsWith(".IS") ? raw.slice(0, -3) : raw
            const payload = {
                status: quote.message || quote.source || "Borsapy / TradingView",
                providerTime: quote.provider_time,
                priceText: quote.value?.toFixed(2) ?? "---",
                change: quote.change ?? Number.NaN,
            }
            if (raw) map.set(raw, payload)
            if (normalized) map.set(normalized, payload)
        }
        return map
    }, [bistTickers, activeWatchlistBistQuotes])

    const bistSymbolSet = useMemo(
        () => new Set((bistSymbols?.symbols || []).map((s) => s.toUpperCase())),
        [bistSymbols]
    )

    const binanceSymbolSet = useMemo(
        () => new Set((binanceSymbols || []).map((s: string) => s.toUpperCase())),
        [binanceSymbols]
    )

    const activeWatchlistSymbolRows = useMemo(
        () =>
            (activeWatchlist?.rows || []).filter(
                (row): row is WatchlistSymbolRow => row.kind === "symbol"
            ),
        [activeWatchlist]
    )

    const activeWatchlistAlarmRules = useMemo(
        () =>
            watchlistAlarmRules.filter(
                (rule) => (activeWatchlist ? rule.watchlistId === activeWatchlist.id : false)
            ),
        [watchlistAlarmRules, activeWatchlist]
    )

    const utilityCalendarItems = useMemo(
        () => buildUtilityCalendarItems(utilityCalendarResponse?.events ?? []),
        [utilityCalendarResponse]
    )

    const utilityCalendarUpcoming = useMemo(() => {
        return utilityCalendarItems.slice(0, 8)
    }, [utilityCalendarItems])

    const utilityCalendarUpdatedLabel = useMemo(() => {
        if (!utilityCalendarUpdatedAt) return "--"
        return new Date(utilityCalendarUpdatedAt).toLocaleString("tr-TR")
    }, [utilityCalendarUpdatedAt])


    const updateActiveWatchlist = useCallback(
        (updater: (watchlist: WatchlistModel) => WatchlistModel) => {
            setWatchlists((prev) =>
                prev.map((watchlist) =>
                    watchlist.id === activeWatchlistId ? updater(watchlist) : watchlist
                )
            )
        },
        [activeWatchlistId]
    )

    const parseSymbolInput = useCallback(
        (rawInput: string): WatchlistSymbolRow | null => {
            let input = rawInput.trim().toUpperCase().replace(/\s+/g, "")
            if (!input) return null

            if (input.endsWith("/USD")) {
                input = `${input.replace("/USD", "")}USDT`
            }

            if (input.endsWith(".IS")) {
                return symbolRow(input.replace(".IS", ""), "BIST")
            }

            if (input.endsWith("USDT")) {
                return symbolRow(input, "Kripto")
            }

            if (binanceSymbolSet.has(input)) {
                return symbolRow(input, "Kripto")
            }

            if (binanceSymbolSet.has(`${input}USDT`)) {
                return symbolRow(`${input}USDT`, "Kripto")
            }

            if (bistSymbolSet.has(input)) {
                return symbolRow(input, "BIST")
            }

            return null
        },
        [binanceSymbolSet, bistSymbolSet]
    )

    const handleAddSymbolToWatchlist = useCallback(() => {
        if (!activeWatchlist) {
            showWatchlistToast("Aktif liste olmadan sembol eklenemez.")
            return
        }
        setWatchlistDialog({
            type: "addSymbol",
            value: "",
        })
    }, [activeWatchlist, showWatchlistToast])

    const handleRemoveRowFromWatchlist = useCallback(
        (rowIndex: number) => {
            updateActiveWatchlist((watchlist) => ({
                ...watchlist,
                rows: watchlist.rows.filter((_, idx) => idx !== rowIndex),
            }))
        },
        [updateActiveWatchlist]
    )

    const handleToggleWatchlistAlerts = useCallback(() => {
        updateActiveWatchlist((watchlist) => ({
            ...watchlist,
            alarmsEnabled: !watchlist.alarmsEnabled,
        }))
    }, [updateActiveWatchlist])

    const handleCopyWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        const duplicate: WatchlistModel = {
            ...activeWatchlist,
            id: makeWatchlistId(activeWatchlist.name),
            name: `${activeWatchlist.name} Kopya`,
            rows: activeWatchlist.rows.map((row) =>
                row.kind === "section" ? { ...row, id: makeWatchlistId(row.title) } : { ...row }
            ),
        }
        setWatchlists((prev) => [duplicate, ...prev])
        setActiveWatchlistId(duplicate.id)
        setShowWatchlistMenu(false)
        showWatchlistToast("Listenin kopyası oluşturuldu.")
    }, [activeWatchlist, showWatchlistToast])

    const handleRenameWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        setWatchlistDialog({
            type: "renameWatchlist",
            watchlistId: activeWatchlist.id,
            value: activeWatchlist.name,
        })
    }, [activeWatchlist])

    const handleDeleteWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        if (watchlists.length <= 1) {
            showWatchlistToast("En az bir liste kalmalı.")
            return
        }
        setWatchlistDialog({
            type: "deleteWatchlist",
            watchlistId: activeWatchlist.id,
            watchlistName: activeWatchlist.name,
        })
    }, [activeWatchlist, watchlists, showWatchlistToast])

    const handleClearWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        setWatchlistDialog({
            type: "clearWatchlist",
            watchlistId: activeWatchlist.id,
            watchlistName: activeWatchlist.name,
        })
    }, [activeWatchlist])

    const handleCreateWatchlist = useCallback(() => {
        setWatchlistDialog({
            type: "createWatchlist",
            value: "",
        })
    }, [])

    const handleLoadWatchlist = useCallback(() => {
        setShowWatchlistSwitcher(true)
        setShowWatchlistMenu(false)
    }, [])

    const handleShareWatchlist = useCallback(async () => {
        if (!activeWatchlist) return
        const symbols = activeWatchlist.rows
            .filter((row): row is WatchlistSymbolRow => row.kind === "symbol")
            .map((row) => row.rawSymbol)
        if (symbols.length === 0) {
            showWatchlistToast("Paylaşmak için listede sembol yok.")
            return
        }
        const payload = `${activeWatchlist.name}: ${symbols.join(", ")}`
        try {
            await navigator.clipboard.writeText(payload)
            showWatchlistToast("Liste panoya kopyalandı.")
        } catch {
            addToast({
                type: "error",
                title: "Pano erisimi yok",
                message: payload,
                duration: 9000,
            })
        }
        setShowWatchlistMenu(false)
    }, [activeWatchlist, addToast, showWatchlistToast])

    const handleWatchlistNotesChange = useCallback(
        (value: string) => {
            updateActiveWatchlist((watchlist) => ({ ...watchlist, notes: value }))
        },
        [updateActiveWatchlist]
    )

    const handleAppendWatchlistNoteTimestamp = useCallback(() => {
        const stamp = new Date().toLocaleString("tr-TR")
        updateActiveWatchlist((watchlist) => {
            const current = watchlist.notes ? `${watchlist.notes}\n` : ""
            return { ...watchlist, notes: `${current}[${stamp}] ` }
        })
        showWatchlistToast("Notlara zaman damgasi eklendi.")
    }, [showWatchlistToast, updateActiveWatchlist])

    const handleCopyWatchlistNotes = useCallback(async () => {
        if (!activeWatchlist) return
        const text = activeWatchlist.notes?.trim()
        if (!text) {
            showWatchlistToast("Kopyalanacak not bulunamadi.")
            return
        }
        try {
            await navigator.clipboard.writeText(text)
            showWatchlistToast("Notlar panoya kopyalandi.")
        } catch {
            addToast({
                type: "error",
                title: "Pano erisimi yok",
                message: text,
                duration: 9000,
            })
        }
    }, [activeWatchlist, addToast, showWatchlistToast])

    const handleClearWatchlistNotes = useCallback(() => {
        if (!activeWatchlist) return
        setWatchlistDialog({
            type: "clearWatchlistNotes",
            watchlistId: activeWatchlist.id,
            watchlistName: activeWatchlist.name,
        })
    }, [activeWatchlist])

    const closeWatchlistDialog = useCallback(() => {
        setWatchlistDialog(null)
    }, [])

    const commitAlarmRuleChange = useCallback((change: AlarmRuleChange) => {
        const result = updateAlarmRuleStorage(change)
        if (!result.ok) {
            showWatchlistToast("Alarm kuralları tarayıcıya kaydedilemedi. İşlem uygulanmadı.")
            return false
        }
        setWatchlistAlarmRules(result.rules)
        return true
    }, [showWatchlistToast])

    const confirmWatchlistDialog = useCallback(() => {
        if (!watchlistDialog) return

        if (watchlistDialog.type === "addSymbol") {
            if (!activeWatchlist) {
                closeWatchlistDialog()
                return
            }

            const parsed = parseSymbolInput(watchlistDialog.value)
            if (!parsed) {
                addToast({
                    type: "error",
                    title: "Gecersiz sembol",
                    message: "Binance veya BIST sembolu deneyin.",
                })
                return
            }

            let added = false
            updateActiveWatchlist((watchlist) => {
                const exists = watchlist.rows.some(
                    (row) =>
                        row.kind === "symbol" &&
                        row.rawSymbol === parsed.rawSymbol &&
                        row.marketType === parsed.marketType
                )
                if (exists) return watchlist
                added = true
                return { ...watchlist, rows: [...watchlist.rows, parsed] }
            })

            showWatchlistToast(
                added
                    ? `${parsed.rawSymbol} listeye eklendi.`
                    : `${parsed.rawSymbol} zaten listede var.`
            )
            closeWatchlistDialog()
            return
        }

        if (watchlistDialog.type === "renameWatchlist") {
            const normalizedName = watchlistDialog.value.trim()
            if (!normalizedName) {
                addToast({
                    type: "error",
                    title: "Liste adi gerekli",
                    message: "Watchlist adini bos birakamazsiniz.",
                })
                return
            }
            if (!commitAlarmRuleChange({
                type: "rename-watchlist",
                watchlistId: watchlistDialog.watchlistId,
                name: normalizedName,
                updatedAt: new Date().toISOString(),
            })) return
            setWatchlists((prev) =>
                prev.map((watchlist) =>
                    watchlist.id === watchlistDialog.watchlistId
                        ? { ...watchlist, name: normalizedName }
                        : watchlist
                )
            )
            setShowWatchlistMenu(false)
            showWatchlistToast("Liste adı güncellendi.")
            closeWatchlistDialog()
            return
        }

        if (watchlistDialog.type === "createWatchlist") {
            const listName = watchlistDialog.value.trim()
            if (!listName) {
                addToast({
                    type: "error",
                    title: "Liste adi gerekli",
                    message: "Yeni watchlist icin bir isim girin.",
                })
                return
            }
            const watchlist: WatchlistModel = {
                id: makeWatchlistId(listName),
                name: listName,
                alarmsEnabled: false,
                notes: "",
                rows: [],
            }
            setWatchlists((prev) => [watchlist, ...prev])
            setActiveWatchlistId(watchlist.id)
            setShowWatchlistMenu(false)
            setShowWatchlistSwitcher(false)
            showWatchlistToast("Yeni liste oluşturuldu.")
            closeWatchlistDialog()
            return
        }

        if (watchlistDialog.type === "deleteWatchlist") {
            const fallback = watchlists.find((watchlist) => watchlist.id !== watchlistDialog.watchlistId)
            if (!commitAlarmRuleChange({ type: "remove-watchlist", watchlistId: watchlistDialog.watchlistId })) return
            setWatchlists((prev) => prev.filter((watchlist) => watchlist.id !== watchlistDialog.watchlistId))
            if (fallback) {
                setActiveWatchlistId(fallback.id)
            }
            setShowWatchlistMenu(false)
            showWatchlistToast("Liste silindi.")
            closeWatchlistDialog()
            return
        }

        if (watchlistDialog.type === "clearWatchlist") {
            setWatchlists((prev) =>
                prev.map((watchlist) =>
                    watchlist.id === watchlistDialog.watchlistId
                        ? { ...watchlist, rows: [] }
                        : watchlist
                )
            )
            setShowWatchlistMenu(false)
            showWatchlistToast("Liste temizlendi.")
            closeWatchlistDialog()
            return
        }

        if (watchlistDialog.type === "clearWatchlistNotes") {
            setWatchlists((prev) =>
                prev.map((watchlist) =>
                    watchlist.id === watchlistDialog.watchlistId
                        ? { ...watchlist, notes: "" }
                        : watchlist
                )
            )
            showWatchlistToast("Notlar temizlendi.")
            closeWatchlistDialog()
        }
    }, [
        activeWatchlist,
        addToast,
        closeWatchlistDialog,
        commitAlarmRuleChange,
        parseSymbolInput,
        showWatchlistToast,
        updateActiveWatchlist,
        watchlistDialog,
        watchlists,
    ])

    const handleToggleAlarmRule = useCallback((ruleId: string) => {
        const displayedRule = watchlistAlarmRules.find((rule) => rule.id === ruleId)
        if (!displayedRule) return
        commitAlarmRuleChange({
            type: "set-enabled", id: ruleId, enabled: !displayedRule.enabled, updatedAt: new Date().toISOString(),
        })
    }, [commitAlarmRuleChange, watchlistAlarmRules])

    const handleRemoveAlarmRule = useCallback((ruleId: string) => {
        commitAlarmRuleChange({ type: "remove", id: ruleId })
    }, [commitAlarmRuleChange])

    const handleHidePaneIndicators = useCallback(() => {
        setActiveIndicators((prev) =>
            prev.map((indicator) =>
                indicator.meta.isOverlay ? indicator : { ...indicator, visible: false }
            )
        )
        showWatchlistToast("Panel indikatorleri gizlendi.")
    }, [showWatchlistToast])

    const handleShowAllIndicators = useCallback(() => {
        setActiveIndicators((prev) => prev.map((indicator) => ({ ...indicator, visible: true })))
        showWatchlistToast("Tum indikatorler gosteriliyor.")
    }, [showWatchlistToast])

    const handleResetIndicatorLayout = useCallback(() => {
        setActiveIndicators(getDefaultActiveIndicators())
        showWatchlistToast("Indikator yerlesimi varsayilana donduruldu.")
    }, [showWatchlistToast])

    return (
        <div
            ref={fullscreenContainerRef}
            className={cn(
                "relative flex h-full min-h-0 flex-col overflow-y-auto rounded-sm bg-background glass-panel-intense lg:flex-row",
                isFullscreen ? "fixed inset-0 z-50 rounded-none" : ""
            )}
        >
            {/* Main Chart Area */}
            <div className="flex min-h-0 min-w-0 shrink-0 flex-col lg:flex-1">
                {/* Header */}
                <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-border/30">
                    {/* Symbol Selector */}
                    <div className="flex flex-wrap items-center gap-4">
                        <div className="relative">
                            <button
                                aria-label={`Sembol seç: ${symbol} (${marketType})`}
                                onClick={() => setShowSymbolSearch(!showSymbolSearch)}
                                className="flex items-center gap-2 px-4 py-2 rounded-sm bg-card/50 hover:bg-card border border-border/50 hover:border-primary/30 transition-all"
                            >
                                <BarChart3 className="h-4 w-4 text-primary" />
                                <span className="text-lg font-bold">{symbol}</span>
                                <span className={cn(
                                    "text-xs px-2 py-0.5 rounded-full font-medium",
                                    marketType === "BIST" ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                                )}>{marketType}</span>
                                <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            </button>

                            {showSymbolSearch && (
                                <div className="absolute top-full left-0 mt-2 w-96 max-w-[calc(100vw-40px)] glass-panel z-50 overflow-hidden">
                                    <div className="p-3 border-b border-border/30">
                                        <div className="relative">
                                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                            <input
                                                type="text"
                                                value={searchQuery}
                                                onChange={(e) => setSearchQuery(e.target.value)}
                                                placeholder="Sembol ara..."
                                                className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-sm text-sm focus:outline-none focus:border-primary/50"
                                                autoFocus
                                            />
                                        </div>
                                    </div>
                                    <div className="max-h-80 overflow-y-auto">
                                        {filteredSymbols.map((s, index) => (
                                            <button
                                                key={`${s.symbol}-${s.market}-${index}`}
                                                onClick={() => handleSymbolSelect(s.symbol, s.market)}
                                                className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-muted/30 transition-colors"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className={cn("w-2 h-2 rounded-full", s.market === "BIST" ? "bg-primary" : "bg-muted-foreground")} />
                                                    <span className="font-medium">{s.symbol}</span>
                                                </div>
                                                <span className={cn("text-xs px-2 py-0.5 rounded-full", s.market === "BIST" ? "bg-primary/10 text-primary" : "bg-muted text-muted-foreground")}>{s.market}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Price Info */}
                        <div className="flex flex-col">
                            <span className="text-2xl font-bold mono-numbers">
                                {finiteNumber(livePrice)
                                    ? `${marketType === "Kripto" ? "$" : "₺"}${livePrice.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: marketType === "Kripto" ? 4 : 2 })}`
                                    : "—"}
                            </span>
                            {lastBistPrice && <span className="text-xs text-muted-foreground"
                                title={[lastBistPrice.source, lastBistPrice.message].filter(Boolean).join(" · ")}>
                                Son kayıt{lastBistPriceTime && ` · ${lastBistPriceTime} TSİ`}
                            </span>}
                            {cryptoPrice != null && <span className="text-xs text-muted-foreground"
                                title={cryptoReceivedTime ? `Tarayıcı alımı ${cryptoReceivedTime} UTC` : undefined}>
                                {cryptoFeed.liveBySymbol[cryptoSymbol] ? "Binance" : "Binance · Son kayıt"}
                                {cryptoPriceTime && ` · ${cryptoPriceTime} UTC`}
                            </span>}
                            {finiteNumber(priceChangePercent) && <div
                                title={lastBistPrice ? "Günlük değişim" : "Mum değişimi"}
                                className={cn("flex items-center gap-1.5 text-sm", isPositive ? "text-profit" : "text-loss")}>
                                {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                                {priceChange != null && <span className="font-medium mono-numbers">{isPositive ? "+" : ""}{priceChange.toFixed(2)}</span>}
                                <span className="mono-numbers">({isPositive ? "+" : ""}{priceChangePercent.toFixed(2)}%)</span>
                            </div>}
                        </div>
                    </div>

                    {/* Timeframe & Controls */}
                    <div className="flex flex-wrap items-center gap-3">
                        {marketType === "BIST" && <span className="text-xs text-muted-foreground">Borsapy / TradingView</span>}
                        <span className="rounded border border-border px-2 py-1 text-xs text-muted-foreground">{timeFormatters.label}</span>
                        {useBorsapy && <Link className="text-xs text-primary underline" href={canUseBorsapy ? "/research?tab=connection" : "/login?next=%2Fchart"}>{canUseBorsapy ? "Hesap bağlantısı" : "Grafik için yönetici girişi"}</Link>}
                        {/* Quick Timeframes */}
                        <div className="flex items-center bg-muted/30 rounded-sm p-1">
                            {availableQuickTimeframes.map((tf) => (
                                <button
                                    key={tf.value}
                                    onClick={() => setTimeframe(tf.value)}
                                    className={cn(
                                        "px-3 py-1.5 rounded-sm text-sm font-medium transition-all",
                                        timeframe === tf.value ? "bg-raised text-foreground" : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    )}
                                >{tf.label}</button>
                            ))}
                            <div className="relative">
                                <IconButton
                                    onClick={() => setShowTimeframeMenu(!showTimeframeMenu)}
                                    className="px-2 py-1.5 rounded-sm text-muted-foreground hover:text-foreground hover:bg-muted/50"
                                    label={showTimeframeMenu ? "Zaman dilimi menüsünü kapat" : "Zaman dilimi menüsünü aç"}
                                >
                                    <ChevronDown className="h-4 w-4" />
                                </IconButton>
                                {showTimeframeMenu && (
                                    <div className="absolute top-full right-0 mt-2 w-64 glass-panel z-50 overflow-hidden">
                                        {availableTimeframeCategories.map((cat) => (
                                            <div key={cat.category}>
                                                <div className="px-3 py-2 text-xs font-semibold text-muted-foreground bg-muted/30">{cat.category}</div>
                                                <div className="grid grid-cols-3 gap-1 p-2">
                                                    {cat.items.map((tf) => (
                                                        <button
                                                            key={tf.value}
                                                            onClick={() => { setTimeframe(tf.value); setShowTimeframeMenu(false) }}
                                                            className={cn("px-2 py-1.5 rounded text-sm font-medium transition-all", timeframe === tf.value ? "bg-primary/20 text-primary" : "hover:bg-muted/50")}
                                                            title={tf.description}
                                                        >{tf.label}</button>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Tools */}
                        <div className="flex items-center gap-1 bg-muted/30 rounded-sm p-1">
                            <div className="relative">
                                <IconButton
                                    onClick={() => setShowIndicatorSearch(!showIndicatorSearch)}
                                    className={cn("p-2 rounded-sm transition-all", activeIndicators.length > 0 ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                    label={showIndicatorSearch ? "İndikatör menüsünü kapat" : "İndikatör menüsünü aç"}
                                >
                                    <LineChart className="h-4 w-4" />
                                </IconButton>
                                {showIndicatorSearch && (
                                    <div className="absolute top-full right-0 mt-2 w-80 glass-panel z-50 overflow-hidden">
                                        <div className="p-3 border-b border-border/30">
                                            <div className="relative">
                                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                                <input type="text" value={indicatorSearchQuery} onChange={(e) => setIndicatorSearchQuery(e.target.value)} placeholder="İndikatör ara..." className="w-full pl-10 pr-4 py-2 bg-background/50 border border-border/50 rounded-sm text-sm focus:outline-none focus:border-primary/50" autoFocus />
                                            </div>
                                        </div>
                                        {activeIndicators.length > 0 && (
                                            <div className="p-2 border-b border-border/30">
                                                <div className="text-xs text-muted-foreground mb-2 px-2">Aktif İndikatörler</div>
                                                {activeIndicators.map((ind) => (
                                                    <div key={ind.id} className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-muted/30">
                                                        <span className={cn("text-sm font-medium", !ind.visible && "opacity-50")}>{ind.meta.shortName}</span>
                                                        <div className="flex items-center gap-1">
                                                            <IconButton
                                                                onClick={() => toggleIndicatorVisibility(ind.id)}
                                                                className="text-muted-foreground hover:text-foreground"
                                                                label={ind.visible ? `${ind.meta.shortName} göstergesini gizle` : `${ind.meta.shortName} göstergesini göster`}
                                                            >
                                                                {ind.visible ? <Eye className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                                                            </IconButton>
                                                            {ind.meta.paramSchema && ind.meta.paramSchema.length > 0 && (
                                                                <IconButton
                                                                    onClick={() => openIndicatorSettings(ind.id)}
                                                                    className="text-muted-foreground hover:text-primary"
                                                                    label={`${ind.meta.shortName} ayarlarını aç`}
                                                                >
                                                                    <Settings2 className="h-4 w-4" />
                                                                </IconButton>
                                                            )}
                                                            <IconButton onClick={() => removeIndicator(ind.id)} className="text-muted-foreground hover:text-loss" label={`${ind.meta.shortName} göstergesini kaldır`}>
                                                                <Trash2 className="h-4 w-4" />
                                                            </IconButton>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                        <div className="max-h-60 overflow-y-auto p-2">
                                            {filteredIndicators.map((ind) => (
                                                <button
                                                    key={ind.id}
                                                    onClick={() => addIndicator(ind.id)}
                                                    disabled={activeIndicators.some(i => i.id === ind.id)}
                                                    className={cn("w-full flex items-center justify-between px-3 py-2 rounded-sm transition-colors text-left", activeIndicators.some(i => i.id === ind.id) ? "opacity-50 cursor-not-allowed bg-muted/20" : "hover:bg-muted/30")}
                                                >
                                                    <div>
                                                        <div className="font-medium text-sm">{ind.shortName}</div>
                                                        <div className="text-xs text-muted-foreground">{ind.description}</div>
                                                    </div>
                                                    {ind.isOverlay && <span className="text-xs px-2 py-0.5 rounded bg-secondary/20 text-secondary">Overlay</span>}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                            <button
                                onClick={() => setDrawingPanelOpen((value) => !value)}
                                className={cn("flex items-center gap-1.5 rounded-md px-2 py-2 text-xs transition-all", drawingPanelOpen ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                aria-label="26 çizim aracını aç"
                                aria-expanded={drawingPanelOpen}
                            >
                                <Pencil className="h-4 w-4" />
                                <span>Çizimler</span><span className="rounded bg-muted px-1 text-[10px]">26</span>
                            </button>
                        </div>

                        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 rounded-sm text-xs">
                            <Zap className="h-3 w-3 text-primary animate-pulse" />
                            <span className="text-muted-foreground">{dataSource}</span>
                        </div>

                        <IconButton
                            onClick={() => setShowRightPanel(!showRightPanel)}
                            className={cn("p-2 rounded-sm transition-all bg-muted/30 hover:bg-muted/50", showRightPanel && "text-primary")}
                            label={showRightPanel ? "İzleme panelini gizle" : "İzleme panelini göster"}
                        >
                            {showRightPanel ? <PanelRightClose className="h-4 w-4" /> : <PanelRightOpen className="h-4 w-4" />}
                        </IconButton>

                        <IconButton
                            onClick={toggleFullscreen}
                            className="p-2 rounded-sm bg-muted/30 hover:bg-muted/50 hover:text-primary transition-all"
                            label={isFullscreen ? "Grafiği küçült" : "Grafiği tam ekran yap"}
                        >
                            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                        </IconButton>
                    </div>
                </div>

                {/* OHLCV Info Bar */}
                {displayOHLCV && (
                    <div className="flex shrink-0 items-center gap-6 overflow-x-auto px-4 py-2 border-b border-border/30 bg-muted/10">
                        <div className="flex items-center gap-6 text-sm">
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Açılış</span>
                                <span className="font-medium mono-numbers">{displayOHLCV.open.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Yüksek</span>
                                <span className="font-medium mono-numbers text-profit">{displayOHLCV.high.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Düşük</span>
                                <span className="font-medium mono-numbers text-loss">{displayOHLCV.low.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Kapanış</span>
                                <span className={cn("font-medium mono-numbers", displayOHLCV.close >= displayOHLCV.open ? "text-profit" : "text-loss")}>{displayOHLCV.close.toFixed(2)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs uppercase">Hacim</span>
                                <span className="font-medium mono-numbers">{finiteNumber(displayOHLCV.volume)
                                    ? displayOHLCV.volume.toLocaleString("tr-TR", { maximumFractionDigits: 2 }) : "—"}</span>
                            </div>
                        </div>
                        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{currentCrosshair ? timeFormatters.timeFormatter(currentCrosshair.time) : 'Son Mum'}</span>
                        </div>
                    </div>
                )}

                {isCandlesError && hasChartCandles && (
                    <ChartDataError mode="refresh" message={candlesErrorMessage}
                        fetching={isCandlesFetching} onRetry={() => void refetchCandles()} />
                )}
                {previewOnly && !isCandlesError && <p role="status" className="border-b border-border px-4 py-2 text-xs text-muted-foreground">
                    {history.isPending || isCandlesFetching
                        ? "Son mumlar gösteriliyor · Gösterge geçmişi yükleniyor"
                        : "Son mumlar gösteriliyor · Gösterge geçmişi bulunamadı"}
                </p>}

                {/* Chart Area */}
                <div className={cn("relative flex-1 min-h-[320px] overflow-hidden", visiblePanelIndicators.length > 0 && "mb-3")}>
                    {visibleOverlayIndicators.length > 0 && (
                        <div className="absolute left-3 top-3 z-20 flex flex-col gap-1 pointer-events-none">
                            {visibleOverlayIndicators.map((ind) => (
                                <div key={ind.id} className="pointer-events-auto flex items-center gap-2 rounded-sm border border-border/50 bg-background/80 px-2 py-1 backdrop-blur-sm">
                                    <span className="text-xs font-medium">{ind.meta.shortName}</span>
                                    <IconButton
                                        onClick={() => toggleIndicatorVisibility(ind.id)}
                                        className="text-muted-foreground hover:text-foreground"
                                        label={`${ind.meta.shortName} göstergesini gizle`}
                                    >
                                        <Eye className="h-3.5 w-3.5" />
                                    </IconButton>
                                    {ind.meta.paramSchema && ind.meta.paramSchema.length > 0 && (
                                        <IconButton
                                            onClick={() => openIndicatorSettings(ind.id)}
                                            className="text-muted-foreground hover:text-primary"
                                            label={`${ind.meta.shortName} ayarlarını aç`}
                                        >
                                            <Settings2 className="h-3.5 w-3.5" />
                                        </IconButton>
                                    )}
                                    <IconButton
                                        onClick={() => removeIndicator(ind.id)}
                                        className="text-muted-foreground hover:text-loss"
                                        label={`${ind.meta.shortName} göstergesini kaldır`}
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </IconButton>
                                </div>
                            ))}
                        </div>
                    )}

                    {isCandlesLoading && !hasChartCandles && (
                        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10 pointer-events-none">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                                <span className="text-sm text-muted-foreground">Grafik yükleniyor...</span>
                            </div>
                        </div>
                    )}
                    {isCandlesError && !isCandlesLoading && !hasChartCandles && (
                        <ChartDataError mode="fatal" message={candlesErrorMessage}
                            fetching={isCandlesFetching} onRetry={() => void refetchCandles()} />
                    )}
                    <div
                        ref={chartContainerRef}
                        className="w-full h-full cursor-crosshair"
                        style={{ touchAction: 'none' }}
                    />

                    {canUseBorsapy && <ChartDrawingTools
                        key={`${marketType}:${symbol}:${timeframe}:${session?.user.username ?? "anonymous"}`}
                        chartRef={chartInstance}
                        seriesRef={seriesInstance}
                        containerRef={chartContainerRef}
                        ready={chartReady}
                        market={marketType}
                        symbol={symbol}
                        timeframe={timeframe}
                        step={getTimeframeStepSeconds(timeframe)}
                        candles={candles}
                        parseTime={parseChartTimeToUnix}
                        projectionVersion={overlayRenderNonce}
                        open={drawingPanelOpen}
                        onOpenChange={setDrawingPanelOpen}
                        onDrawingMode={onDrawingMode}
                        onCountChange={onDrawingCountChange}
                    />}
                </div>

                {/* Indicator Panels */}
                {hasFullHistory && visiblePanelIndicators.map((ind, index) => (
                    <IndicatorPane
                        key={ind.id}
                        indicator={ind}
                        candles={calculationCandles}
                        precomputedSeries={workerComputationState.panes[ind.id] || null}
                        onRemove={() => {
                            removeIndicator(ind.id)
                            indicatorChartsRef.current.delete(ind.id)
                        }}
                        mainChartRef={chartInstance}
                        hoveredUnixTime={hoveredUnixTime}
                        timeZone={timeFormatters.timeZone}
                        showTimeScale={index === visiblePanelIndicators.length - 1}
                        onChartReady={registerIndicatorChart}
                    />
                ))}

                <CustomIndicatorPanel symbol={symbol} market={marketType} timeframe={timeframe} />

                {/* Status Bar */}
                <MarketDataStatus compact metadata={marketType === "Kripto" ? { ...candlesResponse, source: "Binance" } : candlesResponse} />
                {volumeWarning && <p role="status" className="shrink-0 border-t border-amber-500/30 bg-amber-500/5 px-3 py-2 text-xs text-amber-300">{volumeWarning}</p>}
                <div className="flex shrink-0 flex-wrap items-center justify-between gap-2 px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
                    <div className="flex flex-wrap items-center gap-4">
                        <span className="flex items-center gap-1.5">{useBorsapy
                            ? !canUseBorsapy ? "Yönetici girişi gerekli" : chartStream.isError ? "Akış alınamadı · son mumlar gösteriliyor" : chartStream.data?.message || "TradingView akışı bekleniyor"
                            : isCandlesError ? hasChartCandles ? "Yenileme başarısız · son mumlar gösteriliyor" : "Veri alınamadı" : isCandlesFetching ? "Güncelleniyor" : "Periyodik veri"}</span>
                        <span>{candles.length} mum</span>
                        <span>Periyot: {currentTimeframeLabel}</span>
                        {activeIndicators.length > 0 && <span className="flex items-center gap-1"><LineChart className="h-3 w-3 text-primary" />{activeIndicators.length} indikatör</span>}
                    </div>
                    <div className="flex items-center gap-4">
                        <span>Kaynak: {dataSource}</span>
                        <span className="text-primary/60">TradingView Charts</span>
                    </div>
                </div>
            </div>

            {/* Right Panel - Watchlist (TradingView Style) */}
            {showRightPanel && (
                <div className="flex w-full shrink-0 flex-col border-t border-border/30 bg-surface text-foreground lg:w-[300px] lg:border-l lg:border-t-0 xl:w-[320px]">
                    <div className="flex shrink-0 gap-1 border-b border-border p-2" aria-label="İzleme listesi kaynağı">
                        <button type="button" aria-pressed={watchlistSource === "server"} onClick={() => setWatchlistSource("server")} className={cn("min-h-11 flex-1 rounded px-2 text-xs", watchlistSource === "server" ? "bg-raised text-primary" : "text-muted-foreground")}>Sunucu listeleri</button>
                        <button type="button" aria-pressed={watchlistSource === "local"} onClick={() => setWatchlistSource("local")} className={cn("min-h-11 flex-1 rounded px-2 text-xs", watchlistSource === "local" ? "bg-raised text-primary" : "text-muted-foreground")}>Eski yerel listeler</button>
                    </div>
                    {watchlistSource === "server" ? <ServerWatchlistPanel key={`${session?.user.username}:${session?.expiresAt}`} symbol={symbol} market={marketType} onSelect={handleSymbolSelect} /> : <div className="flex min-h-0 flex-1">
                    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                        <p className="border-b border-border px-3 py-2 text-[11px] text-muted-foreground">Bu listeler yalnız bu tarayıcıda saklanır. Sunucu listelerini etkilemez; alarm merkezinden elle kopyalayabilirsiniz.</p>
                        <div className="relative flex items-center gap-1 px-2 py-2 border-b border-border">
                            <div className="relative">
                                <button
                                    onClick={() => {
                                        setShowWatchlistSwitcher((prev) => !prev)
                                        setShowWatchlistMenu(false)
                                    }}
                                    className="flex items-center gap-1 rounded-sm border border-border bg-raised px-2.5 py-1.5 text-sm font-semibold hover:bg-overlay"
                                >
                                    <span>{activeWatchlist?.name || "Izleme Listesi"}</span>
                                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                                </button>
                                {showWatchlistSwitcher && (
                                    <div className="absolute left-0 top-full mt-2 w-64 rounded-sm border border-border bg-overlay z-50">
                                        <div className="border-b border-border px-3 py-2 text-xs text-muted-foreground">
                                            Son kullanilan listeler
                                        </div>
                                        <div className="max-h-72 overflow-y-auto py-1">
                                            {watchlists.map((watchlist) => (
                                                <button
                                                    key={watchlist.id}
                                                    onClick={() => {
                                                        setActiveWatchlistId(watchlist.id)
                                                        setShowWatchlistSwitcher(false)
                                                    }}
                                                    className={cn(
                                                        "w-full px-3 py-2 text-left text-sm hover:bg-raised",
                                                        watchlist.id === activeWatchlistId && "bg-raised text-primary"
                                                    )}
                                                >
                                                    {watchlist.name}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>

                            <IconButton
                                onClick={handleAddSymbolToWatchlist}
                                className="flex h-7 w-7 items-center justify-center rounded-sm hover:bg-raised text-muted-foreground"
                                label="Listeye sembol ekle"
                            >
                                <Plus className="h-4 w-4" />
                            </IconButton>
                            <IconButton
                                onClick={() => {
                                    refetchTickers()
                                    refetchActiveWatchlistBistQuotes()
                                }}
                                className="flex h-7 w-7 items-center justify-center rounded-sm hover:bg-raised text-muted-foreground"
                                label="Veriyi yenile"
                            >
                                <RefreshCw className="h-4 w-4" />
                            </IconButton>
                            <IconButton
                                onClick={() => {
                                    setShowWatchlistMenu((prev) => !prev)
                                    setShowWatchlistSwitcher(false)
                                }}
                                className="flex h-7 w-7 items-center justify-center rounded-sm hover:bg-raised text-muted-foreground"
                                label="Liste menüsünü aç"
                            >
                                <MoreHorizontal className="h-4 w-4" />
                            </IconButton>

                            {showWatchlistMenu && (
                                <div className="absolute left-2 top-full mt-2 w-72 rounded-sm border border-border bg-overlay z-50 overflow-hidden">
                                    <div className="flex items-center justify-between px-3 py-2 border-b border-border">
                                        <span className="text-sm font-medium">Paylasim listesi</span>
                                        <Link href="/alarms" className="inline-flex min-h-11 items-center gap-1 px-2 text-xs hover:bg-raised">
                                            <Bell className="h-4 w-4" aria-hidden="true" /> Sunucu alarmları
                                        </Link>
                                    </div>
                                    <div className="p-1">
                                        <button onClick={handleShareWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Share2 className="h-4 w-4" /> Listeyi paylas</button>
                                        <button onClick={handleCopyWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Copy className="h-4 w-4" /> Kopya olustur</button>
                                        <button onClick={handleRenameWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Pencil className="h-4 w-4" /> Yeni ad ver</button>
                                        <button onClick={handleClearWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Trash2 className="h-4 w-4" /> Sembolleri temizle</button>
                                        <button onClick={handleDeleteWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm text-loss hover:bg-loss/10"><Trash2 className="h-4 w-4" /> Listeyi sil</button>
                                        <div className="my-1 border-t border-border" />
                                        <button onClick={handleCreateWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Plus className="h-4 w-4" /> Yeni liste olustur</button>
                                        <button onClick={handleLoadWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><FolderOpen className="h-4 w-4" /> Listeyi yukle</button>
                                        <button onClick={handleAddSymbolToWatchlist} className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><Upload className="h-4 w-4" /> Sembol ekle</button>
                                        <Link href="/alarms" className="w-full flex items-center gap-2 rounded px-2 py-2 text-sm hover:bg-raised"><ArrowUpRight className="h-4 w-4" /> Alarmlar sayfasi</Link>
                                    </div>
                                    <div className="border-t border-border px-3 py-2">
                                        <div className="mb-1 text-[11px] text-muted-foreground uppercase">Son kullanilanlar</div>
                                        <div className="space-y-1">
                                            {watchlists.slice(0, 5).map((watchlist) => (
                                                <button
                                                    key={`recent-${watchlist.id}`}
                                                    onClick={() => {
                                                        setActiveWatchlistId(watchlist.id)
                                                        setShowWatchlistMenu(false)
                                                    }}
                                                    className="w-full rounded px-2 py-1.5 text-left text-sm hover:bg-raised"
                                                >
                                                    {watchlist.name}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="grid grid-cols-[1.4fr_1fr_0.8fr] items-center gap-2 border-b border-border px-3 py-2 text-[11px] uppercase text-muted-foreground">
                            <span>Sembol</span>
                            <span className="text-right">Son</span>
                            <span className="text-right">Deg%</span>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {(activeWatchlist?.rows || []).length === 0 && (
                                <div className="px-3 py-4 text-sm text-muted-foreground">
                                    Liste bos. <button className="text-primary hover:underline" onClick={handleAddSymbolToWatchlist}>Sembol ekle</button>
                                </div>
                            )}
                            {(activeWatchlist?.rows || []).map((row, index) => {
                                if (row.kind === "section") {
                                    return (
                                        <div key={row.id} className="px-3 py-2 border-t border-border text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                                            {row.title}
                                        </div>
                                    )
                                }

                                const quote =
                                    row.marketType === "Kripto"
                                        ? cryptoQuoteMap.get(row.rawSymbol)
                                        : bistQuoteMap.get(row.rawSymbol)
                                const displaySymbol =
                                    row.marketType === "Kripto"
                                        ? row.rawSymbol.replace("USDT", "/USD")
                                        : row.rawSymbol
                                const change = quote?.change ?? Number.NaN
                                const priceText = quote?.priceText ?? "---"
                                const quoteStatus = row.marketType === "Kripto" ? "Binance · USDT" : bistQuoteMap.get(row.rawSymbol)?.status || "Borsapy · veri bekleniyor"
                                const quoteTime = row.marketType === "BIST" ? bistQuoteMap.get(row.rawSymbol)?.providerTime : null

                                return (
                                    <div
                                        key={`${row.marketType}-${row.rawSymbol}-${index}`}
                                        className={cn(
                                            "group grid grid-cols-[1.4fr_1fr_0.8fr_20px] items-center gap-2 px-3 py-2 transition-colors hover:bg-raised",
                                            symbol === row.rawSymbol && marketType === row.marketType && "bg-raised"
                                        )}
                                    >
                                        <button
                                            onClick={() => handleSymbolSelect(row.rawSymbol, row.marketType)}
                                            className="truncate text-left text-sm font-medium"
                                            title={`${row.rawSymbol} (${row.marketType}) · ${quoteStatus}${quoteTime ? ` · ${quoteTime}` : ""}`}
                                        >
                                            {displaySymbol}
                                            <span className="block truncate text-[10px] font-normal text-muted-foreground">{quoteStatus}</span>
                                        </button>
                                        <span className="text-right text-sm font-mono tabular-nums">{priceText}</span>
                                        <span className={cn("text-right text-sm font-mono tabular-nums", !Number.isFinite(change) ? "text-muted-foreground" : change >= 0 ? "text-profit" : "text-loss")}>
                                            {Number.isFinite(change) ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
                                        </span>
                                        <IconButton
                                            onClick={() => handleRemoveRowFromWatchlist(index)}
                                            className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-loss transition-opacity"
                                            label={`${row.rawSymbol} satırını kaldır`}
                                        >
                                            <X className="h-3.5 w-3.5" />
                                        </IconButton>
                                    </div>
                                )
                            })}
                        </div>

                        <p className="border-t border-border px-3 py-2 text-[10px] text-muted-foreground">BIST fiyatları açık listedeki ilk 50 sembol için izlenir. Gerçek zamanlı veri kabulü doğrulanmadı.</p>
                        {watchlistNotice && (
                            <div className="border-t border-border px-3 py-2 text-xs text-primary">
                                {watchlistNotice}
                            </div>
                        )}

                        {activeUtilityPanel && (
                            <div className="border-t border-border px-3 py-3 text-xs">
                                {activeUtilityPanel === "alerts" && (
                                    <div className="space-y-3">
                                        <div className="space-y-2 rounded border border-primary/40 bg-base p-3">
                                            <div className="font-semibold">Sunucu alarmları</div>
                                            <p className="text-muted-foreground">Tarayıcı kapalıyken de izlenen kuralları alarm merkezinde oluşturun. Veri geldikçe veya mum kapanışında değerlendirmeyi seçebilirsiniz.</p>
                                            <Link href={`/alarms?symbol=${encodeURIComponent(symbol)}&market=${encodeURIComponent(marketType)}`} className="flex min-h-11 items-center justify-between rounded border border-border px-2 hover:bg-raised">
                                                <span>{symbol} için sunucu alarmı oluştur</span><ArrowUpRight className="h-4 w-4 shrink-0" />
                                            </Link>
                                            {activeWatchlist && <Link href={`/alarms?watchlist=${encodeURIComponent(activeWatchlist.id)}`} className="flex min-h-11 items-center justify-between rounded border border-border px-2 hover:bg-raised">
                                                <span>Bu listeyi sunucuya elle kopyala</span><ArrowUpRight className="h-4 w-4 shrink-0" />
                                            </Link>}
                                            <p className="text-[11px] text-muted-foreground">Semboller forma kopyalanır; kaydetmeden alarm başlamaz. Yönetici girişi gerekir.</p>
                                        </div>
                                        <div className="flex items-center justify-between gap-2">
                                            <span className="text-muted-foreground">Eski yerel liste alarmları</span>
                                            <button onClick={handleToggleWatchlistAlerts} className="min-h-11 rounded border border-border px-2" aria-pressed={Boolean(activeWatchlist?.alarmsEnabled)}>
                                                {activeWatchlist?.alarmsEnabled ? "Yerel açık" : "Yerel kapalı"}
                                            </button>
                                        </div>
                                        <p className="text-muted-foreground">Aşağıdaki eski kurallar yalnız yerel alarm sayfası açıkken kontrol edilir; sunucu alarmlarını etkilemez.</p>
                                        <div className="text-muted-foreground">
                                            Listedeki semboller: {activeWatchlistSymbolRows.length} • Kurallar: {activeWatchlistAlarmRules.length}
                                        </div>

                                        <div className="max-h-40 space-y-1 overflow-y-auto rounded border border-border/40 bg-base p-2">
                                            {activeWatchlistAlarmRules.length === 0 && (
                                                <div className="text-muted-foreground">Bu liste icin alarm kurali yok.</div>
                                            )}
                                            {activeWatchlistAlarmRules.map((rule) => {
                                                const timeframeLabel =
                                                    ALARM_TIMEFRAME_OPTIONS.find((item) => item.value === rule.timeframe)?.label || rule.timeframe
                                                const indicatorLabel =
                                                    ALARM_INDICATOR_OPTIONS.find((item) => item.value === rule.indicator)?.label || rule.indicator
                                                const thresholdText =
                                                    rule.indicator === "rsi"
                                                        ? `DIP<=${rule.thresholds.rsiDipThreshold} / TEPE>=${rule.thresholds.rsiTopThreshold}`
                                                        : rule.indicator === "wr"
                                                            ? `DIP<=${rule.thresholds.wrDipThreshold} / TEPE>=${rule.thresholds.wrTopThreshold}`
                                                            : rule.indicator === "combo"
                                                                ? `DIP>=${rule.thresholds.comboDipThreshold} / TEPE>=${rule.thresholds.comboTopThreshold}`
                                                                : `DIP>=${rule.thresholds.hunterDipThreshold} / TEPE>=${rule.thresholds.hunterTopThreshold}`

                                                return (
                                                    <div key={rule.id} className="rounded border border-border/50 px-2 py-1.5">
                                                        <div className="flex items-center justify-between gap-2">
                                                            <div className="truncate font-medium">{indicatorLabel} • {timeframeLabel}</div>
                                                            <div className="flex items-center gap-1">
                                                                <button
                                                                    onClick={() => handleToggleAlarmRule(rule.id)}
                                                                    className={cn(
                                                                        "rounded px-1.5 py-0.5 text-[10px]",
                                                                        rule.enabled ? "bg-primary text-primary-foreground" : "bg-raised text-muted-foreground"
                                                                    )}
                                                                >
                                                                    {rule.enabled ? "Acik" : "Kapali"}
                                                                </button>
                                                                <IconButton
                                                                    onClick={() => handleRemoveAlarmRule(rule.id)}
                                                                    className="text-muted-foreground hover:text-loss"
                                                                    label="Alarm kuralını sil"
                                                                >
                                                                    <X className="h-3.5 w-3.5" />
                                                                </IconButton>
                                                            </div>
                                                        </div>
                                                        <div className="mt-1 text-[10px] text-muted-foreground">{thresholdText}</div>
                                                    </div>
                                                )
                                            })}
                                        </div>

                                        <Link href="/alarms/local" className="flex min-h-11 items-center justify-between rounded border border-border/50 px-2 py-1.5 text-muted-foreground hover:bg-raised">
                                            <span>Eski yerel alarm sayfasını aç</span>
                                            <ArrowUpRight className="h-3.5 w-3.5" />
                                        </Link>
                                    </div>
                                )}
                                {activeUtilityPanel === "notes" && (
                                    <div className="space-y-2.5">
                                        <div className="flex items-center justify-between">
                                            <span className="text-muted-foreground">Liste notlari</span>
                                            <span className="text-[10px] text-muted-foreground/80">
                                                {(activeWatchlist?.notes || "").length} karakter
                                            </span>
                                        </div>
                                        <textarea
                                            value={activeWatchlist?.notes || ""}
                                            onChange={(e) => handleWatchlistNotesChange(e.target.value)}
                                            placeholder="Bu liste icin not girin..."
                                            className="h-24 w-full resize-none rounded border border-border bg-base px-2 py-1.5 text-xs outline-none focus:border-primary/60"
                                        />
                                        <div className="grid grid-cols-3 gap-1.5">
                                            <button
                                                onClick={handleAppendWatchlistNoteTimestamp}
                                                className="rounded border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-raised"
                                            >
                                                Zaman damgasi
                                            </button>
                                            <button
                                                onClick={handleCopyWatchlistNotes}
                                                className="rounded border border-border px-2 py-1 text-[11px] text-muted-foreground hover:bg-raised"
                                            >
                                                Kopyala
                                            </button>
                                            <button
                                                onClick={handleClearWatchlistNotes}
                                                className="rounded border border-loss/40 px-2 py-1 text-[11px] text-loss hover:bg-loss/10"
                                            >
                                                Temizle
                                            </button>
                                        </div>
                                    </div>
                                )}
                                {activeUtilityPanel === "calendar" && (
                                    <div className="space-y-2 text-muted-foreground">
                                        <div className="flex items-center justify-between">
                                            <span>Ekonomik takvim · Borsapy</span>
                                            <button
                                                onClick={() => refetchUtilityCalendar()}
                                                disabled={!session?.user.is_admin}
                                                className={cn(
                                                    "rounded border border-border px-2 py-0.5 text-[10px] hover:bg-raised",
                                                    isUtilityCalendarFetching && "opacity-70"
                                                )}
                                            >
                                                {isUtilityCalendarFetching ? "Yenileniyor" : "Yenile"}
                                            </button>
                                        </div>
                                        <div className="text-[11px]">
                                            Son guncelleme: {utilityCalendarUpdatedLabel}
                                        </div>
                                        <div className="text-[11px]">Sunucu saati: {serverClockLabel}</div>
                                        <div className="text-[11px]">Grafik periyodu: {currentTimeframeLabel}</div>
                                        <div className="text-[11px]">Saatler kaynağın bildirdiği şekildedir; saat dilimi doğrulanmadı.</div>
                                        {utilityCalendarResponse?.meta.warnings.map(warning => <p key={warning} className="text-[11px] text-warning">{warning}</p>)}
                                        <div className="max-h-52 space-y-1 overflow-y-auto rounded border border-border/40 bg-base p-2">
                                            {utilityCalendarUpcoming.length === 0 && (
                                                <div className="text-[11px] text-muted-foreground">
                                                    Yakin donem ekonomik olay bulunamadi.
                                                </div>
                                            )}
                                            {utilityCalendarUpcoming.map((event) => (
                                                <div key={event.id} className="rounded border border-border/40 px-2 py-1">
                                                    <div className="flex items-center justify-between gap-2">
                                                        <span className="text-[11px] text-foreground">
                                                            {event.date} {event.time}
                                                        </span>
                                                        <span
                                                            className={cn(
                                                                "rounded px-1.5 py-0.5 text-[10px]",
                                                                event.impact === "Yuksek"
                                                                    ? "bg-loss/20 text-loss"
                                                                    : event.impact === "Orta"
                                                                        ? "bg-primary/20 text-primary"
                                                                        : "bg-raised text-muted-foreground"
                                                            )}
                                                        >
                                                            {event.impact}
                                                        </span>
                                                    </div>
                                                    <div className="mt-0.5 text-[11px] text-muted-foreground">
                                                        {event.country} • {event.title}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                        <Link href="/calendar" className="flex items-center justify-between rounded border border-border/50 px-2 py-1.5 hover:bg-raised">
                                            <span>Takvimi tam sayfada ac</span>
                                            <ArrowUpRight className="h-3.5 w-3.5" />
                                        </Link>
                                    </div>
                                )}
                                {activeUtilityPanel === "layout" && (
                                    <div className="space-y-2 text-muted-foreground">
                                        <div className="text-[11px]">Panel: {showRightPanel ? "Acik" : "Kapali"}</div>
                                        <div className="text-[11px]">Indikator sayisi: {activeIndicators.length}</div>
                                        <div className="text-[11px]">Overlay: {visibleOverlayIndicators.length}</div>
                                        <div className="text-[11px]">Alarm kurali: {activeWatchlistAlarmRules.length}</div>

                                        <div className="grid grid-cols-2 gap-1.5">
                                            <button
                                                onClick={() => setShowRightPanel((prev) => !prev)}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                {showRightPanel ? "Paneli gizle" : "Paneli ac"}
                                            </button>
                                            <button
                                                onClick={toggleFullscreen}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                {isFullscreen ? "Kucult" : "Tam ekran"}
                                            </button>
                                            <button
                                                onClick={() => setDrawingPanelOpen(true)}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                Çizimleri yönet
                                            </button>
                                            <button
                                                onClick={handleHidePaneIndicators}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                Alt panelleri gizle
                                            </button>
                                            <button
                                                onClick={handleShowAllIndicators}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                Tum indikatorler
                                            </button>
                                            <button
                                                onClick={handleResetIndicatorLayout}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                Varsayilan layout
                                            </button>
                                        </div>
                                    </div>
                                )}
                                {activeUtilityPanel === "help" && (
                                    <div className="space-y-2 text-muted-foreground">
                                        <div className="rounded border border-border/40 bg-base p-2 text-[11px]">
                                            <div>Notlar: Izleme listesine ozel not tutar, panoya kopyalar.</div>
                                            <div>Takvim: Gercek ekonomik olay akisini 60 sn aralikla yeniler.</div>
                                            <div>Yerlesim: Panel ve grafik duzenini hizli sekilde degistirir.</div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-1.5">
                                            <Link href="/alarms" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Alarm merkezi
                                            </Link>
                                            <Link href="/calendar" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Takvim sayfasi
                                            </Link>
                                            <Link href="/research" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Araştırma
                                            </Link>
                                            <Link href="/trades" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Islemler
                                            </Link>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="w-12 border-l border-border flex flex-col items-center gap-1 py-2">
                        {WATCHLIST_UTILITY_ITEMS.map((panelItem) => {
                            const Icon = panelItem.icon
                            return (
                                <IconButton
                                    key={panelItem.id}
                                    onClick={() =>
                                        setActiveUtilityPanel((prev) =>
                                            prev === panelItem.id ? null : panelItem.id
                                        )
                                    }
                                    className={cn(
                                        "flex h-9 w-9 items-center justify-center rounded-sm transition-colors",
                                        activeUtilityPanel === panelItem.id
                                            ? "bg-raised text-primary"
                                            : "text-muted-foreground hover:bg-raised hover:text-foreground"
                                    )}
                                    label={panelItem.label}
                                >
                                    <Icon className="h-4 w-4" />
                                </IconButton>
                            )
                        })}
                    </div>
                    </div>}
                </div>
            )}

            {editingIndicator && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
                    <div className="w-full max-w-2xl rounded-sm border border-border/50 bg-background">
                        <div className="flex items-center justify-between border-b border-border/40 px-4 py-3">
                            <div>
                                <div className="text-sm text-muted-foreground">İndikatör Ayarları</div>
                                <div className="text-lg font-semibold">{editingIndicator.meta.name}</div>
                            </div>
                            <IconButton
                                onClick={closeIndicatorSettings}
                                className="rounded-sm p-2 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                                label="İndikatör ayarlarını kapat"
                            >
                                <X className="h-4 w-4" />
                            </IconButton>
                        </div>

                        <div className="grid max-h-[65vh] gap-4 overflow-y-auto p-4 md:grid-cols-2">
                            {(editingIndicator.meta.paramSchema || []).map((schema: IndicatorParamSchema) => {
                                const currentValue = draftIndicatorParams[schema.key]
                                    ?? editingIndicator.params[schema.key]
                                    ?? editingIndicator.meta.defaultParams[schema.key]
                                    ?? schema.min
                                const step = schema.step ?? 1
                                const updateSchemaValue = (rawValue: number) => {
                                    const clamped = Math.min(schema.max, Math.max(schema.min, rawValue))
                                    updateDraftIndicatorParam(schema.key, clamped)
                                }
                                return (
                                    <div key={schema.key} className="rounded-sm border border-border/30 bg-muted/10 p-3">
                                        <div className="mb-2 flex items-center justify-between">
                                            <label className="text-sm font-medium">{schema.label}</label>
                                            <span className="text-xs text-muted-foreground">{currentValue}</span>
                                        </div>
                                        <input
                                            type="range"
                                            min={schema.min}
                                            max={schema.max}
                                            step={step}
                                            value={currentValue}
                                            onChange={(e) => updateSchemaValue(Number(e.target.value))}
                                            className="mb-2 w-full"
                                        />
                                        <input
                                            type="number"
                                            min={schema.min}
                                            max={schema.max}
                                            step={step}
                                            value={currentValue}
                                            onChange={(e) => {
                                                const parsed = Number(e.target.value)
                                                if (Number.isNaN(parsed)) return
                                                updateSchemaValue(parsed)
                                            }}
                                            className="w-full rounded-sm border border-border/40 bg-background px-2 py-1 text-sm outline-none focus:border-primary/50"
                                        />
                                    </div>
                                )
                            })}
                        </div>

                        <div className="flex items-center justify-between border-t border-border/40 px-4 py-3">
                            <button
                                onClick={resetDraftIndicatorParams}
                                className="rounded-sm border border-border/40 px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                            >
                                Varsayılanlara Dön
                            </button>
                            <button
                                onClick={applyIndicatorSettings}
                                className="rounded-sm bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90"
                            >
                                Uygula
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <ActionDialog
                open={watchlistDialog !== null}
                title={
                    watchlistDialog?.type === "addSymbol"
                            ? "Watchlist sembol ekle"
                            : watchlistDialog?.type === "renameWatchlist"
                                ? "Watchlist adini degistir"
                                : watchlistDialog?.type === "createWatchlist"
                                    ? "Yeni watchlist"
                                    : watchlistDialog?.type === "deleteWatchlist"
                                        ? "Watchlist silinecek"
                                        : watchlistDialog?.type === "clearWatchlist"
                                            ? "Watchlist temizlenecek"
                                            : watchlistDialog?.type === "clearWatchlistNotes"
                                                ? "Notlar silinecek"
                                                : ""
                }
                description={
                    watchlistDialog?.type === "addSymbol"
                            ? "Ornek: BTCUSDT, ETH/USD veya THYAO"
                            : watchlistDialog?.type === "deleteWatchlist"
                                ? `${watchlistDialog.watchlistName} listesini silmek istiyor musunuz?`
                                : watchlistDialog?.type === "clearWatchlist"
                                    ? `${watchlistDialog.watchlistName} listesindeki tum satirlar silinecek.`
                                    : watchlistDialog?.type === "clearWatchlistNotes"
                                        ? `${watchlistDialog.watchlistName} notlari temizlenecek.`
                                        : "Degeri girip onaylayin."
                }
                mode={
                    watchlistDialog?.type === "deleteWatchlist" ||
                    watchlistDialog?.type === "clearWatchlist" ||
                    watchlistDialog?.type === "clearWatchlistNotes"
                        ? "confirm"
                        : "prompt"
                }
                variant={
                    watchlistDialog?.type === "deleteWatchlist" ||
                    watchlistDialog?.type === "clearWatchlist" ||
                    watchlistDialog?.type === "clearWatchlistNotes"
                        ? "danger"
                        : "default"
                }
                value={watchlistDialog && "value" in watchlistDialog ? watchlistDialog.value : ""}
                placeholder={
                    watchlistDialog?.type === "addSymbol"
                            ? "Sembol"
                            : watchlistDialog?.type === "renameWatchlist" || watchlistDialog?.type === "createWatchlist"
                                ? "Watchlist adi"
                                : undefined
                }
                confirmLabel={
                    watchlistDialog?.type === "addSymbol"
                            ? "Ekle"
                            : watchlistDialog?.type === "renameWatchlist"
                                ? "Guncelle"
                                : watchlistDialog?.type === "createWatchlist"
                                    ? "Olustur"
                                    : watchlistDialog?.type === "deleteWatchlist"
                                        ? "Sil"
                                        : watchlistDialog?.type === "clearWatchlist" || watchlistDialog?.type === "clearWatchlistNotes"
                                            ? "Temizle"
                                            : "Onayla"
                }
                cancelLabel="Vazgec"
                onValueChange={(value) =>
                    setWatchlistDialog((prev) => (prev && "value" in prev ? { ...prev, value } : prev))
                }
                onCancel={closeWatchlistDialog}
                onConfirm={confirmWatchlistDialog}
            />
        </div>
    )
}

export default AdvancedChartPage
