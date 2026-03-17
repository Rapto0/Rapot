"use client"

import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import Link from "next/link"
import { useQuery } from "@tanstack/react-query"
import {
    fetchCandles,
    fetchBistSymbols,
    fetchEconomicCalendar,
    fetchGlobalIndices,
    fetchSignals,
    fetchTicker,
    type ApiSignal,
    type EconomicCalendarEvent,
} from "@/lib/api/client"
import { useBinanceTicker } from "@/lib/hooks/use-binance-ticker"
import { cn } from "@/lib/utils"
import { IconButton } from "@/components/ui/icon-button"
import { Select } from "@/components/ui/select"
import {
    AVAILABLE_INDICATORS,
    type Candle,
    type IndicatorMeta,
    type IndicatorParamSchema,
} from "@/lib/indicators"
import type {
    IndicatorWorkerComputeRequest,
    IndicatorWorkerComputeResponse,
    WorkerIndicatorDescriptor,
    WorkerPaneSeriesResult,
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
    Ruler,
    Pencil,
    Type,
    Plus,
    RefreshCw,
    MoreHorizontal,
    Trash2,
    Settings2,
    Eye,
    EyeOff,
    Bell,
    MessageSquare,
    CalendarDays,
    Newspaper,
    LayoutGrid,
    CircleHelp,
    Share2,
    Copy,
    FolderOpen,
    Upload,
    ArrowUpRight,
} from "lucide-react"
import {
    ALARM_INDICATOR_OPTIONS,
    ALARM_TIMEFRAME_OPTIONS,
    DEFAULT_ALARM_THRESHOLDS,
    createWatchlistAlarmRule,
    loadWatchlistAlarmRules,
    saveWatchlistAlarmRules,
    type AlarmIndicator,
    type AlarmThresholds,
    type AlarmTimeframe,
    type WatchlistAlarmRule,
} from "@/lib/watchlist-alarms"

// ==================== TYPES ====================

interface SignalMarker {
    time: string
    type: 'AL' | 'SAT'
    price: number
    label?: string
}

type MarketType = "BIST" | "Kripto"

interface ActiveIndicator {
    id: string
    meta: IndicatorMeta
    params: Record<string, number>
    visible: boolean
}

interface PersistedActiveIndicator {
    id: string
    params: Record<string, number>
    visible: boolean
}

interface WatchlistSymbolRow {
    kind: "symbol"
    rawSymbol: string
    marketType: MarketType
}

interface WatchlistSectionRow {
    kind: "section"
    id: string
    title: string
}

type WatchlistRow = WatchlistSymbolRow | WatchlistSectionRow

interface WatchlistModel {
    id: string
    name: string
    alarmsEnabled: boolean
    notes: string
    rows: WatchlistRow[]
}

type RightUtilityPanelId = "alerts" | "notes" | "calendar" | "news" | "layout" | "help"

interface UtilityPanelItem {
    id: RightUtilityPanelId
    label: string
    icon: any
}

interface ChartAnchorPoint {
    time: number
    price: number
}

interface RulerDrawing {
    id: string
    start: ChartAnchorPoint
    end: ChartAnchorPoint
}

interface PencilDrawing {
    id: string
    points: ChartAnchorPoint[]
}

interface TextDrawing {
    id: string
    point: ChartAnchorPoint
    text: string
}

interface WorkerComputationState {
    requestId: number
    computeMs: number
    panes: Record<string, WorkerPaneSeriesResult>
    overlays: {
        combo: Array<{ time: string, signal: "AL" | "SAT" }>
        hunter: Array<{ time: string, signal: "AL" | "SAT" }>
    }
}

type UtilityCalendarImpact = "Dusuk" | "Orta" | "Yuksek"

interface UtilityCalendarItem {
    id: string
    date: string
    time: string
    country: string
    title: string
    impact: UtilityCalendarImpact
    actual: string
    forecast: string
    previous: string
    orderKey: string
}

interface WatchlistSignalFeedItem {
    id: number
    symbol: string
    marketType: string
    strategy: string
    signalType: string
    timeframe: string
    specialTag: string
    createdAt: string
}

const INDICATOR_SETTINGS_STORAGE_KEY = "rapot.dashboard.indicators.v1"
const DEFAULT_OVERLAY_INDICATOR_IDS = ["combo", "hunter"] as const
const WATCHLIST_STORAGE_KEY = "rapot.dashboard.watchlists.v1"
const ACTIVE_WATCHLIST_STORAGE_KEY = "rapot.dashboard.watchlists.active.v1"
const WATCHLIST_PANEL_STORAGE_KEY = "rapot.dashboard.watchlists.panel.v1"
const WATCHLIST_UTILITY_CALENDAR_REFRESH_MS = 60_000
const WATCHLIST_UTILITY_SIGNAL_REFRESH_MS = 60_000

const WATCHLIST_UTILITY_ITEMS: UtilityPanelItem[] = [
    { id: "alerts", label: "Alarmlar", icon: Bell },
    { id: "notes", label: "Notlar", icon: MessageSquare },
    { id: "calendar", label: "Takvim", icon: CalendarDays },
    { id: "news", label: "Haberler", icon: Newspaper },
    { id: "layout", label: "Yerleşim", icon: LayoutGrid },
    { id: "help", label: "Yardım", icon: CircleHelp },
]

const makeWatchlistId = (name: string) =>
    `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36)}`

const symbolRow = (rawSymbol: string, marketType: MarketType): WatchlistSymbolRow => ({
    kind: "symbol",
    rawSymbol,
    marketType,
})

const DEFAULT_WATCHLISTS: WatchlistModel[] = [
    {
        id: "binance-spot",
        name: "BINANCE SPOT",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("BTCUSDT", "Kripto"),
            symbolRow("ETHUSDT", "Kripto"),
            symbolRow("BNBUSDT", "Kripto"),
            symbolRow("XRPUSDT", "Kripto"),
            symbolRow("SOLUSDT", "Kripto"),
            symbolRow("DOGEUSDT", "Kripto"),
            symbolRow("ADAUSDT", "Kripto"),
            symbolRow("AVAXUSDT", "Kripto"),
        ],
    },
    {
        id: "futures",
        name: "Futures",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("BTCUSDT", "Kripto"),
            symbolRow("ETHUSDT", "Kripto"),
            symbolRow("SOLUSDT", "Kripto"),
            symbolRow("XRPUSDT", "Kripto"),
            symbolRow("DOGEUSDT", "Kripto"),
        ],
    },
    {
        id: "gem",
        name: "Gem",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("ARBUSDT", "Kripto"),
            symbolRow("SEIUSDT", "Kripto"),
            symbolRow("INJUSDT", "Kripto"),
            symbolRow("TIAUSDT", "Kripto"),
            symbolRow("SUIUSDT", "Kripto"),
        ],
    },
    {
        id: "global",
        name: "Global",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("BTCUSDT", "Kripto"),
            symbolRow("ETHUSDT", "Kripto"),
            symbolRow("THYAO", "BIST"),
            symbolRow("GARAN", "BIST"),
            symbolRow("ASELS", "BIST"),
        ],
    },
    {
        id: "bist-portfolio",
        name: "BIST Portföy",
        alarmsEnabled: false,
        notes: "",
        rows: [
            symbolRow("THYAO", "BIST"),
            symbolRow("ASELS", "BIST"),
            symbolRow("EREGL", "BIST"),
            symbolRow("BIMAS", "BIST"),
            symbolRow("KCHOL", "BIST"),
        ],
    },
]

const getDefaultActiveIndicators = (): ActiveIndicator[] => {
    const defaults: ActiveIndicator[] = []
    for (const id of DEFAULT_OVERLAY_INDICATOR_IDS) {
        const meta = AVAILABLE_INDICATORS.find((indicator) => indicator.id === id)
        if (!meta) continue
        defaults.push({
            id,
            meta,
            params: { ...meta.defaultParams },
            visible: true,
        })
    }
    return defaults
}

// Extended Timeframe options organized by category
const TIMEFRAME_CATEGORIES = [
    {
        category: "Dakika",
        items: [
            { label: "15D", value: "15m", description: "15 Dakika" },
            { label: "30D", value: "30m", description: "30 Dakika" },
        ]
    },
    {
        category: "Saat",
        items: [
            { label: "1S", value: "1h", description: "1 Saat" },
            { label: "2S", value: "2h", description: "2 Saat" },
            { label: "4S", value: "4h", description: "4 Saat" },
            { label: "8S", value: "8h", description: "8 Saat" },
            { label: "12S", value: "12h", description: "12 Saat" },
        ]
    },
    {
        category: "Gün",
        items: [
            { label: "1G", value: "1d", description: "1 Gün" },
            { label: "2G", value: "2d", description: "2 Gün" },
            { label: "3G", value: "3d", description: "3 Gün" },
            { label: "4G", value: "4d", description: "4 Gün" },
            { label: "5G", value: "5d", description: "5 Gün" },
            { label: "6G", value: "6d", description: "6 Gün" },
        ]
    },
    {
        category: "Hafta",
        items: [
            { label: "1H", value: "1wk", description: "1 Hafta" },
            { label: "2H", value: "2wk", description: "2 Hafta" },
            { label: "3H", value: "3wk", description: "3 Hafta" },
        ]
    },
    {
        category: "Ay",
        items: [
            { label: "1A", value: "1mo", description: "1 Ay" },
            { label: "2A", value: "2mo", description: "2 Ay" },
            { label: "3A", value: "3mo", description: "3 Ay" },
        ]
    },
]

// Quick timeframes for header
const QUICK_TIMEFRAMES = [
    { label: "1S", value: "1h" },
    { label: "4S", value: "4h" },
    { label: "1G", value: "1d" },
    { label: "1H", value: "1wk" },
    { label: "1A", value: "1mo" },
]

const BIST_ALLOWED_TIMEFRAMES = new Set([
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "1d",
    "2d",
    "3d",
    "4d",
    "5d",
    "6d",
    "1wk",
    "2wk",
    "3wk",
    "1mo",
    "2mo",
    "3mo",
])

// Popular crypto symbols for watchlist
const CRYPTO_WATCHLIST = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "SOLUSDT", "DOTUSDT", "MATICUSDT", "LTCUSDT",
]

const DEV_PERF_ENABLED = process.env.NODE_ENV !== "production"
const DEV_PERF_THROTTLE_MS = 2000

// ==================== CHART THEME ====================

const chartColors = {
    background: "transparent",
    text: "rgba(255, 255, 255, 0.5)",
    grid: "rgba(255, 255, 255, 0.04)",
    crosshair: "rgba(255, 255, 255, 0.18)",
    crosshairLabel: "#16161e",
    bullish: "#22c55e",
    bearish: "#ef4444",
    volume: {
        up: "rgba(34, 197, 94, 0.18)",
        down: "rgba(239, 68, 68, 0.18)"
    },
    indicators: {
        rsi: "#3b82f6",
        macd: "#8b5cf6",
        macdSignal: "#06b6d4",
        macdHistogram: "rgba(255, 255, 255, 0.28)",
        wr: "#8b5cf6",
        cci: "#3b82f6",
    }
}

const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})$/
const INTRADAY_RE = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/

const normalizeHorzTimeToUnix = (value: unknown): number | null => {
    if (typeof value === "number" && Number.isFinite(value)) {
        return Math.floor(value)
    }
    if (typeof value === "string") {
        if (!value.trim()) return null
        return parseChartTimeToUnix(value)
    }
    if (value && typeof value === "object" && "year" in value && "month" in value && "day" in value) {
        const typed = value as { year: number, month: number, day: number }
        return Math.floor(Date.UTC(typed.year, typed.month - 1, typed.day, 0, 0, 0) / 1000)
    }
    return null
}

const getTimeframeStepSeconds = (timeframe: string): number => {
    const mapping: Record<string, number> = {
        "15m": 15 * 60,
        "30m": 30 * 60,
        "1h": 60 * 60,
        "2h": 2 * 60 * 60,
        "4h": 4 * 60 * 60,
        "8h": 8 * 60 * 60,
        "12h": 12 * 60 * 60,
        "18h": 18 * 60 * 60,
        "1d": 24 * 60 * 60,
        "2d": 2 * 24 * 60 * 60,
        "3d": 3 * 24 * 60 * 60,
        "4d": 4 * 24 * 60 * 60,
        "5d": 5 * 24 * 60 * 60,
        "6d": 6 * 24 * 60 * 60,
        "1wk": 7 * 24 * 60 * 60,
        "2wk": 14 * 24 * 60 * 60,
        "3wk": 21 * 24 * 60 * 60,
        "1mo": 30 * 24 * 60 * 60,
        "2mo": 60 * 24 * 60 * 60,
        "3mo": 90 * 24 * 60 * 60,
    }
    return mapping[timeframe] ?? 24 * 60 * 60
}

const findNearestSeriesPointByTime = (
    points: Array<{ timeKey: number, rawTime: string | number, value: number }>,
    targetTime: number
): { timeKey: number, rawTime: string | number, value: number } | null => {
    if (points.length === 0) return null

    let left = 0
    let right = points.length - 1
    while (left <= right) {
        const mid = Math.floor((left + right) / 2)
        const current = points[mid].timeKey
        if (current === targetTime) return points[mid]
        if (current < targetTime) left = mid + 1
        else right = mid - 1
    }

    const leftPoint = left < points.length ? points[left] : null
    const rightPoint = right >= 0 ? points[right] : null
    if (!leftPoint) return rightPoint
    if (!rightPoint) return leftPoint
    return Math.abs(leftPoint.timeKey - targetTime) < Math.abs(rightPoint.timeKey - targetTime)
        ? leftPoint
        : rightPoint
}

const buildMarkerHash = (markers: Array<{ time: string | number, text?: string, position?: string, color?: string }>): string => {
    if (markers.length === 0) return "0"
    let hash = 17
    for (let i = 0; i < markers.length; i++) {
        const marker = markers[i]
        const encoded = `${marker.time}|${marker.text || ""}|${marker.position || ""}|${marker.color || ""}`
        for (let j = 0; j < encoded.length; j++) {
            hash = (hash * 31 + encoded.charCodeAt(j)) >>> 0
        }
    }
    return `${markers.length}:${hash}`
}

// Helper to parse backend time string into chart timestamp.
// IMPORTANT:
// - BIST intraday timestamps come as TR exchange wall-time.
// - Crypto intraday timestamps come as UTC wall-time.
// Lightweight Charts expects UTC timestamps; we therefore encode the provided wall-time
// as UTC to keep backend grouping boundaries stable on every client timezone.
const parseChartTimeToUnix = (timeStr: string): number => {
    const value = timeStr.trim()
    const intradayMatch = value.match(INTRADAY_RE)
    if (intradayMatch) {
        const year = Number(intradayMatch[1])
        const month = Number(intradayMatch[2])
        const day = Number(intradayMatch[3])
        const hour = Number(intradayMatch[4])
        const minute = Number(intradayMatch[5])
        const second = Number(intradayMatch[6] || "0")
        return Math.floor(Date.UTC(year, month - 1, day, hour, minute, second) / 1000)
    }

    const dateOnlyMatch = value.match(DATE_ONLY_RE)
    if (dateOnlyMatch) {
        const year = Number(dateOnlyMatch[1])
        const month = Number(dateOnlyMatch[2])
        const day = Number(dateOnlyMatch[3])
        return Math.floor(Date.UTC(year, month - 1, day, 0, 0, 0) / 1000)
    }

    const parsed = Date.parse(value)
    if (!Number.isNaN(parsed)) {
        return Math.floor(parsed / 1000)
    }
    return 0
}

// Helper to format date for Lightweight Charts
// For daily data: returns yyyy-mm-dd string
// For intraday data: returns Unix timestamp (seconds)
const formatTime = (timeStr: string): string | number => {
    if (timeStr.includes(' ') || timeStr.includes('T')) {
        return parseChartTimeToUnix(timeStr)
    }
    return timeStr
}

const formatCrosshairTime = (value: unknown): string => {
    if (typeof value === "number") {
        return new Intl.DateTimeFormat("tr-TR", {
            timeZone: "UTC",
            year: "2-digit",
            month: "short",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
        }).format(new Date(value * 1000))
    }

    if (typeof value === "string") {
        if (value.trim().length === 0) return value
        const unix = parseChartTimeToUnix(value)
        return formatCrosshairTime(unix)
    }

    if (value && typeof value === "object" && "year" in value && "month" in value && "day" in value) {
        const typed = value as { year: number, month: number, day: number }
        const unix = Math.floor(Date.UTC(typed.year, typed.month - 1, typed.day, 0, 0, 0) / 1000)
        return new Intl.DateTimeFormat("tr-TR", {
            timeZone: "UTC",
            year: "2-digit",
            month: "short",
            day: "2-digit",
        }).format(new Date(unix * 1000))
    }

    return String(value ?? "")
}

// Helper to deduplicate and sort candle data by time
const deduplicateByTime = <T extends { time: string | number }>(data: T[]): T[] => {
    const seen = new Map<string | number, T>()
    for (const item of data) {
        seen.set(item.time, item) // Later items override earlier ones
    }
    return Array.from(seen.values()).sort((a, b) => {
        const timeA = typeof a.time === 'number' ? a.time : parseChartTimeToUnix(a.time)
        const timeB = typeof b.time === 'number' ? b.time : parseChartTimeToUnix(b.time)
        return timeA - timeB
    })
}

const mapUtilityCalendarImpact = (value: string | null): UtilityCalendarImpact => {
    const normalized = (value || "").toLowerCase()
    if (normalized.includes("high") || normalized === "3" || normalized.includes("critical")) return "Yuksek"
    if (normalized.includes("medium") || normalized === "2" || normalized.includes("med")) return "Orta"
    return "Dusuk"
}

const formatUtilityCalendarMetric = (value: number | null, unit: string | null): string => {
    if (value === null || value === undefined) return ""
    const numeric = Number(value)
    const formatted = Number.isInteger(numeric) ? numeric.toString() : numeric.toFixed(2)
    return `${formatted}${unit || ""}`
}

const parseUtilityCalendarDateTime = (
    value: string | null
): { date: string, time: string, orderKey: string } | null => {
    if (!value) return null
    const direct = value.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/)
    if (direct) {
        const date = direct[1]
        const time = direct[2]
        return { date, time, orderKey: `${date}T${time}` }
    }

    const normalized = value.includes("T") ? value : value.replace(" ", "T")
    const dateObj = new Date(normalized)
    if (Number.isNaN(dateObj.getTime())) return null

    return {
        date: dateObj.toISOString().slice(0, 10),
        time: dateObj.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" }),
        orderKey: dateObj.toISOString(),
    }
}

const buildUtilityCalendarItems = (rawEvents: EconomicCalendarEvent[]): UtilityCalendarItem[] => {
    return rawEvents
        .map((event, index) => {
            const parsed = parseUtilityCalendarDateTime(event.time)
            if (!parsed) return null
            return {
                id: `${parsed.orderKey}-${event.country || "ROW"}-${index}`,
                date: parsed.date,
                time: parsed.time,
                country: (event.country || event.currency || "ROW").toUpperCase(),
                title: event.event || "Ekonomik veri",
                impact: mapUtilityCalendarImpact(event.impact),
                actual: formatUtilityCalendarMetric(event.actual, event.unit),
                forecast: formatUtilityCalendarMetric(event.estimate, event.unit),
                previous: formatUtilityCalendarMetric(event.previous, event.unit),
                orderKey: parsed.orderKey,
            }
        })
        .filter((item): item is UtilityCalendarItem => item !== null)
        .sort((a, b) => a.orderKey.localeCompare(b.orderKey))
}

const buildWatchlistSignalFeed = (
    rawSignals: ApiSignal[],
    activeSymbolRows: WatchlistSymbolRow[]
): WatchlistSignalFeedItem[] => {
    if (rawSignals.length === 0 || activeSymbolRows.length === 0) return []
    const symbolSet = new Set(
        activeSymbolRows.map((row) => `${row.marketType}:${row.rawSymbol.toUpperCase()}`)
    )

    return rawSignals
        .filter((signal) => {
            const marketType = signal.market_type === "BIST" ? "BIST" : "Kripto"
            const symbol = signal.symbol?.toUpperCase?.() || ""
            return symbolSet.has(`${marketType}:${symbol}`)
        })
        .sort((a, b) => {
            const left = a.created_at ? Date.parse(a.created_at) : 0
            const right = b.created_at ? Date.parse(b.created_at) : 0
            return right - left
        })
        .slice(0, 12)
        .map((signal) => ({
            id: signal.id,
            symbol: signal.symbol,
            marketType: signal.market_type,
            strategy: signal.strategy,
            signalType: signal.signal_type,
            timeframe: signal.timeframe,
            specialTag: signal.special_tag || "-",
            createdAt: signal.created_at || "",
        }))
}

const formatSignalTimestamp = (isoValue: string): string => {
    if (!isoValue) return "-"
    const date = new Date(isoValue)
    if (Number.isNaN(date.getTime())) return "-"
    return date.toLocaleString("tr-TR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    })
}

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
    // Basic state
    const [symbol, setSymbol] = useState(initialSymbol)
    const [marketType, setMarketType] = useState<MarketType>(initialMarket)
    const [timeframe, setTimeframe] = useState("1d")
    const [showSymbolSearch, setShowSymbolSearch] = useState(false)
    const [showTimeframeMenu, setShowTimeframeMenu] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [isFullscreen, setIsFullscreen] = useState(false)
    const [showRightPanel, setShowRightPanel] = useState(showWatchlist)
    const [watchlists, setWatchlists] = useState<WatchlistModel[]>(() => DEFAULT_WATCHLISTS)
    const [activeWatchlistId, setActiveWatchlistId] = useState<string>(DEFAULT_WATCHLISTS[0]?.id || "")
    const [showWatchlistSwitcher, setShowWatchlistSwitcher] = useState(false)
    const [showWatchlistMenu, setShowWatchlistMenu] = useState(false)
    const [activeUtilityPanel, setActiveUtilityPanel] = useState<RightUtilityPanelId | null>("alerts")
    const [watchlistsHydrated, setWatchlistsHydrated] = useState(false)
    const [watchlistNotice, setWatchlistNotice] = useState<string | null>(null)
    const [serverClockLabel, setServerClockLabel] = useState("--")
    const [watchlistAlarmRules, setWatchlistAlarmRules] = useState<WatchlistAlarmRule[]>([])
    const [watchlistAlarmRulesHydrated, setWatchlistAlarmRulesHydrated] = useState(false)
    const [alarmIndicatorDraft, setAlarmIndicatorDraft] = useState<AlarmIndicator>("rsi")
    const [alarmTimeframeDraft, setAlarmTimeframeDraft] = useState<AlarmTimeframe>("4h")
    const [alarmThresholdDraft, setAlarmThresholdDraft] = useState<AlarmThresholds>(() => ({
        ...DEFAULT_ALARM_THRESHOLDS,
    }))

    // Indicator state
    const [showIndicatorSearch, setShowIndicatorSearch] = useState(false)
    const [indicatorSearchQuery, setIndicatorSearchQuery] = useState("")
    const [activeIndicators, setActiveIndicators] = useState<ActiveIndicator[]>(() => getDefaultActiveIndicators())
    const [editingIndicatorId, setEditingIndicatorId] = useState<string | null>(null)
    const [draftIndicatorParams, setDraftIndicatorParams] = useState<Record<string, number>>({})
    const [indicatorStateHydrated, setIndicatorStateHydrated] = useState(false)

    // Drawing tools state
    const [activeTool, setActiveTool] = useState<'none' | 'ruler' | 'pencil' | 'text'>('none')
    const [rulerDrawings, setRulerDrawings] = useState<RulerDrawing[]>([])
    const [rulerDraftStart, setRulerDraftStart] = useState<ChartAnchorPoint | null>(null)
    const [rulerDraftEnd, setRulerDraftEnd] = useState<ChartAnchorPoint | null>(null)
    const [pencilDrawings, setPencilDrawings] = useState<PencilDrawing[]>([])
    const [activePencilPoints, setActivePencilPoints] = useState<ChartAnchorPoint[] | null>(null)
    const [textDrawings, setTextDrawings] = useState<TextDrawing[]>([])
    const [overlayRenderNonce, setOverlayRenderNonce] = useState(0)
    const [hoveredUnixTime, setHoveredUnixTime] = useState<number | null>(null)

    // Chart ready state
    const [chartReady, setChartReady] = useState(false)

    // Crosshair data
    const [crosshairData, setCrosshairData] = useState<{
        time: string
        open: number
        high: number
        low: number
        close: number
        volume: number
    } | null>(null)
    const [workerComputationState, setWorkerComputationState] = useState<WorkerComputationState>({
        requestId: 0,
        computeMs: 0,
        panes: {},
        overlays: { combo: [], hunter: [] },
    })

    // Refs
    const chartContainerRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<any>(null)
    const seriesInstance = useRef<any>(null)
    const markersInstance = useRef<any>(null) // v5 markers primitive
    const lastCrosshairUnixRef = useRef<number | null>(null)
    const activeToolRef = useRef<'none' | 'ruler' | 'pencil' | 'text'>('none')
    const lastMarkersHashRef = useRef<string>("")
    const lastCandleHashRef = useRef<string>("")
    const fullscreenContainerRef = useRef<HTMLDivElement>(null)
    const isInitialLoadRef = useRef<boolean>(true)
    const lastSymbolRef = useRef<string>(initialSymbol)
    const lastTimeframeRef = useRef<string>("1d")
    const lastRouteSelectionRef = useRef<{ symbol: string; market: MarketType }>({
        symbol: initialSymbol.trim().toUpperCase(),
        market: initialMarket,
    })
    const indicatorChartsRef = useRef<Map<string, any>>(new Map())
    const isPointerDrawingRef = useRef(false)
    const rulerDraftStartRef = useRef<ChartAnchorPoint | null>(null)
    const rulerMoveRafRef = useRef<number | null>(null)
    const pendingRulerAnchorRef = useRef<ChartAnchorPoint | null>(null)
    const overlaySyncRafRef = useRef<number | null>(null)
    const hasProjectedDrawingsRef = useRef(false)
    const indicatorWorkerRef = useRef<Worker | null>(null)
    const latestWorkerRequestIdRef = useRef(0)
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
            } catch (error) {
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
                items: category.items.filter((item) => BIST_ALLOWED_TIMEFRAMES.has(item.value)),
            }))
            .filter((category) => category.items.length > 0)
    }, [marketType])

    const availableQuickTimeframes = useMemo(() => {
        if (marketType !== "BIST") return QUICK_TIMEFRAMES
        return QUICK_TIMEFRAMES.filter((item) => BIST_ALLOWED_TIMEFRAMES.has(item.value))
    }, [marketType])

    useEffect(() => {
        if (marketType !== "BIST") return
        if (BIST_ALLOWED_TIMEFRAMES.has(timeframe)) return
        setTimeframe("1d")
    }, [marketType, timeframe])

    useEffect(() => {
        activeToolRef.current = activeTool
    }, [activeTool])

    useEffect(() => {
        hasProjectedDrawingsRef.current =
            rulerDrawings.length > 0 ||
            pencilDrawings.length > 0 ||
            textDrawings.length > 0 ||
            rulerDraftStart !== null ||
            rulerDraftEnd !== null ||
            activePencilPoints !== null
    }, [rulerDrawings, pencilDrawings, textDrawings, rulerDraftStart, rulerDraftEnd, activePencilPoints])

    useEffect(() => {
        rulerDraftStartRef.current = rulerDraftStart
    }, [rulerDraftStart])

    useEffect(() => {
        const updateClock = () => setServerClockLabel(new Date().toLocaleString("tr-TR"))
        updateClock()
        const timer = window.setInterval(updateClock, 1000)
        return () => window.clearInterval(timer)
    }, [])

    const anchorFromClientPoint = useCallback((clientX: number, clientY: number): ChartAnchorPoint | null => {
        if (!chartContainerRef.current || !chartInstance.current || !seriesInstance.current) return null
        const rect = chartContainerRef.current.getBoundingClientRect()
        const x = clientX - rect.left
        const y = clientY - rect.top

        if (x < 0 || y < 0 || x > rect.width || y > rect.height) return null

        const timeValue = chartInstance.current.timeScale().coordinateToTime(x)
        const unix = normalizeHorzTimeToUnix(timeValue)
        const price = seriesInstance.current.coordinateToPrice(y)

        if (unix === null || price === null || !Number.isFinite(price)) return null
        return { time: unix, price }
    }, [])

    const projectAnchorToScreen = useCallback((point: ChartAnchorPoint): { x: number, y: number } | null => {
        if (!chartInstance.current || !seriesInstance.current) return null
        const x = chartInstance.current.timeScale().timeToCoordinate(point.time)
        const y = seriesInstance.current.priceToCoordinate(point.price)
        if (x === null || y === null || !Number.isFinite(x) || !Number.isFinite(y)) return null
        return { x, y }
    }, [])

    const handleDrawingMouseDown = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
        if (activeTool === "none") return
        const anchor = anchorFromClientPoint(event.clientX, event.clientY)
        if (!anchor) return

        if (activeTool === "ruler") {
            const currentDraftStart = rulerDraftStartRef.current
            if (!currentDraftStart) {
                setRulerDraftStart(anchor)
                setRulerDraftEnd(anchor)
                rulerDraftStartRef.current = anchor
            } else {
                setRulerDrawings((prev) => [...prev, {
                    id: `${Date.now().toString(36)}-${prev.length}`,
                    start: currentDraftStart,
                    end: anchor,
                }])
                setRulerDraftStart(null)
                setRulerDraftEnd(null)
                rulerDraftStartRef.current = null
            }
            return
        }

        if (activeTool === "pencil") {
            isPointerDrawingRef.current = true
            setActivePencilPoints([anchor])
            return
        }

        if (activeTool === "text") {
            const text = window.prompt("Grafiğe eklenecek metni girin:")
            if (!text || !text.trim()) return
            setTextDrawings((prev) => [...prev, {
                id: `${Date.now().toString(36)}-${prev.length}`,
                point: anchor,
                text: text.trim(),
            }])
        }
    }, [activeTool, anchorFromClientPoint])

    const handleDrawingMouseMove = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
        if (activeTool === "none") return
        const anchor = anchorFromClientPoint(event.clientX, event.clientY)
        if (!anchor) return

        if (activeTool === "ruler" && rulerDraftStartRef.current) {
            pendingRulerAnchorRef.current = anchor
            if (rulerMoveRafRef.current === null) {
                rulerMoveRafRef.current = window.requestAnimationFrame(() => {
                    rulerMoveRafRef.current = null
                    const nextAnchor = pendingRulerAnchorRef.current
                    if (!nextAnchor) return
                    setRulerDraftEnd((prev) => {
                        if (prev && Math.abs(prev.time - nextAnchor.time) < 1 && Math.abs(prev.price - nextAnchor.price) < 0.01) {
                            return prev
                        }
                        return nextAnchor
                    })
                })
            }
            return
        }

        if (activeTool === "pencil" && isPointerDrawingRef.current) {
            setActivePencilPoints((prev) => {
                if (!prev || prev.length === 0) return [anchor]
                const last = prev[prev.length - 1]
                if (Math.abs(last.time - anchor.time) < 1 && Math.abs(last.price - anchor.price) < 0.01) {
                    return prev
                }
                return [...prev, anchor]
            })
        }
    }, [activeTool, anchorFromClientPoint])

    const handleDrawingMouseUp = useCallback(() => {
        if (activeTool === "pencil" && isPointerDrawingRef.current) {
            isPointerDrawingRef.current = false
            setActivePencilPoints((prev) => {
                if (!prev || prev.length < 2) return null
                setPencilDrawings((existing) => [...existing, {
                    id: `${Date.now().toString(36)}-${existing.length}`,
                    points: prev,
                }])
                return null
            })
        }
    }, [activeTool])

    useEffect(() => {
        if (activeTool !== "ruler") {
            if (rulerMoveRafRef.current !== null) {
                window.cancelAnimationFrame(rulerMoveRafRef.current)
                rulerMoveRafRef.current = null
            }
            pendingRulerAnchorRef.current = null
            setRulerDraftStart(null)
            setRulerDraftEnd(null)
            rulerDraftStartRef.current = null
        }
        if (activeTool !== "pencil") {
            isPointerDrawingRef.current = false
            setActivePencilPoints(null)
        }
    }, [activeTool])

    useEffect(() => {
        return () => {
            if (overlaySyncRafRef.current !== null) {
                window.cancelAnimationFrame(overlaySyncRafRef.current)
                overlaySyncRafRef.current = null
            }
            if (rulerMoveRafRef.current !== null) {
                window.cancelAnimationFrame(rulerMoveRafRef.current)
                rulerMoveRafRef.current = null
            }
        }
    }, [])

    useEffect(() => {
        if (!watchlistNotice) return
        const timer = setTimeout(() => setWatchlistNotice(null), 2800)
        return () => clearTimeout(timer)
    }, [watchlistNotice])

    useEffect(() => {
        if (typeof window === "undefined") {
            setWatchlistsHydrated(true)
            setWatchlistAlarmRulesHydrated(true)
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
                storedPanel === "news" ||
                storedPanel === "layout" ||
                storedPanel === "help"
            ) {
                setActiveUtilityPanel(storedPanel)
            }

            const restoredAlarmRules = loadWatchlistAlarmRules()
            if (restoredAlarmRules.length > 0) {
                setWatchlistAlarmRules(restoredAlarmRules)
            }
        } catch (error) {
            console.error("Watchlist state could not be restored:", error)
        } finally {
            setWatchlistsHydrated(true)
            setWatchlistAlarmRulesHydrated(true)
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
        if (!watchlistAlarmRulesHydrated || typeof window === "undefined") return
        saveWatchlistAlarmRules(watchlistAlarmRules)
    }, [watchlistAlarmRules, watchlistAlarmRulesHydrated])

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

    // Fetch candle data
    const { data: candlesResponse, isLoading } = useQuery({
        queryKey: ['chart-candles', symbol, marketType, timeframe],
        queryFn: () => fetchCandles(symbol, marketType, timeframe, 1000),
        refetchInterval: 60000,
    })

    // Fetch BIST symbols for search
    const { data: bistSymbols } = useQuery({
        queryKey: ['bist-symbols'],
        queryFn: fetchBistSymbols,
        staleTime: 300000,
    })

    // Fetch all Binance USDT pairs
    const { data: binanceSymbols } = useQuery({
        queryKey: ['binance-symbols'],
        queryFn: async () => {
            const res = await fetch('https://api.binance.com/api/v3/exchangeInfo')
            const data = await res.json()
            return data.symbols
                .filter((s: any) => s.quoteAsset === 'USDT' && s.status === 'TRADING')
                .map((s: any) => s.symbol)
                .sort()
        },
        staleTime: 3600000,
    })

    // Fetch BIST tickers for watchlist
    const { data: bistTickers, refetch: refetchTickers } = useQuery({
        queryKey: ['watchlist-ticker'],
        queryFn: fetchTicker,
        refetchInterval: 30000,
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
        return Array.from(set).sort()
    }, [watchlists, activeWatchlistId])

    const { data: activeWatchlistBistQuotes, refetch: refetchActiveWatchlistBistQuotes } = useQuery({
        queryKey: ['watchlist-active-bist-quotes', ...activeWatchlistBistSymbolsForQuery],
        queryFn: () => fetchGlobalIndices(activeWatchlistBistSymbolsForQuery),
        enabled: activeWatchlistBistSymbolsForQuery.length > 0,
        refetchInterval: 30000,
        staleTime: 10_000,
    })

    const utilityCalendarRange = useMemo(() => {
        const now = new Date()
        const from = now.toISOString().slice(0, 10)
        const toDate = new Date(now)
        toDate.setDate(toDate.getDate() + 7)
        const to = toDate.toISOString().slice(0, 10)
        return { from, to }
    }, [])

    const {
        data: utilityCalendarRaw = [],
        isFetching: isUtilityCalendarFetching,
        dataUpdatedAt: utilityCalendarUpdatedAt,
        refetch: refetchUtilityCalendar,
    } = useQuery({
        queryKey: ['chart-watchlist-calendar', utilityCalendarRange.from, utilityCalendarRange.to],
        queryFn: () =>
            fetchEconomicCalendar({
                from_date: utilityCalendarRange.from,
                to_date: utilityCalendarRange.to,
            }),
        refetchInterval: WATCHLIST_UTILITY_CALENDAR_REFRESH_MS,
        staleTime: 30_000,
    })

    const {
        data: utilityWatchlistSignalsRaw = [],
        isFetching: isUtilitySignalsFetching,
        refetch: refetchUtilitySignals,
    } = useQuery({
        queryKey: ['chart-watchlist-signals-feed'],
        queryFn: () => fetchSignals({ limit: 300 }),
        refetchInterval: WATCHLIST_UTILITY_SIGNAL_REFRESH_MS,
        staleTime: 30_000,
    })

    const watchlistCryptoSymbols = useMemo(() => {
        const symbols = new Set<string>(CRYPTO_WATCHLIST)
        for (const list of watchlists) {
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
    }, [watchlists, marketType, symbol])

    // Live crypto prices for watchlist
    const cryptoPrices = useBinanceTicker(watchlistCryptoSymbols, {
        paused: activeTool !== "none",
        flushIntervalMs: 320,
    })

    const candles: Candle[] = useMemo(() => {
        const rawCandles = candlesResponse?.candles || []
        if (rawCandles.length === 0) return []

        const deduped = new Map<number, Candle>()
        for (const candle of rawCandles) {
            const unix = parseChartTimeToUnix(candle.time)
            deduped.set(unix, candle)
        }

        return Array.from(deduped.entries())
            .sort((a, b) => a[0] - b[0])
            .map((entry) => entry[1])
    }, [candlesResponse?.candles])
    const dataSource = candlesResponse?.source || "loading"

    const candlesSignature = useMemo(() => {
        if (candles.length === 0) return "empty"
        const first = candles[0]
        const last = candles[candles.length - 1]
        return `${candles.length}:${first.time}:${first.open}:${first.high}:${first.low}:${first.close}:${last.time}:${last.open}:${last.high}:${last.low}:${last.close}`
    }, [candles])

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
            if (message.requestId < latestWorkerRequestIdRef.current) {
                return
            }
            setWorkerComputationState({
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

        pendingWorkerDispatchTimerRef.current = window.setTimeout(() => {
            const worker = indicatorWorkerRef.current
            if (!worker) return

            const requestId = latestWorkerRequestIdRef.current + 1
            latestWorkerRequestIdRef.current = requestId

            const message: IndicatorWorkerComputeRequest = {
                type: "compute-indicators",
                requestId,
                candles,
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
    }, [candles, candlesSignature, workerIndicators, workerIndicatorSignature])

    // Calculate price info
    const currentPrice = candles.length > 0 ? candles[candles.length - 1].close : 0
    const prevPrice = candles.length > 1 ? candles[candles.length - 2].close : currentPrice
    const priceChange = currentPrice - prevPrice
    const priceChangePercent = prevPrice > 0 ? (priceChange / prevPrice) * 100 : 0
    const isPositive = priceChange >= 0

    // Live price for crypto
    const livePrice = marketType === "Kripto" && cryptoPrices[symbol]
        ? cryptoPrices[symbol].price
        : currentPrice

    // OHLCV display data
    const displayOHLCV = crosshairData || (candles.length > 0 ? candles[candles.length - 1] : null)

    const visibleOverlayIndicators = useMemo(
        () => activeIndicators.filter(ind => ind.meta.isOverlay && ind.visible),
        [activeIndicators]
    )

    const visiblePanelIndicators = useMemo(
        () => activeIndicators.filter(ind => !ind.meta.isOverlay && ind.visible),
        [activeIndicators]
    )

    const showMainTimeScale = visiblePanelIndicators.length === 0

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

    // Create/update chart
    useEffect(() => {
        if (!chartContainerRef.current) return

        import("lightweight-charts").then(({ createChart, ColorType, CrosshairMode, CandlestickSeries }) => {
            if (!chartContainerRef.current) return

            // Destroy existing chart
            if (chartInstance.current) {
                chartInstance.current.remove()
                chartInstance.current = null
                seriesInstance.current = null
                markersInstance.current = null
                setChartReady(false)
            }

            const containerWidth = chartContainerRef.current.clientWidth
            const containerHeight = isFullscreen ? window.innerHeight - 120 : 500

            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { type: ColorType.Solid, color: chartColors.background },
                    textColor: chartColors.text,
                    fontSize: 12,
                },
                grid: {
                    vertLines: { color: chartColors.grid },
                    horzLines: { color: chartColors.grid },
                },
                width: containerWidth,
                height: containerHeight,
                rightPriceScale: {
                    borderColor: chartColors.grid,
                    // Keep main price labels away from the indicator pane border.
                    scaleMargins: { top: 0.05, bottom: showMainTimeScale ? 0.05 : 0.2 },
                    minimumWidth: 64,
                },
                timeScale: {
                    visible: showMainTimeScale,
                    borderColor: chartColors.grid,
                    timeVisible: true,
                    secondsVisible: false,
                    rightOffset: 12,
                    barSpacing: 6,
                    minBarSpacing: 2,
                },
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
                if (candleData && 'open' in candleData) {
                    setCrosshairData({
                        time: formatCrosshairTime(param.time),
                        open: candleData.open,
                        high: candleData.high,
                        low: candleData.low,
                        close: candleData.close,
                        volume: 0,
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
                if (chartContainerRef.current && chartInstance.current) {
                    const newHeight = isFullscreen ? window.innerHeight - 120 : 500
                    chartInstance.current.applyOptions({
                        width: chartContainerRef.current.clientWidth,
                        height: newHeight,
                    })
                }
            }
            window.addEventListener("resize", handleResize)

            return () => {
                chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleRangeChange)
                window.removeEventListener("resize", handleResize)
                // Clean up markers primitive
                if (markersInstance.current) {
                    try {
                        markersInstance.current.detach()
                    } catch (e) {
                        // Ignore
                    }
                    markersInstance.current = null
                }
            }
        })
    }, [isFullscreen, requestOverlayProjectionRefresh, showMainTimeScale, syncIndicatorPanesToMainRange])

    // Update chart data
    useEffect(() => {
        if (!chartReady || candles.length === 0 || !seriesInstance.current) return
        const updateStart = performance.now()

        // Dynamic import for v5 markers API
        import("lightweight-charts").then(({ createSeriesMarkers }) => {
            if (!seriesInstance.current) return

            const rawCandleData = candles.map((item) => ({
                time: formatTime(item.time),
                open: item.open,
                high: item.high,
                low: item.low,
                close: item.close,
            }))

            // Deduplicate and sort data
            const candleData = deduplicateByTime(rawCandleData)
            const firstCandle = candleData[0]
            const lastCandle = candleData[candleData.length - 1]
            const nextCandleHash = firstCandle && lastCandle
                ? `${candleData.length}:${firstCandle.time}:${firstCandle.open}:${firstCandle.high}:${firstCandle.low}:${firstCandle.close}:${lastCandle.time}:${lastCandle.open}:${lastCandle.high}:${lastCandle.low}:${lastCandle.close}`
                : "0"

            try {
                if (nextCandleHash !== lastCandleHashRef.current) {
                    seriesInstance.current.setData(candleData)
                    lastCandleHashRef.current = nextCandleHash
                }

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
                                    } catch (e) {
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

                // Only fit content on initial load or when symbol/timeframe changes
                // This preserves user's zoom/pan position during data refreshes
                const symbolChanged = lastSymbolRef.current !== symbol
                const timeframeChanged = lastTimeframeRef.current !== timeframe

                if (isInitialLoadRef.current || symbolChanged || timeframeChanged) {
                    chartInstance.current?.timeScale().fitContent()
                    isInitialLoadRef.current = false
                    lastSymbolRef.current = symbol
                    lastTimeframeRef.current = timeframe
                }
                syncIndicatorPanesToMainRange()
                requestOverlayProjectionRefresh()
                logPerf("main-chart-update", {
                    ms: Number((performance.now() - updateStart).toFixed(2)),
                    candles: candleData.length,
                    workerRequestId: workerComputationState.requestId,
                    comboSignals: workerComputationState.overlays.combo.length,
                    hunterSignals: workerComputationState.overlays.hunter.length,
                })
            } catch (e) {
                console.error("Chart update error:", e)
            }
        })
    }, [candles, signals, showSignals, activeIndicators, chartReady, symbol, timeframe, candlesSignature, signalsSignature, markerIndicatorSignature, activeTool, requestOverlayProjectionRefresh, workerComputationState.requestId, workerOverlaySignature, workerComputationState.overlays.combo, workerComputationState.overlays.hunter, logPerf, syncIndicatorPanesToMainRange])

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

    const projectedDrawings = useMemo(() => {
        const stepSeconds = getTimeframeStepSeconds(timeframe)

        const projectRuler = (ruler: RulerDrawing) => {
            const start = projectAnchorToScreen(ruler.start)
            const end = projectAnchorToScreen(ruler.end)
            if (!start || !end) return null

            const priceDiff = ruler.end.price - ruler.start.price
            const pct = ruler.start.price !== 0 ? (priceDiff / ruler.start.price) * 100 : 0
            const bars = Math.max(1, Math.round(Math.abs(ruler.end.time - ruler.start.time) / stepSeconds))
            const midpoint = {
                x: (start.x + end.x) / 2,
                y: (start.y + end.y) / 2,
            }

            return {
                id: ruler.id,
                start,
                end,
                label: `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%  ${priceDiff >= 0 ? "+" : ""}${priceDiff.toFixed(2)} (${bars} bar)`,
                midpoint,
            }
        }

        const rulerItems = rulerDrawings
            .map(projectRuler)
            .filter((item): item is NonNullable<ReturnType<typeof projectRuler>> => item !== null)

        let rulerDraft: ReturnType<typeof projectRuler> | null = null
        if (rulerDraftStart && rulerDraftEnd) {
            rulerDraft = projectRuler({
                id: "draft-ruler",
                start: rulerDraftStart,
                end: rulerDraftEnd,
            })
        }

        const pencilItems = pencilDrawings
            .map((stroke) => {
                const points = stroke.points
                    .map((point) => projectAnchorToScreen(point))
                    .filter((point): point is { x: number, y: number } => point !== null)
                if (points.length < 2) return null
                return { id: stroke.id, points }
            })
            .filter((item): item is { id: string, points: { x: number, y: number }[] } => item !== null)

        const activePencil = (activePencilPoints || [])
            .map((point) => projectAnchorToScreen(point))
            .filter((point): point is { x: number, y: number } => point !== null)

        const textItems = textDrawings
            .map((drawing) => {
                const point = projectAnchorToScreen(drawing.point)
                if (!point) return null
                return {
                    id: drawing.id,
                    point,
                    text: drawing.text,
                }
            })
            .filter((item): item is { id: string, point: { x: number, y: number }, text: string } => item !== null)

        return {
            rulerItems,
            rulerDraft,
            pencilItems,
            activePencil,
            textItems,
        }
    }, [
        timeframe,
        projectAnchorToScreen,
        rulerDrawings,
        rulerDraftStart,
        rulerDraftEnd,
        pencilDrawings,
        activePencilPoints,
        textDrawings,
        overlayRenderNonce,
    ])

    const activeWatchlist = useMemo(
        () => watchlists.find((watchlist) => watchlist.id === activeWatchlistId) || watchlists[0] || null,
        [watchlists, activeWatchlistId]
    )

    const cryptoQuoteMap = useMemo(() => {
        const map = new Map<string, { priceText: string; change: number }>()
        for (const [sym, payload] of Object.entries(cryptoPrices)) {
            map.set(sym, {
                priceText: payload?.price ? payload.price.toFixed(2) : "---",
                change: payload?.change ?? 0,
            })
        }
        return map
    }, [cryptoPrices])

    const bistQuoteMap = useMemo(() => {
        const map = new Map<string, { priceText: string; change: number }>()
        for (const ticker of bistTickers || []) {
            const quote = {
                priceText: ticker.price?.toFixed(2) || "---",
                change: ticker.changePercent || 0,
            }
            map.set(ticker.symbol.toUpperCase(), quote)
            map.set(ticker.name.toUpperCase(), quote)
        }
        for (const quote of activeWatchlistBistQuotes || []) {
            const raw = (quote.symbol || "").toUpperCase()
            const normalized = raw.endsWith(".IS") ? raw.slice(0, -3) : raw
            const payload = {
                priceText: typeof quote.regularMarketPrice === "number"
                    ? quote.regularMarketPrice.toFixed(2)
                    : "---",
                change: quote.regularMarketChangePercent || 0,
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

    const activeWatchlistQuotes = useMemo(() => {
        return activeWatchlistSymbolRows
            .map((row) => {
                const quote =
                    row.marketType === "Kripto"
                        ? cryptoQuoteMap.get(row.rawSymbol)
                        : bistQuoteMap.get(row.rawSymbol)
                return {
                    ...row,
                    priceText: quote?.priceText ?? "---",
                    change: quote?.change ?? 0,
                    hasQuote: !!quote,
                }
            })
            .filter((row) => row.hasQuote)
    }, [activeWatchlistSymbolRows, cryptoQuoteMap, bistQuoteMap])

    const watchlistChangeSnapshot = useMemo(() => {
        if (activeWatchlistQuotes.length === 0) return null
        let strongest = activeWatchlistQuotes[0]
        let weakest = activeWatchlistQuotes[0]
        let sum = 0
        for (const row of activeWatchlistQuotes) {
            sum += row.change
            if (row.change > strongest.change) strongest = row
            if (row.change < weakest.change) weakest = row
        }
        return {
            average: sum / activeWatchlistQuotes.length,
            strongest,
            weakest,
            quotedCount: activeWatchlistQuotes.length,
        }
    }, [activeWatchlistQuotes])

    const utilityCalendarItems = useMemo(
        () => buildUtilityCalendarItems(utilityCalendarRaw),
        [utilityCalendarRaw]
    )

    const utilityCalendarUpcoming = useMemo(() => {
        const nowKey = new Date().toISOString()
        const upcoming = utilityCalendarItems.filter((item) => item.orderKey >= nowKey)
        return (upcoming.length > 0 ? upcoming : utilityCalendarItems).slice(0, 8)
    }, [utilityCalendarItems])

    const utilityCalendarUpdatedLabel = useMemo(() => {
        if (!utilityCalendarUpdatedAt) return "--"
        return new Date(utilityCalendarUpdatedAt).toLocaleString("tr-TR")
    }, [utilityCalendarUpdatedAt])

    const watchlistSignalFeed = useMemo(
        () => buildWatchlistSignalFeed(utilityWatchlistSignalsRaw, activeWatchlistSymbolRows),
        [utilityWatchlistSignalsRaw, activeWatchlistSymbolRows]
    )

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
        if (!activeWatchlist) return
        const value = window.prompt("Sembol girin (ör: BTCUSDT, ETH/USD veya THYAO)")
        if (!value) return
        const parsed = parseSymbolInput(value)
        if (!parsed) {
            showWatchlistToast("Geçersiz sembol. Binance veya BIST sembolü deneyin.")
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
    }, [activeWatchlist, parseSymbolInput, showWatchlistToast, updateActiveWatchlist])

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
        const nextName = window.prompt("Yeni liste adı", activeWatchlist.name)
        if (!nextName || !nextName.trim()) return
        const normalizedName = nextName.trim()
        updateActiveWatchlist((watchlist) => ({ ...watchlist, name: normalizedName }))
        setWatchlistAlarmRules((prev) =>
            prev.map((rule) =>
                rule.watchlistId === activeWatchlist.id
                    ? { ...rule, watchlistName: normalizedName, updatedAt: new Date().toISOString() }
                    : rule
            )
        )
        setShowWatchlistMenu(false)
        showWatchlistToast("Liste adı güncellendi.")
    }, [activeWatchlist, showWatchlistToast, updateActiveWatchlist])

    const handleDeleteWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        if (watchlists.length <= 1) {
            showWatchlistToast("En az bir liste kalmalı.")
            return
        }
        const approved = window.confirm(`${activeWatchlist.name} listesini silmek istiyor musunuz?`)
        if (!approved) return

        const fallback = watchlists.find((watchlist) => watchlist.id !== activeWatchlist.id)
        setWatchlists((prev) => prev.filter((watchlist) => watchlist.id !== activeWatchlist.id))
        setWatchlistAlarmRules((prev) => prev.filter((rule) => rule.watchlistId !== activeWatchlist.id))
        if (fallback) {
            setActiveWatchlistId(fallback.id)
        }
        setShowWatchlistMenu(false)
        showWatchlistToast("Liste silindi.")
    }, [activeWatchlist, watchlists, showWatchlistToast])

    const handleClearWatchlist = useCallback(() => {
        if (!activeWatchlist) return
        const approved = window.confirm(`${activeWatchlist.name} listesini temizlemek istiyor musunuz?`)
        if (!approved) return
        updateActiveWatchlist((watchlist) => ({ ...watchlist, rows: [] }))
        setShowWatchlistMenu(false)
        showWatchlistToast("Liste temizlendi.")
    }, [activeWatchlist, showWatchlistToast, updateActiveWatchlist])

    const handleCreateWatchlist = useCallback(() => {
        const listName = window.prompt("Yeni liste adı")
        if (!listName || !listName.trim()) return
        const watchlist: WatchlistModel = {
            id: makeWatchlistId(listName),
            name: listName.trim(),
            alarmsEnabled: false,
            notes: "",
            rows: [],
        }
        setWatchlists((prev) => [watchlist, ...prev])
        setActiveWatchlistId(watchlist.id)
        setShowWatchlistMenu(false)
        setShowWatchlistSwitcher(false)
        showWatchlistToast("Yeni liste oluşturuldu.")
    }, [showWatchlistToast])

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
            window.prompt("Panoya kopyalayın", payload)
        }
        setShowWatchlistMenu(false)
    }, [activeWatchlist, showWatchlistToast])

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
            window.prompt("Notlari kopyalayin", text)
        }
    }, [activeWatchlist, showWatchlistToast])

    const handleClearWatchlistNotes = useCallback(() => {
        if (!activeWatchlist) return
        const approved = window.confirm(`${activeWatchlist.name} notlari temizlensin mi?`)
        if (!approved) return
        updateActiveWatchlist((watchlist) => ({ ...watchlist, notes: "" }))
        showWatchlistToast("Notlar temizlendi.")
    }, [activeWatchlist, showWatchlistToast, updateActiveWatchlist])

    const handleAlarmThresholdDraftChange = useCallback(
        (key: keyof AlarmThresholds, rawValue: string) => {
            const parsed = Number(rawValue)
            if (!Number.isFinite(parsed)) return
            setAlarmThresholdDraft((prev) => ({ ...prev, [key]: parsed }))
        },
        []
    )

    const handleCreateWatchlistAlarmRule = useCallback(() => {
        if (!activeWatchlist) return
        const nextRule = createWatchlistAlarmRule(
            activeWatchlist.id,
            activeWatchlist.name,
            alarmIndicatorDraft,
            alarmTimeframeDraft,
            alarmThresholdDraft
        )
        setWatchlistAlarmRules((prev) => [nextRule, ...prev])
        showWatchlistToast(`${activeWatchlist.name} için yeni alarm eklendi.`)
    }, [
        activeWatchlist,
        alarmIndicatorDraft,
        alarmTimeframeDraft,
        alarmThresholdDraft,
        showWatchlistToast,
    ])

    const handleToggleAlarmRule = useCallback((ruleId: string) => {
        setWatchlistAlarmRules((prev) =>
            prev.map((rule) =>
                rule.id === ruleId
                    ? { ...rule, enabled: !rule.enabled, updatedAt: new Date().toISOString() }
                    : rule
            )
        )
    }, [])

    const handleRemoveAlarmRule = useCallback((ruleId: string) => {
        setWatchlistAlarmRules((prev) => prev.filter((rule) => rule.id !== ruleId))
    }, [])

    const handleClearChartDrawings = useCallback(() => {
        setRulerDrawings([])
        setPencilDrawings([])
        setTextDrawings([])
        setRulerDraftStart(null)
        setRulerDraftEnd(null)
        setActivePencilPoints(null)
        rulerDraftStartRef.current = null
        isPointerDrawingRef.current = false
        setActiveTool("none")
        requestOverlayProjectionRefresh()
        showWatchlistToast("Cizimler temizlendi.")
    }, [requestOverlayProjectionRefresh, showWatchlistToast])

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
                "relative flex h-full min-h-0 overflow-hidden rounded-sm bg-background glass-panel-intense",
                isFullscreen ? "fixed inset-0 z-50 rounded-none" : ""
            )}
        >
            {/* Main Chart Area */}
            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
                {/* Header */}
                <div className="flex items-center justify-between px-4 py-3 border-b border-border/30">
                    {/* Symbol Selector */}
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <button
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
                                <div className="absolute top-full left-0 mt-2 w-96 glass-panel z-50 overflow-hidden">
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
                                {marketType === "Kripto" ? "$" : "₺"}
                                {livePrice.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: marketType === "Kripto" ? 4 : 2 })}
                            </span>
                            <div className={cn("flex items-center gap-1.5 text-sm", isPositive ? "text-profit" : "text-loss")}>
                                {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                                <span className="font-medium mono-numbers">{isPositive ? "+" : ""}{priceChange.toFixed(2)}</span>
                                <span className="mono-numbers">({isPositive ? "+" : ""}{priceChangePercent.toFixed(2)}%)</span>
                            </div>
                        </div>
                    </div>

                    {/* Timeframe & Controls */}
                    <div className="flex items-center gap-3">
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
                            <IconButton
                                onClick={() => setActiveTool(activeTool === "ruler" ? "none" : "ruler")}
                                className={cn("p-2 rounded-sm transition-all", activeTool === "ruler" ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                label="Ölçüm cetvelini aç"
                            >
                                <Ruler className="h-4 w-4" />
                            </IconButton>
                            <IconButton
                                onClick={() => setActiveTool(activeTool === "pencil" ? "none" : "pencil")}
                                className={cn("p-2 rounded-sm transition-all", activeTool === "pencil" ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                label="Çizim aracını aç"
                            >
                                <Pencil className="h-4 w-4" />
                            </IconButton>
                            <IconButton
                                onClick={() => setActiveTool(activeTool === "text" ? "none" : "text")}
                                className={cn("p-2 rounded-sm transition-all", activeTool === "text" ? "text-primary bg-primary/10" : "text-muted-foreground hover:text-foreground hover:bg-muted/50")}
                                label="Grafiğe metin ekleme aracını aç"
                            >
                                <Type className="h-4 w-4" />
                            </IconButton>
                        </div>

                        <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 rounded-sm text-xs">
                            <Zap className="h-3 w-3 text-primary animate-pulse" />
                            <span className="text-muted-foreground">{dataSource}</span>
                        </div>

                        <IconButton
                            onClick={() => setShowRightPanel(!showRightPanel)}
                            className={cn("p-2 rounded-sm transition-all bg-muted/30 hover:bg-muted/50", showRightPanel && "text-primary")}
                            label={showRightPanel ? "Sağ paneli gizle" : "Sağ paneli göster"}
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
                    <div className="flex items-center gap-6 px-4 py-2 border-b border-border/30 bg-muted/10">
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
                        </div>
                        <div className="ml-auto flex items-center gap-2 text-xs text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>{crosshairData ? crosshairData.time : 'Son Mum'}</span>
                        </div>
                    </div>
                )}

                {/* Active Tool Info */}
                {activeTool !== 'none' && (
                    <div className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary text-sm">
                        {activeTool === 'ruler' && "Ölçüm modu aktif. Grafikte iki nokta seçin."}
                        {activeTool === 'pencil' && "Çizim modu aktif. Grafikte serbest çizim yapabilirsiniz."}
                        {activeTool === 'text' && "Metin modu aktif. Grafikte bir noktaya tıklayarak metin ekleyin."}
                        <IconButton onClick={() => setActiveTool("none")} className="ml-auto hover:text-white" label="Aktif aracı kapat">
                            <X className="h-4 w-4" />
                        </IconButton>
                    </div>
                )}

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

                    {isLoading && (
                        <div className="absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10 pointer-events-none">
                            <div className="flex flex-col items-center gap-3">
                                <div className="w-10 h-10 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                                <span className="text-sm text-muted-foreground">Grafik yükleniyor...</span>
                            </div>
                        </div>
                    )}
                    <div
                        ref={chartContainerRef}
                        className="w-full h-full cursor-crosshair"
                        style={{ touchAction: 'none' }}
                    />

                    <div
                        className={cn(
                            "absolute inset-0 z-[12]",
                            activeTool === "none" ? "pointer-events-none" : "pointer-events-auto cursor-crosshair"
                        )}
                        onMouseDown={handleDrawingMouseDown}
                        onMouseMove={handleDrawingMouseMove}
                        onMouseUp={handleDrawingMouseUp}
                        onMouseLeave={handleDrawingMouseUp}
                    >
                        <svg className="h-full w-full">
                            {projectedDrawings.rulerItems.map((ruler) => (
                                <g key={ruler.id}>
                                    <line x1={ruler.start.x} y1={ruler.start.y} x2={ruler.end.x} y2={ruler.end.y} stroke="#9ca3af" strokeWidth={1.5} />
                                    <circle cx={ruler.start.x} cy={ruler.start.y} r={3} fill="#9ca3af" />
                                    <circle cx={ruler.end.x} cy={ruler.end.y} r={3} fill="#9ca3af" />
                                    <rect x={ruler.midpoint.x - 88} y={ruler.midpoint.y - 24} width={176} height={18} rx={4} fill="rgba(17,24,39,0.85)" />
                                    <text x={ruler.midpoint.x} y={ruler.midpoint.y - 11} fill="#e5e7eb" fontSize={11} textAnchor="middle">
                                        {ruler.label}
                                    </text>
                                </g>
                            ))}

                            {projectedDrawings.rulerDraft && (
                                <g>
                                    <line
                                        x1={projectedDrawings.rulerDraft.start.x}
                                        y1={projectedDrawings.rulerDraft.start.y}
                                        x2={projectedDrawings.rulerDraft.end.x}
                                        y2={projectedDrawings.rulerDraft.end.y}
                                        stroke="#60a5fa"
                                        strokeWidth={1.5}
                                        strokeDasharray="4 3"
                                    />
                                    <rect
                                        x={projectedDrawings.rulerDraft.midpoint.x - 88}
                                        y={projectedDrawings.rulerDraft.midpoint.y - 24}
                                        width={176}
                                        height={18}
                                        rx={4}
                                        fill="rgba(30,58,138,0.82)"
                                    />
                                    <text
                                        x={projectedDrawings.rulerDraft.midpoint.x}
                                        y={projectedDrawings.rulerDraft.midpoint.y - 11}
                                        fill="#dbeafe"
                                        fontSize={11}
                                        textAnchor="middle"
                                    >
                                        {projectedDrawings.rulerDraft.label}
                                    </text>
                                </g>
                            )}

                            {projectedDrawings.pencilItems.map((stroke) => (
                                <polyline
                                    key={stroke.id}
                                    points={stroke.points.map((point) => `${point.x},${point.y}`).join(" ")}
                                    fill="none"
                                    stroke="#fbbf24"
                                    strokeWidth={1.6}
                                    strokeLinejoin="round"
                                    strokeLinecap="round"
                                />
                            ))}

                            {projectedDrawings.activePencil.length > 1 && (
                                <polyline
                                    points={projectedDrawings.activePencil.map((point) => `${point.x},${point.y}`).join(" ")}
                                    fill="none"
                                    stroke="#fcd34d"
                                    strokeWidth={1.6}
                                    strokeLinejoin="round"
                                    strokeLinecap="round"
                                />
                            )}

                            {projectedDrawings.textItems.map((item) => (
                                <g key={item.id}>
                                    <rect
                                        x={item.point.x - 4}
                                        y={item.point.y - 17}
                                        width={Math.max(52, item.text.length * 6.2)}
                                        height={18}
                                        rx={4}
                                        fill="rgba(31,41,55,0.88)"
                                    />
                                    <text x={item.point.x + 2} y={item.point.y - 5} fill="#e5e7eb" fontSize={11}>
                                        {item.text}
                                    </text>
                                </g>
                            ))}
                        </svg>
                    </div>
                </div>

                {/* Indicator Panels */}
                {visiblePanelIndicators.map((ind, index) => (
                    <IndicatorPane
                        key={ind.id}
                        indicator={ind}
                        candles={candles}
                        precomputedSeries={workerComputationState.panes[ind.id] || null}
                        onRemove={() => {
                            removeIndicator(ind.id)
                            indicatorChartsRef.current.delete(ind.id)
                        }}
                        mainChartRef={chartInstance}
                        hoveredUnixTime={hoveredUnixTime}
                        showTimeScale={index === visiblePanelIndicators.length - 1}
                        onChartReady={registerIndicatorChart}
                    />
                ))}

                {/* Status Bar */}
                <div className="flex items-center justify-between px-4 py-2 border-t border-border/30 text-xs text-muted-foreground">
                    <div className="flex items-center gap-4">
                        <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-profit animate-pulse" />Canlı</span>
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
                <div className="flex w-[300px] border-l border-border/30 bg-surface text-foreground xl:w-[320px]">
                    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
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
                                        <button
                                            onClick={handleToggleWatchlistAlerts}
                                            className={cn(
                                                "h-5 w-10 rounded-full p-0.5 transition-colors",
                                                activeWatchlist?.alarmsEnabled ? "bg-primary" : "bg-raised"
                                            )}
                                            aria-label="Liste alarmlarını aç veya kapat"
                                            aria-pressed={Boolean(activeWatchlist?.alarmsEnabled)}
                                        >
                                            <span
                                                className={cn(
                                                    "block h-4 w-4 rounded-full bg-white transition-transform",
                                                    activeWatchlist?.alarmsEnabled ? "translate-x-5" : "translate-x-0"
                                                )}
                                            />
                                        </button>
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
                                const change = quote?.change ?? 0
                                const priceText = quote?.priceText ?? "---"

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
                                            title={`${row.rawSymbol} (${row.marketType})`}
                                        >
                                            {displaySymbol}
                                        </button>
                                        <span className="text-right text-sm font-mono tabular-nums">{priceText}</span>
                                        <span className={cn("text-right text-sm font-mono tabular-nums", change >= 0 ? "text-profit" : "text-loss")}>
                                            {change >= 0 ? "+" : ""}
                                            {change.toFixed(2)}%
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

                        {watchlistNotice && (
                            <div className="border-t border-border px-3 py-2 text-xs text-primary">
                                {watchlistNotice}
                            </div>
                        )}

                        {activeUtilityPanel && (
                            <div className="border-t border-border px-3 py-3 text-xs">
                                {activeUtilityPanel === "alerts" && (
                                    <div className="space-y-3">
                                        <div className="flex items-center justify-between">
                                            <span className="text-muted-foreground">Liste alarmlari</span>
                                            <button onClick={handleToggleWatchlistAlerts} className={cn("rounded px-2 py-1 text-[11px]", activeWatchlist?.alarmsEnabled ? "bg-primary text-primary-foreground" : "bg-raised text-foreground")}>
                                                {activeWatchlist?.alarmsEnabled ? "Acik" : "Kapali"}
                                            </button>
                                        </div>
                                        <div className="rounded border border-border/50 bg-base p-2.5">
                                            <div className="grid grid-cols-2 gap-2">
                                                <label className="flex flex-col gap-1">
                                                    <span className="text-[10px] uppercase text-muted-foreground">Indikator</span>
                                                    <Select
                                                        value={alarmIndicatorDraft}
                                                        onChange={(e) => setAlarmIndicatorDraft(e.target.value as AlarmIndicator)}
                                                        className="h-7 rounded border-border bg-background py-1 text-xs"
                                                    >
                                                        {ALARM_INDICATOR_OPTIONS.map((option) => (
                                                            <option key={option.value} value={option.value}>
                                                                {option.label}
                                                            </option>
                                                        ))}
                                                    </Select>
                                                </label>
                                                <label className="flex flex-col gap-1">
                                                    <span className="text-[10px] uppercase text-muted-foreground">Periyot</span>
                                                    <Select
                                                        value={alarmTimeframeDraft}
                                                        onChange={(e) => setAlarmTimeframeDraft(e.target.value as AlarmTimeframe)}
                                                        className="h-7 rounded border-border bg-background py-1 text-xs"
                                                    >
                                                        {ALARM_TIMEFRAME_OPTIONS.map((option) => (
                                                            <option key={option.value} value={option.value}>
                                                                {option.label}
                                                            </option>
                                                        ))}
                                                    </Select>
                                                </label>
                                            </div>

                                            {(alarmIndicatorDraft === "rsi" || alarmIndicatorDraft === "wr") && (
                                                <div className="mt-2 grid grid-cols-2 gap-2">
                                                    <label className="flex flex-col gap-1">
                                                        <span className="text-[10px] uppercase text-muted-foreground">DIP esik</span>
                                                        <input
                                                            type="number"
                                                            value={alarmIndicatorDraft === "rsi" ? alarmThresholdDraft.rsiDipThreshold : alarmThresholdDraft.wrDipThreshold}
                                                            onChange={(e) =>
                                                                handleAlarmThresholdDraftChange(
                                                                    alarmIndicatorDraft === "rsi" ? "rsiDipThreshold" : "wrDipThreshold",
                                                                    e.target.value
                                                                )
                                                            }
                                                            className="rounded border border-border bg-background px-2 py-1 text-xs"
                                                        />
                                                    </label>
                                                    <label className="flex flex-col gap-1">
                                                        <span className="text-[10px] uppercase text-muted-foreground">TEPE esik</span>
                                                        <input
                                                            type="number"
                                                            value={alarmIndicatorDraft === "rsi" ? alarmThresholdDraft.rsiTopThreshold : alarmThresholdDraft.wrTopThreshold}
                                                            onChange={(e) =>
                                                                handleAlarmThresholdDraftChange(
                                                                    alarmIndicatorDraft === "rsi" ? "rsiTopThreshold" : "wrTopThreshold",
                                                                    e.target.value
                                                                )
                                                            }
                                                            className="rounded border border-border bg-background px-2 py-1 text-xs"
                                                        />
                                                    </label>
                                                </div>
                                            )}

                                            {(alarmIndicatorDraft === "combo" || alarmIndicatorDraft === "hunter") && (
                                                <div className="mt-2 grid grid-cols-2 gap-2">
                                                    <label className="flex flex-col gap-1">
                                                        <span className="text-[10px] uppercase text-muted-foreground">DIP skor</span>
                                                        <input
                                                            type="number"
                                                            value={alarmIndicatorDraft === "combo" ? alarmThresholdDraft.comboDipThreshold : alarmThresholdDraft.hunterDipThreshold}
                                                            onChange={(e) =>
                                                                handleAlarmThresholdDraftChange(
                                                                    alarmIndicatorDraft === "combo" ? "comboDipThreshold" : "hunterDipThreshold",
                                                                    e.target.value
                                                                )
                                                            }
                                                            className="rounded border border-border bg-background px-2 py-1 text-xs"
                                                        />
                                                    </label>
                                                    <label className="flex flex-col gap-1">
                                                        <span className="text-[10px] uppercase text-muted-foreground">TEPE skor</span>
                                                        <input
                                                            type="number"
                                                            value={alarmIndicatorDraft === "combo" ? alarmThresholdDraft.comboTopThreshold : alarmThresholdDraft.hunterTopThreshold}
                                                            onChange={(e) =>
                                                                handleAlarmThresholdDraftChange(
                                                                    alarmIndicatorDraft === "combo" ? "comboTopThreshold" : "hunterTopThreshold",
                                                                    e.target.value
                                                                )
                                                            }
                                                            className="rounded border border-border bg-background px-2 py-1 text-xs"
                                                        />
                                                    </label>
                                                </div>
                                            )}

                                            <button
                                                onClick={handleCreateWatchlistAlarmRule}
                                                className="mt-2 w-full rounded bg-primary px-2 py-1.5 text-xs font-medium text-primary-foreground hover:opacity-90"
                                            >
                                                Alarm ekle
                                            </button>
                                        </div>

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

                                        <Link href="/alarms" className="flex items-center justify-between rounded border border-border/50 px-2 py-1.5 text-muted-foreground hover:bg-raised">
                                            <span>/alarms sayfasinda aktif tetikleri izle</span>
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
                                            <span>Canli takvim</span>
                                            <button
                                                onClick={() => refetchUtilityCalendar()}
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
                                {activeUtilityPanel === "news" && (
                                    <div className="space-y-2 text-muted-foreground">
                                        <div className="flex items-center justify-between">
                                            <span>Canli akis</span>
                                            <button
                                                onClick={() => refetchUtilitySignals()}
                                                className={cn(
                                                    "rounded border border-border px-2 py-0.5 text-[10px] hover:bg-raised",
                                                    isUtilitySignalsFetching && "opacity-70"
                                                )}
                                            >
                                                {isUtilitySignalsFetching ? "Yenileniyor" : "Yenile"}
                                            </button>
                                        </div>
                                        {watchlistChangeSnapshot ? (
                                            <div className="rounded border border-border/40 bg-base p-2 text-[11px]">
                                                <div>Ortalama degisim: {watchlistChangeSnapshot.average >= 0 ? "+" : ""}{watchlistChangeSnapshot.average.toFixed(2)}%</div>
                                                <div>Pozitif lider: {watchlistChangeSnapshot.strongest.rawSymbol} ({watchlistChangeSnapshot.strongest.change >= 0 ? "+" : ""}{watchlistChangeSnapshot.strongest.change.toFixed(2)}%)</div>
                                                <div>Negatif lider: {watchlistChangeSnapshot.weakest.rawSymbol} ({watchlistChangeSnapshot.weakest.change >= 0 ? "+" : ""}{watchlistChangeSnapshot.weakest.change.toFixed(2)}%)</div>
                                                <div>Kotasyon gelen sembol: {watchlistChangeSnapshot.quotedCount}</div>
                                            </div>
                                        ) : (
                                            <div className="text-[11px]">Canli quote bekleniyor.</div>
                                        )}

                                        <div className="max-h-52 space-y-1 overflow-y-auto rounded border border-border/40 bg-base p-2">
                                            {watchlistSignalFeed.length === 0 && (
                                                <div className="text-[11px] text-muted-foreground">
                                                    Bu liste sembolleri icin yeni sinyal akisi yok.
                                                </div>
                                            )}
                                            {watchlistSignalFeed.map((item) => (
                                                <Link
                                                    key={item.id}
                                                    href={`/chart?symbol=${encodeURIComponent(item.symbol)}&market=${encodeURIComponent(item.marketType)}`}
                                                    className="block rounded border border-border/50 px-2 py-1 hover:bg-raised"
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <span className="font-medium text-foreground">{item.symbol}</span>
                                                        <span className={cn("rounded px-1.5 py-0.5 text-[10px]", item.signalType === "AL" ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss")}>
                                                            {item.signalType}
                                                        </span>
                                                    </div>
                                                    <div className="mt-0.5 text-[10px] text-muted-foreground">
                                                        {item.strategy} • {item.timeframe} • {item.specialTag} • {formatSignalTimestamp(item.createdAt)}
                                                    </div>
                                                </Link>
                                            ))}
                                        </div>
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
                                                onClick={handleClearChartDrawings}
                                                className="rounded border border-border px-2 py-1 text-[11px] hover:bg-raised"
                                            >
                                                Cizimleri temizle
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
                                            <div>Haberler: Liste sembollerine ait son sinyal akislarini gosterir.</div>
                                            <div>Yerlesim: Panel ve grafik duzenini hizli sekilde degistirir.</div>
                                        </div>
                                        <div className="grid grid-cols-2 gap-1.5">
                                            <Link href="/alarms" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Alarm merkezi
                                            </Link>
                                            <Link href="/calendar" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Takvim sayfasi
                                            </Link>
                                            <Link href="/signals" className="rounded border border-border px-2 py-1 text-center text-[11px] hover:bg-raised">
                                                Sinyal akisi
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
        </div>
    )
}

// ==================== INDICATOR PANE COMPONENT ====================

interface IndicatorPaneProps {
    indicator: ActiveIndicator
    candles: Candle[]
    precomputedSeries: WorkerPaneSeriesResult | null
    onRemove: () => void
    mainChartRef: React.MutableRefObject<any>
    hoveredUnixTime: number | null
    showTimeScale: boolean
    onChartReady?: (indicatorId: string, chart: any) => void
}

function IndicatorPane({
    indicator,
    candles,
    precomputedSeries,
    onRemove,
    mainChartRef,
    hoveredUnixTime,
    showTimeScale,
    onChartReady,
}: IndicatorPaneProps) {
    const containerRef = useRef<HTMLDivElement>(null)
    const chartRef = useRef<any>(null)
    const primarySeriesRef = useRef<any>(null)
    const primarySeriesPointsRef = useRef<Array<{ timeKey: number, rawTime: string | number, value: number }>>([])
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
                } catch (e) {
                    // Chart already disposed
                }
                chartRef.current = null
            }

            const chart = createChart(containerRef.current, {
                layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: chartColors.text, fontSize: 10 },
                grid: { vertLines: { color: chartColors.grid }, horzLines: { color: chartColors.grid } },
                width: containerRef.current.clientWidth,
                height: paneHeightRef.current,
                rightPriceScale: {
                    borderColor: chartColors.grid,
                    minimumWidth: 64,
                    // Keep indicator labels away from pane edges so they don't collide with main chart labels.
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
                },
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
            let primaryLine: Array<{ time: string | number, value: number }> = []

            const setPrimarySeriesPoints = (line: Array<{ time: string | number, value: number }>) => {
                primaryLine = line
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

            const alignLineToTimeline = (line: Array<{ time: string | number, value: number }>) => {
                if (candleTimeline.length === 0) return line as Array<{ time: string | number } | { time: string | number, value: number }>
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

            const alignHistogramToTimeline = (histogram: Array<{ time: string | number, value: number, color: string }>) => {
                if (candleTimeline.length === 0) return histogram as Array<{ time: string | number } | { time: string | number, value: number, color: string }>
                const valueByTime = new Map<number, { value: number, color: string }>()
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
                let lineData: Array<{ time: string | number, value: number }> = []
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

                let macdLine: Array<{ time: string | number, value: number }> = []
                let signalLine: Array<{ time: string | number, value: number }> = []
                let histogram: Array<{ time: string | number, value: number, color: string }> = []

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
                let lineData: Array<{ time: string | number, value: number }> = []
                if (precomputedSeries?.kind === "line") {
                    lineData = deduplicateByTime(
                        precomputedSeries.line.map((point) => ({ time: formatTime(point.time), value: point.value }))
                    )
                }
                series.setData(alignLineToTimeline(lineData) as any)
                setPrimarySeriesPoints(lineData)
            } else if (indicator.id === "cci") {
                series = chart.addSeries(LineSeries, { color: chartColors.indicators.cci, lineWidth: 2 })
                let lineData: Array<{ time: string | number, value: number }> = []
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

            // Sync time scale with main chart (with safety checks)
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
                } catch (e) {
                    // Chart disposed or not ready
                }
            }

            // Subscribe to main chart's visible range changes
            let mainTimeScale: any = null

            if (mainChartRef.current) {
                try {
                    mainTimeScale = mainChartRef.current.timeScale()
                    mainTimeScale.subscribeVisibleLogicalRangeChange(syncWithMain)

                    // Initial sync
                    syncWithMain()
                } catch (e) {
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
                    } catch (e) {
                        // Chart disposed
                    }
                }
            }
            window.addEventListener('resize', handleResize)

            // Cleanup function
            return () => {
                isDisposedRef.current = true
                window.removeEventListener('resize', handleResize)

                // Unsubscribe from events
                if (mainTimeScale) {
                    try { mainTimeScale.unsubscribeVisibleLogicalRangeChange(syncWithMain) } catch (e) { /* ignore */ }
                }

                // Remove chart
                if (chartRef.current) {
                    try {
                        chartRef.current.remove()
                    } catch (e) {
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
        } catch (e) {
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
                try { chartRef.current.clearCrosshairPosition() } catch (e) { /* ignore */ }
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
                } catch (e) {
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

export default AdvancedChartPage
