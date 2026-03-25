"use client"

import { useEffect, useMemo, useState, type ReactNode } from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertTriangle, Check, ListPlus, RefreshCw, Search, Settings2, Star, StarOff } from "lucide-react"
import {
  fetchMarketMetrics,
  fetchSpecialTagHealth,
  fetchLogs,
  fetchScanHistory,
  fetchSignals,
  type ApiSignal,
  type LogEntry,
  type ScanHistory,
  type ApiSpecialTagHealth,
} from "@/lib/api/client"
import { useBotHealth } from "@/lib/hooks/use-health"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { ActionDialog } from "@/components/ui/action-dialog"
import { useToast } from "@/components/ui/toast"
import { cn, getTimeAgo } from "@/lib/utils"

type MarketKind = "BIST" | "Kripto"
type MarketFilter = "ALL" | MarketKind
type StrategyFilter = "ALL" | "COMBO" | "HUNTER"
type SignalFilter = "ALL" | "AL" | "SAT"
type SortDirection = "asc" | "desc"
type ViewKey = "ozel" | "momentum" | "akim" | "risk"

type ColumnId =
  | "symbol"
  | "market"
  | "price"
  | "changePct"
  | "perf7d"
  | "perf30d"
  | "lastSignal"
  | "strategy"
  | "timeframe"
  | "rsi14"
  | "rsiFast"
  | "cci"
  | "macd"
  | "wr"
  | "roc"
  | "ult"
  | "bbp"
  | "psy"
  | "zScore"
  | "signals24h"
  | "signalsTotal"
  | "bias"
  | "score"
  | "lastSeen"

type NumericFilterColumnId =
  | "price"
  | "changePct"
  | "perf7d"
  | "perf30d"
  | "rsi14"
  | "rsiFast"
  | "cci"
  | "macd"
  | "wr"
  | "roc"
  | "ult"
  | "bbp"
  | "psy"
  | "zScore"
  | "signals24h"
  | "signalsTotal"
  | "bias"

type NumericFilterOperator = "gt" | "gte" | "lt" | "lte" | "eq" | "between"

interface NumericFilterRule {
  column: NumericFilterColumnId
  operator: NumericFilterOperator
  value: number
  valueTo: number | null
}

interface NumericColumnFilterInput {
  operator: NumericFilterOperator
  value: string
  valueTo: string
}

interface ScannerMetricTarget {
  key: string
  symbol: string
  marketType: MarketKind
}

interface MarketMetricSnapshot {
  latestPrice: number
  changePct: number | null
  perf7d: number | null
  perf30d: number | null
}

interface ScannerSignal {
  id: number
  symbol: string
  marketType: MarketKind
  strategy: "COMBO" | "HUNTER"
  signalType: "AL" | "SAT"
  timeframe: string
  score: string
  price: number
  createdAt: string
  details: Record<string, unknown> | null
}

interface ScreenerRow {
  key: string
  symbol: string
  marketType: MarketKind
  latestPrice: number
  changePct: number | null
  perf7d: number | null
  perf30d: number | null
  lastSignalType: "AL" | "SAT"
  lastStrategy: "COMBO" | "HUNTER"
  lastTimeframe: string
  lastScore: string
  lastSeenIso: string
  lastSeenTs: number
  buySignals: number
  sellSignals: number
  comboSignals: number
  hunterSignals: number
  totalSignals: number
  signals24h: number
  rsi14: number | null
  rsiFast: number | null
  cci: number | null
  macd: number | null
  wr: number | null
  roc: number | null
  ult: number | null
  bbp: number | null
  psy: number | null
  zScore: number | null
}

interface MutableScreenerRow {
  row: ScreenerRow
  timeline: Array<{ ts: number; price: number }>
}

interface WatchlistModel {
  id: string
  name: string
  symbols: string[]
}

interface ColumnMeta {
  label: string
  align: "left" | "right"
  sortValue: (row: ScreenerRow) => number | string
}

const EMPTY_SIGNALS: ScannerSignal[] = []
const EMPTY_SCANS: ScanHistory[] = []
const EMPTY_LOGS: LogEntry[] = []

const WATCHLIST_STORAGE_KEY = "rapot.scanner.watchlists.v2"
const WATCHLIST_ACTIVE_KEY = "rapot.scanner.watchlists.active.v2"
const PREF_STORAGE_KEY = "rapot.scanner.preferences.v2"

const COLUMN_ORDER: ColumnId[] = [
  "symbol",
  "market",
  "price",
  "changePct",
  "perf7d",
  "perf30d",
  "lastSignal",
  "strategy",
  "timeframe",
  "rsi14",
  "rsiFast",
  "cci",
  "macd",
  "wr",
  "roc",
  "ult",
  "bbp",
  "psy",
  "zScore",
  "signals24h",
  "signalsTotal",
  "bias",
  "score",
  "lastSeen",
]

const LOCKED_COLUMNS = new Set<ColumnId>(["symbol", "price"])

const COLUMN_META: Record<ColumnId, ColumnMeta> = {
  symbol: { label: "Sembol", align: "left", sortValue: (row) => row.symbol },
  market: { label: "Pazar", align: "left", sortValue: (row) => row.marketType },
  price: { label: "Fiyat", align: "right", sortValue: (row) => row.latestPrice },
  changePct: { label: "Degisim %", align: "right", sortValue: (row) => row.changePct ?? Number.NEGATIVE_INFINITY },
  perf7d: { label: "Perf 7G", align: "right", sortValue: (row) => row.perf7d ?? Number.NEGATIVE_INFINITY },
  perf30d: { label: "Perf 30G", align: "right", sortValue: (row) => row.perf30d ?? Number.NEGATIVE_INFINITY },
  lastSignal: { label: "Son Sinyal", align: "left", sortValue: (row) => row.lastSignalType },
  strategy: { label: "Strateji", align: "left", sortValue: (row) => row.lastStrategy },
  timeframe: { label: "Periyot", align: "left", sortValue: (row) => timeframeRank(row.lastTimeframe) },
  rsi14: { label: "RSI(14)", align: "right", sortValue: (row) => row.rsi14 ?? Number.NEGATIVE_INFINITY },
  rsiFast: { label: "RSI Fast", align: "right", sortValue: (row) => row.rsiFast ?? Number.NEGATIVE_INFINITY },
  cci: { label: "CCI", align: "right", sortValue: (row) => row.cci ?? Number.NEGATIVE_INFINITY },
  macd: { label: "MACD", align: "right", sortValue: (row) => row.macd ?? Number.NEGATIVE_INFINITY },
  wr: { label: "W%R", align: "right", sortValue: (row) => row.wr ?? Number.NEGATIVE_INFINITY },
  roc: { label: "ROC", align: "right", sortValue: (row) => row.roc ?? Number.NEGATIVE_INFINITY },
  ult: { label: "ULT", align: "right", sortValue: (row) => row.ult ?? Number.NEGATIVE_INFINITY },
  bbp: { label: "BB%", align: "right", sortValue: (row) => row.bbp ?? Number.NEGATIVE_INFINITY },
  psy: { label: "PSY", align: "right", sortValue: (row) => row.psy ?? Number.NEGATIVE_INFINITY },
  zScore: { label: "Z-Score", align: "right", sortValue: (row) => row.zScore ?? Number.NEGATIVE_INFINITY },
  signals24h: { label: "Sinyal 24s", align: "right", sortValue: (row) => row.signals24h },
  signalsTotal: { label: "Sinyal Toplam", align: "right", sortValue: (row) => row.totalSignals },
  bias: { label: "Bias", align: "right", sortValue: (row) => row.buySignals - row.sellSignals },
  score: { label: "Skor", align: "left", sortValue: (row) => row.lastScore },
  lastSeen: { label: "Son Guncelleme", align: "right", sortValue: (row) => row.lastSeenTs },
}

const COLUMN_HELP: Record<ColumnId, string> = {
  symbol: "Takip edilen enstruman kodu.",
  market: "Enstrumanin geldigi pazar (BIST veya Kripto).",
  price: "Secilen sembol icin son gorulen fiyat.",
  changePct: "Bir onceki kayda gore yuzdesel degisim.",
  perf7d: "Yaklasik 7 gunluk performans.",
  perf30d: "Yaklasik 30 gunluk performans.",
  lastSignal: "Botun son verdigi sinyal yonu.",
  strategy: "Son sinyali ureten strateji.",
  timeframe: "Son sinyalin ait oldugu periyot.",
  rsi14: "RSI(14) degeri.",
  rsiFast: "Kisa periyot RSI degeri (RSI Fast).",
  cci: "CCI osilator degeri.",
  macd: "MACD degeri.",
  wr: "Williams %R degeri.",
  roc: "Rate of Change (ROC) degeri.",
  ult: "Ultimate Oscillator degeri.",
  bbp: "Bollinger Band %B degeri.",
  psy: "PSY osilator degeri.",
  zScore: "Fiyatin normalize edilmis Z-Score degeri.",
  signals24h: "Son 24 saatte bu sembolde uretilen toplam AL+SAT sinyal adedi.",
  signalsTotal: "Bu sembol icin kaydedilen toplam sinyal sayisi.",
  bias: "AL sinyalleri eksi SAT sinyalleri.",
  score: "Stratejinin son hesaplanan skor metni.",
  lastSeen: "Bu sembole ait son kaydin sisteme dusme zamani.",
}

const NUMERIC_FILTER_COLUMNS: NumericFilterColumnId[] = [
  "price",
  "changePct",
  "perf7d",
  "perf30d",
  "rsi14",
  "rsiFast",
  "cci",
  "macd",
  "wr",
  "roc",
  "ult",
  "bbp",
  "psy",
  "zScore",
  "signals24h",
  "signalsTotal",
  "bias",
]

const NUMERIC_FILTER_OPERATORS: Array<{ value: NumericFilterOperator; label: string }> = [
  { value: "gt", label: ">" },
  { value: "gte", label: ">=" },
  { value: "lt", label: "<" },
  { value: "lte", label: "<=" },
  { value: "eq", label: "=" },
  { value: "between", label: "Aralik" },
]

const VIEW_PRESETS: Record<ViewKey, { label: string; subtitle: string; columns: ColumnId[]; sortBy: ColumnId; sortDirection: SortDirection }> = {
  ozel: {
    label: "Ozel",
    subtitle: "Sinyal yogunlugu ve son durum odakli temel takip gorunumu.",
    columns: ["symbol", "price", "changePct", "lastSignal", "strategy", "timeframe", "rsi14", "signals24h", "signalsTotal", "lastSeen"],
    sortBy: "signals24h",
    sortDirection: "desc",
  },
  momentum: {
    label: "Momentum",
    subtitle: "Kisa ve orta vade ivme takibi icin performans ve osilator odakli gorunum.",
    columns: ["symbol", "price", "changePct", "perf7d", "perf30d", "rsi14", "rsiFast", "roc", "macd", "wr", "cci", "bias", "lastSeen"],
    sortBy: "changePct",
    sortDirection: "desc",
  },
  akim: {
    label: "Akim",
    subtitle: "Bot akisinda son uretilen sinyallerin frekans ve strateji dagilimi.",
    columns: ["symbol", "lastSignal", "strategy", "timeframe", "score", "signals24h", "signalsTotal", "price", "lastSeen"],
    sortBy: "lastSeen",
    sortDirection: "desc",
  },
  risk: {
    label: "Risk",
    subtitle: "Asiri alis/satis bolgeleri ve sinyal bias dengesini takip eder.",
    columns: ["symbol", "price", "changePct", "rsi14", "wr", "ult", "bbp", "cci", "zScore", "bias", "signals24h", "lastSignal", "lastSeen"],
    sortBy: "rsi14",
    sortDirection: "desc",
  },
}

const DEFAULT_WATCHLISTS: WatchlistModel[] = [
  { id: "bist-core", name: "BIST Portfoy", symbols: ["BIST:THYAO", "BIST:GARAN", "BIST:AKBNK", "BIST:ASELS", "BIST:KCHOL"] },
  { id: "crypto-core", name: "Kripto Core", symbols: ["Kripto:BTCUSDT", "Kripto:ETHUSDT", "Kripto:SOLUSDT", "Kripto:BNBUSDT"] },
  { id: "mix-monitor", name: "Mix Takip", symbols: ["BIST:SASA", "BIST:KONTR", "Kripto:XRPUSDT", "Kripto:AVAXUSDT"] },
]

const KNOWN_TIMEFRAME_ORDER = ["15 DAKIKA", "30 DAKIKA", "1 SAAT", "4 SAAT", "1 GUN", "1 HAFTA", "2 HAFTA", "3 HAFTA", "1 AY"]

type ScannerDialogState =
  | { type: "columnFilter"; column: NumericFilterColumnId; value: string }
  | { type: "createWatchlist"; value: string }
  | { type: "renameWatchlist"; watchlistId: string; value: string }
  | { type: "deleteWatchlist"; watchlistId: string; watchlistName: string }
  | null

export default function ScannerPage() {
  const { addToast } = useToast()
  const health = useBotHealth()

  const [searchQuery, setSearchQuery] = useState("")
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL")
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("ALL")
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("ALL")
  const [timeframeFilter, setTimeframeFilter] = useState<string[]>([])
  const [columnFilterInputs, setColumnFilterInputs] = useState<Partial<Record<NumericFilterColumnId, NumericColumnFilterInput>>>({})

  const [activeView, setActiveView] = useState<ViewKey>("ozel")
  const [visibleColumns, setVisibleColumns] = useState<ColumnId[]>(VIEW_PRESETS.ozel.columns)
  const [sortBy, setSortBy] = useState<ColumnId>(VIEW_PRESETS.ozel.sortBy)
  const [sortDirection, setSortDirection] = useState<SortDirection>(VIEW_PRESETS.ozel.sortDirection)

  const [watchlists, setWatchlists] = useState<WatchlistModel[]>(DEFAULT_WATCHLISTS)
  const [activeWatchlistId, setActiveWatchlistId] = useState(DEFAULT_WATCHLISTS[0]?.id ?? "")
  const [watchOnly, setWatchOnly] = useState(false)
  const [watchlistDraft, setWatchlistDraft] = useState("")
  const [watchlistNotice, setWatchlistNotice] = useState<string | null>(null)
  const [showColumnPanel, setShowColumnPanel] = useState(false)
  const [showWatchlistPanel, setShowWatchlistPanel] = useState(false)
  const [selectedRowKey, setSelectedRowKey] = useState<string | null>(null)
  const [hydrated, setHydrated] = useState(false)
  const [dialogState, setDialogState] = useState<ScannerDialogState>(null)

  const scansQuery = useQuery({
    queryKey: ["scanner-v2", "scanHistory"],
    queryFn: () => fetchScanHistory(180),
    staleTime: 30_000,
    refetchInterval: 90_000,
    refetchIntervalInBackground: false,
  })

  const logsQuery = useQuery({
    queryKey: ["scanner-v2", "logs"],
    queryFn: () => fetchLogs(120),
    staleTime: 30_000,
    refetchInterval: 90_000,
    refetchIntervalInBackground: false,
  })

  const specialTagHealthQuery = useQuery<ApiSpecialTagHealth>({
    queryKey: ["scanner-v2", "special-tag-health"],
    queryFn: () => fetchSpecialTagHealth({ market_type: "BIST", since_hours: 24, window_seconds: 900 }),
    staleTime: 60_000,
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  })

  const bistSignalsQuery = useQuery<ScannerSignal[]>({
    queryKey: ["scanner-v2", "signals", "BIST"],
    queryFn: async () => (await fetchSignals({ market_type: "BIST", limit: 700 })).map(mapApiSignal),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  })

  const kriptoSignalsQuery = useQuery<ScannerSignal[]>({
    queryKey: ["scanner-v2", "signals", "Kripto"],
    queryFn: async () => (await fetchSignals({ market_type: "Kripto", limit: 700 })).map(mapApiSignal),
    staleTime: 30_000,
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
  })

  const scans = useMemo(() => scansQuery.data ?? EMPTY_SCANS, [scansQuery.data])
  const logs = useMemo(() => logsQuery.data ?? EMPTY_LOGS, [logsQuery.data])
  const specialTagHealth = specialTagHealthQuery.data ?? null
  const bistSignals = useMemo(() => bistSignalsQuery.data ?? EMPTY_SIGNALS, [bistSignalsQuery.data])
  const kriptoSignals = useMemo(() => kriptoSignalsQuery.data ?? EMPTY_SIGNALS, [kriptoSignalsQuery.data])
  const allSignals = useMemo(() => [...bistSignals, ...kriptoSignals].sort(sortSignalsByDateDesc), [bistSignals, kriptoSignals])
  const screenerRows = useMemo(() => buildScreenerRows(allSignals), [allSignals])
  const numericFilters = useMemo(() => buildNumericFiltersFromInputs(columnFilterInputs), [columnFilterInputs])

  const metricTargets = useMemo<ScannerMetricTarget[]>(
    () =>
      [...screenerRows]
        .sort((left, right) => right.lastSeenTs - left.lastSeenTs)
        .slice(0, 600)
        .map((row) => ({ key: row.key, symbol: row.symbol, marketType: row.marketType })),
    [screenerRows]
  )

  const metricTargetKey = useMemo(() => metricTargets.map((target) => target.key).join("|"), [metricTargets])

  const marketMetricQuery = useQuery<Record<string, MarketMetricSnapshot>>({
    queryKey: ["scanner-v2", "market-metrics", metricTargetKey],
    queryFn: () => fetchMarketMetricsForTargets(metricTargets),
    enabled: metricTargets.length > 0,
    staleTime: 60_000,
    refetchInterval: 120_000,
    refetchIntervalInBackground: false,
  })

  const rowsWithMarketMetrics = useMemo(
    () => applyMarketMetrics(screenerRows, marketMetricQuery.data ?? {}),
    [screenerRows, marketMetricQuery.data]
  )

  const timeframeOptions = useMemo(() => {
    const values = new Set<string>()
    for (const row of rowsWithMarketMetrics) values.add(row.lastTimeframe)
    return Array.from(values).sort((left, right) => timeframeRank(left) - timeframeRank(right))
  }, [rowsWithMarketMetrics])

  const activeWatchlist = useMemo(
    () => watchlists.find((watchlist) => watchlist.id === activeWatchlistId) ?? watchlists[0] ?? null,
    [watchlists, activeWatchlistId]
  )
  const activeWatchSet = useMemo(() => new Set(activeWatchlist?.symbols ?? []), [activeWatchlist])

  const filteredRows = useMemo(() => {
    const keyword = searchQuery.trim().toUpperCase()
    const timeframeSet = new Set(timeframeFilter)
    return rowsWithMarketMetrics.filter((row) => {
      if (marketFilter !== "ALL" && row.marketType !== marketFilter) return false
      if (strategyFilter !== "ALL" && row.lastStrategy !== strategyFilter) return false
      if (signalFilter !== "ALL" && row.lastSignalType !== signalFilter) return false
      if (timeframeSet.size > 0 && !timeframeSet.has(row.lastTimeframe)) return false
      if (keyword && !`${row.symbol} ${row.marketType}`.toUpperCase().includes(keyword)) return false
      if (watchOnly && !activeWatchSet.has(row.key)) return false
      if (!matchesNumericFilters(row, numericFilters)) return false
      return true
    })
  }, [rowsWithMarketMetrics, searchQuery, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly, activeWatchSet, numericFilters])

  const sortedRows = useMemo(() => {
    const meta = COLUMN_META[sortBy]
    const directionFactor = sortDirection === "asc" ? 1 : -1
    return [...filteredRows].sort((left, right) => {
      const l = meta.sortValue(left)
      const r = meta.sortValue(right)
      if (typeof l === "number" && typeof r === "number") {
        if (l === r) return left.symbol.localeCompare(right.symbol, "tr")
        return (l - r) * directionFactor
      }
      const cmp = String(l).localeCompare(String(r), "tr")
      if (cmp === 0) return left.symbol.localeCompare(right.symbol, "tr")
      return cmp * directionFactor
    })
  }, [filteredRows, sortBy, sortDirection])

  useEffect(() => {
    if (sortedRows.length === 0) {
      setSelectedRowKey(null)
      return
    }
    if (!selectedRowKey || !sortedRows.some((row) => row.key === selectedRowKey)) {
      setSelectedRowKey(sortedRows[0].key)
    }
  }, [sortedRows, selectedRowKey])

  const selectedRow = useMemo(() => sortedRows.find((row) => row.key === selectedRowKey) ?? null, [sortedRows, selectedRowKey])
  const selectedSignals = useMemo(() => {
    if (!selectedRow) return EMPTY_SIGNALS
    return allSignals.filter((signal) => signal.symbol === selectedRow.symbol && signal.marketType === selectedRow.marketType).slice(0, 16)
  }, [allSignals, selectedRow])

  const latestScan = scans[0] ?? null
  const specialTagIssues = useMemo(
    () => (specialTagHealth?.rows ?? []).filter((row) => row.missing > 0),
    [specialTagHealth]
  )
  const warningLogCount = logs.filter((entry) => toLogLevel(entry.level) === "WARNING").length
  const errorLogCount = logs.filter((entry) => toLogLevel(entry.level) === "ERROR").length
  const signals24h = allSignals.filter((signal) => Date.now() - (parseDate(signal.createdAt)?.getTime() ?? 0) <= 86_400_000).length
  const buyCountFiltered = filteredRows.reduce((sum, row) => sum + row.buySignals, 0)
  const sellCountFiltered = filteredRows.reduce((sum, row) => sum + row.sellSignals, 0)

  const isRefreshing =
    scansQuery.isFetching ||
    logsQuery.isFetching ||
    specialTagHealthQuery.isFetching ||
    bistSignalsQuery.isFetching ||
    kriptoSignalsQuery.isFetching ||
    marketMetricQuery.isFetching

  const isScreenerDataLoading =
    (bistSignalsQuery.isLoading && !bistSignalsQuery.data) ||
    (kriptoSignalsQuery.isLoading && !kriptoSignalsQuery.data) ||
    (metricTargets.length > 0 && marketMetricQuery.isLoading && !marketMetricQuery.data)

  const hasScreenerDataError =
    bistSignalsQuery.isError ||
    kriptoSignalsQuery.isError ||
    marketMetricQuery.isError

  const screenerDataErrorMessage = useMemo(() => {
    const messages: string[] = []
    if (bistSignalsQuery.error instanceof Error) messages.push(`BIST: ${bistSignalsQuery.error.message}`)
    if (kriptoSignalsQuery.error instanceof Error) messages.push(`Kripto: ${kriptoSignalsQuery.error.message}`)
    if (marketMetricQuery.error instanceof Error) messages.push(`Metrikler: ${marketMetricQuery.error.message}`)
    if (messages.length === 0) return "Tarama verisi alinamadi. Ag veya API durumunu kontrol edin."
    return messages.join(" | ")
  }, [bistSignalsQuery.error, kriptoSignalsQuery.error, marketMetricQuery.error])

  useEffect(() => {
    if (typeof window === "undefined") return
    try {
      const rawWatchlists = window.localStorage.getItem(WATCHLIST_STORAGE_KEY)
      if (rawWatchlists) {
        const parsed = JSON.parse(rawWatchlists)
        if (Array.isArray(parsed)) {
          const restored = parsed
            .map((item): WatchlistModel | null => {
              if (!item || typeof item !== "object") return null
              const model = item as Partial<WatchlistModel>
              if (typeof model.id !== "string" || typeof model.name !== "string" || !Array.isArray(model.symbols)) return null
              return { id: model.id, name: model.name, symbols: model.symbols.filter((s): s is string => typeof s === "string") }
            })
            .filter((item): item is WatchlistModel => item !== null)
          if (restored.length > 0) setWatchlists(restored)
        }
      }

      const storedActiveId = window.localStorage.getItem(WATCHLIST_ACTIVE_KEY)
      if (storedActiveId) setActiveWatchlistId(storedActiveId)

      const rawPrefs = window.localStorage.getItem(PREF_STORAGE_KEY)
      if (rawPrefs) {
        const prefs = JSON.parse(rawPrefs) as Partial<{
          activeView: ViewKey
          visibleColumns: ColumnId[]
          sortBy: ColumnId
          sortDirection: SortDirection
          marketFilter: MarketFilter
          strategyFilter: StrategyFilter
          signalFilter: SignalFilter
          timeframeFilter: string[]
          watchOnly: boolean
          columnFilterInputs: Partial<Record<NumericFilterColumnId, NumericColumnFilterInput>>
        }>
        if (prefs.activeView && VIEW_PRESETS[prefs.activeView]) setActiveView(prefs.activeView)
        if (Array.isArray(prefs.visibleColumns)) {
          const validColumns = prefs.visibleColumns.filter((column): column is ColumnId => COLUMN_ORDER.includes(column))
          if (validColumns.length > 0) setVisibleColumns(addLockedColumns(validColumns))
        }
        if (prefs.sortBy && COLUMN_ORDER.includes(prefs.sortBy)) setSortBy(prefs.sortBy)
        if (prefs.sortDirection === "asc" || prefs.sortDirection === "desc") setSortDirection(prefs.sortDirection)
        if (prefs.marketFilter === "ALL" || prefs.marketFilter === "BIST" || prefs.marketFilter === "Kripto") setMarketFilter(prefs.marketFilter)
        if (prefs.strategyFilter === "ALL" || prefs.strategyFilter === "COMBO" || prefs.strategyFilter === "HUNTER") setStrategyFilter(prefs.strategyFilter)
        if (prefs.signalFilter === "ALL" || prefs.signalFilter === "AL" || prefs.signalFilter === "SAT") setSignalFilter(prefs.signalFilter)
        if (Array.isArray(prefs.timeframeFilter)) setTimeframeFilter(prefs.timeframeFilter.filter((item): item is string => typeof item === "string"))
        if (typeof prefs.watchOnly === "boolean") setWatchOnly(prefs.watchOnly)
        if (prefs.columnFilterInputs && typeof prefs.columnFilterInputs === "object") {
          setColumnFilterInputs(sanitizeColumnFilterInputs(prefs.columnFilterInputs))
        }
      }
    } catch (error) {
      console.error("Scanner preferences could not be restored:", error)
    } finally {
      setHydrated(true)
    }
  }, [])

  useEffect(() => {
    if (!hydrated || typeof window === "undefined") return
    window.localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(watchlists))
    window.localStorage.setItem(WATCHLIST_ACTIVE_KEY, activeWatchlistId)
    window.localStorage.setItem(PREF_STORAGE_KEY, JSON.stringify({ activeView, visibleColumns, sortBy, sortDirection, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly, columnFilterInputs }))
  }, [hydrated, watchlists, activeWatchlistId, activeView, visibleColumns, sortBy, sortDirection, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly, columnFilterInputs])

  useEffect(() => {
    if (!watchlistNotice) return
    const timer = window.setTimeout(() => setWatchlistNotice(null), 2400)
    return () => window.clearTimeout(timer)
  }, [watchlistNotice])

  const refreshAll = async () => {
    await Promise.all([
      scansQuery.refetch(),
      logsQuery.refetch(),
      specialTagHealthQuery.refetch(),
      bistSignalsQuery.refetch(),
      kriptoSignalsQuery.refetch(),
      marketMetricQuery.refetch(),
    ])
  }

  const applyViewPreset = (view: ViewKey) => {
    const preset = VIEW_PRESETS[view]
    setActiveView(view)
    setVisibleColumns(addLockedColumns(preset.columns))
    setSortBy(preset.sortBy)
    setSortDirection(preset.sortDirection)
  }

  const handleSort = (column: ColumnId) => {
    if (sortBy !== column) {
      setSortBy(column)
      setSortDirection("desc")
      return
    }
    setSortDirection((prev) => (prev === "desc" ? "asc" : "desc"))
  }

  const toggleTimeframe = (timeframe: string) => {
    setTimeframeFilter((prev) => (prev.includes(timeframe) ? prev.filter((item) => item !== timeframe) : [...prev, timeframe]))
  }

  const toggleColumn = (column: ColumnId) => {
    setVisibleColumns((prev) => {
      if (prev.includes(column)) {
        if (LOCKED_COLUMNS.has(column)) return prev
        return prev.filter((item) => item !== column)
      }
      return sortColumns([...prev, column])
    })
  }

  const updateColumnFilterInput = (
    column: NumericFilterColumnId,
    patch: Partial<NumericColumnFilterInput>
  ) => {
    setColumnFilterInputs((prev) => {
      const current = prev[column] ?? { operator: "gte", value: "", valueTo: "" }
      const next = { ...current, ...patch }
      return { ...prev, [column]: next }
    })
  }

  const clearColumnFilterInput = (column: NumericFilterColumnId) => {
    setColumnFilterInputs((prev) => {
      const next = { ...prev }
      delete next[column]
      return next
    })
  }

  const applyColumnFilterPrompt = (column: NumericFilterColumnId) => {
    const currentInput = columnFilterInputs[column]
    const currentText = currentInput ? summarizeColumnFilterInput(currentInput) : ""
    setDialogState({
      type: "columnFilter",
      column,
      value: currentText,
    })
  }

  const upsertActiveWatchlist = (updater: (watchlist: WatchlistModel) => WatchlistModel) => {
    setWatchlists((prev) => prev.map((watchlist) => (watchlist.id === activeWatchlistId ? updater(watchlist) : watchlist)))
  }

  const toggleWatchSymbol = (symbolKey: string) => {
    if (!activeWatchlist) return
    upsertActiveWatchlist((watchlist) => {
      if (watchlist.symbols.includes(symbolKey)) {
        return { ...watchlist, symbols: watchlist.symbols.filter((item) => item !== symbolKey) }
      }
      return { ...watchlist, symbols: [...watchlist.symbols, symbolKey] }
    })
  }

  const resolveSymbolToKey = (raw: string) => {
    const normalized = raw.trim().toUpperCase()
    if (!normalized) return null
    if (normalized.includes(":")) {
      const exact = screenerRows.find((row) => row.key.toUpperCase() === normalized)
      return exact?.key ?? null
    }
    const matches = screenerRows.filter((row) => row.symbol.toUpperCase() === normalized)
    if (matches.length === 0) return null
    if (matches.length === 1) return matches[0].key
    if (marketFilter !== "ALL") {
      const byMarket = matches.find((row) => row.marketType === marketFilter)
      if (byMarket) return byMarket.key
    }
    return matches[0].key
  }

  const addDraftToWatchlist = () => {
    if (!activeWatchlist) return
    const resolved = resolveSymbolToKey(watchlistDraft)
    if (!resolved) {
      setWatchlistNotice("Sembol bulunamadi.")
      return
    }
    if (activeWatchSet.has(resolved)) {
      setWatchlistNotice("Sembol listede zaten var.")
      return
    }
    upsertActiveWatchlist((watchlist) => ({ ...watchlist, symbols: [...watchlist.symbols, resolved] }))
    setWatchlistDraft("")
    setWatchlistNotice("Sembol listeye eklendi.")
  }

  const createWatchlist = () => {
    setDialogState({
      type: "createWatchlist",
      value: "",
    })
  }

  const renameWatchlist = () => {
    if (!activeWatchlist) return
    setDialogState({
      type: "renameWatchlist",
      watchlistId: activeWatchlist.id,
      value: activeWatchlist.name,
    })
  }

  const deleteWatchlist = () => {
    if (!activeWatchlist) return
    if (watchlists.length <= 1) {
      setWatchlistNotice("En az bir watchlist kalmali.")
      return
    }
    setDialogState({
      type: "deleteWatchlist",
      watchlistId: activeWatchlist.id,
      watchlistName: activeWatchlist.name,
    })
  }

  const closeDialog = () => {
    setDialogState(null)
  }

  const handleDialogConfirm = () => {
    if (!dialogState) return

    if (dialogState.type === "columnFilter") {
      const trimmed = dialogState.value.trim()
      if (!trimmed) {
        clearColumnFilterInput(dialogState.column)
        closeDialog()
        return
      }

      const parsed = parseColumnFilterExpression(trimmed)
      if (!parsed) {
        addToast({
          type: "error",
          title: "Gecersiz filtre formati",
          message: "Ornekler: >= 7, <= 10, = 30, 20..40",
        })
        return
      }

      updateColumnFilterInput(dialogState.column, parsed)
      closeDialog()
      return
    }

    if (dialogState.type === "createWatchlist") {
      const nextName = dialogState.value.trim()
      if (!nextName) {
        addToast({
          type: "error",
          title: "Liste adi gerekli",
          message: "Yeni watchlist icin bir isim girin.",
        })
        return
      }
      const model: WatchlistModel = { id: makeWatchlistId(nextName), name: nextName, symbols: [] }
      setWatchlists((prev) => [model, ...prev])
      setActiveWatchlistId(model.id)
      setWatchOnly(true)
      setWatchlistNotice("Yeni liste olusturuldu.")
      addToast({
        type: "success",
        title: "Watchlist olusturuldu",
        message: `${nextName} aktif liste olarak secildi.`,
      })
      closeDialog()
      return
    }

    if (dialogState.type === "renameWatchlist") {
      const nextName = dialogState.value.trim()
      if (!nextName) {
        addToast({
          type: "error",
          title: "Liste adi gerekli",
          message: "Watchlist adini bos birakamazsiniz.",
        })
        return
      }
      setWatchlists((prev) =>
        prev.map((watchlist) =>
          watchlist.id === dialogState.watchlistId
            ? { ...watchlist, name: nextName }
            : watchlist
        )
      )
      setWatchlistNotice("Liste adi guncellendi.")
      addToast({
        type: "success",
        title: "Watchlist guncellendi",
        message: `Yeni ad: ${nextName}`,
      })
      closeDialog()
      return
    }

    if (dialogState.type === "deleteWatchlist") {
      const fallback = watchlists.find((watchlist) => watchlist.id !== dialogState.watchlistId)
      setWatchlists((prev) =>
        prev.filter((watchlist) => watchlist.id !== dialogState.watchlistId)
      )
      if (fallback) setActiveWatchlistId(fallback.id)
      setWatchlistNotice("Watchlist silindi.")
      addToast({
        type: "success",
        title: "Watchlist silindi",
        message: `${dialogState.watchlistName} listesi kaldirildi.`,
      })
      closeDialog()
    }
  }

  const sortIconForColumn = (column: ColumnId) => {
    if (sortBy !== column) return "<>"
    return sortDirection === "desc" ? "v" : "^"
  }

  const visibleColumnsSafe = addLockedColumns(visibleColumns)
  const criticalLogs = logs.filter((entry) => {
    const level = toLogLevel(entry.level)
    return level === "ERROR" || level === "WARNING"
  }).slice(0, 12)

  return (
    <div className="mx-auto flex w-full max-w-[1900px] flex-col gap-3 px-3 py-3 md:px-4">
      <section className="border border-border bg-surface">
        <div className="border-b border-border px-3 py-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <div className="label-uppercase">Hisse Takipcisi</div>
              <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Rapto Screener</h1>
              <p className="mt-1 text-xs text-muted-foreground">{VIEW_PRESETS[activeView].subtitle}</p>
            </div>
            <div className="flex w-full flex-wrap items-center gap-2 xl:w-auto">
              <label className="relative flex min-w-[280px] flex-1 items-center xl:min-w-[360px] xl:flex-none">
                <Search className="pointer-events-none absolute left-2 h-3.5 w-3.5 text-muted-foreground" />
                <Input value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} className="h-8 pl-8 text-xs" placeholder="Ara (CTRL+K) - THYAO, BTCUSDT..." />
              </label>
              <Button type="button" variant="outline" size="sm" className="h-8 gap-1.5 px-2 text-xs" onClick={refreshAll} disabled={isRefreshing}>
                <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
                Yenile
              </Button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 border-b border-border md:grid-cols-3 xl:grid-cols-6">
          <RibbonCell label="Bot Durumu" value={health.isRunning ? "AKTIF" : "PASIF"} tone={health.isRunning ? "profit" : "loss"} />
          <RibbonCell label="Screener Satiri" value={formatCount(sortedRows.length)} />
          <RibbonCell label="Universe" value={formatCount(screenerRows.length)} />
          <RibbonCell label="24s Sinyal" value={formatCount(signals24h)} />
          <RibbonCell label="AL / SAT" value={`${formatCount(buyCountFiltered)} / ${formatCount(sellCountFiltered)}`} tone={buyCountFiltered >= sellCountFiltered ? "profit" : "loss"} />
          <RibbonCell label="Log Risk" value={`${errorLogCount} err | ${warningLogCount} warn`} tone={errorLogCount > 0 ? "loss" : warningLogCount > 0 ? "neutral" : "profit"} />
        </div>

        <div className="border-b border-border px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <Select value={marketFilter} onChange={(event) => setMarketFilter(event.target.value as MarketFilter)} className="min-w-[130px]">
              <option value="ALL">Pazar: Tum</option>
              <option value="BIST">Pazar: BIST</option>
              <option value="Kripto">Pazar: Kripto</option>
            </Select>
            <Select value={strategyFilter} onChange={(event) => setStrategyFilter(event.target.value as StrategyFilter)} className="min-w-[150px]">
              <option value="ALL">Strateji: Tum</option>
              <option value="COMBO">Strateji: COMBO</option>
              <option value="HUNTER">Strateji: HUNTER</option>
            </Select>
            <Select value={signalFilter} onChange={(event) => setSignalFilter(event.target.value as SignalFilter)} className="min-w-[120px]">
              <option value="ALL">Tip: Tum</option>
              <option value="AL">Tip: AL</option>
              <option value="SAT">Tip: SAT</option>
            </Select>
            <Select value={activeWatchlist?.id ?? ""} onChange={(event) => setActiveWatchlistId(event.target.value)} className="min-w-[180px]">
              {watchlists.map((watchlist) => (
                <option key={watchlist.id} value={watchlist.id}>
                  {watchlist.name}
                </option>
              ))}
            </Select>
            <button type="button" onClick={() => setWatchOnly((prev) => !prev)} className={cn("h-8 rounded-sm border px-2 text-xs", watchOnly ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground")}>
              Sadece liste
            </button>
            <button type="button" onClick={() => { setShowWatchlistPanel((prev) => !prev); setShowColumnPanel(false) }} className={cn("inline-flex h-8 items-center gap-1 rounded-sm border px-2 text-xs", showWatchlistPanel ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground")}>
              <ListPlus className="h-3.5 w-3.5" />
              Watchlist
            </button>
            <button type="button" onClick={() => { setShowColumnPanel((prev) => !prev); setShowWatchlistPanel(false) }} className={cn("inline-flex h-8 items-center gap-1 rounded-sm border px-2 text-xs", showColumnPanel ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground")}>
              <Settings2 className="h-3.5 w-3.5" />
              Kolonlar
            </button>
            <button type="button" onClick={() => { setSearchQuery(""); setMarketFilter("ALL"); setStrategyFilter("ALL"); setSignalFilter("ALL"); setTimeframeFilter([]); setColumnFilterInputs({}); setWatchOnly(false) }} className="h-8 rounded-sm border border-border bg-base px-2 text-xs text-muted-foreground hover:text-foreground">
              Filtre sifirla
            </button>
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            {timeframeOptions.slice(0, 9).map((timeframe) => {
              const isActive = timeframeFilter.includes(timeframe)
              return (
                <button key={timeframe} type="button" onClick={() => toggleTimeframe(timeframe)} className={cn("inline-flex h-7 items-center rounded-sm border px-2 text-[11px]", isActive ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground")}>
                  {timeframe}
                </button>
              )
            })}
          </div>

          <div className="mt-2 flex flex-wrap gap-2">
            {(Object.keys(VIEW_PRESETS) as ViewKey[]).map((view) => {
              const isActive = view === activeView
              return (
                <button key={view} type="button" onClick={() => applyViewPreset(view)} className={cn("inline-flex h-8 items-center rounded-sm border px-3 text-xs", isActive ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground")}>
                  {VIEW_PRESETS[view].label}
                </button>
              )
            })}
          </div>
        </div>

        {showColumnPanel ? (
          <div className="border-b border-border px-3 py-2">
            <div className="label-uppercase">Kolon Gosterimi</div>
            <div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
              {COLUMN_ORDER.map((column) => {
                const enabled = visibleColumnsSafe.includes(column)
                return (
                  <button key={column} type="button" onClick={() => toggleColumn(column)} title={COLUMN_HELP[column]} className={cn("flex h-8 items-center justify-between rounded-sm border px-2 text-xs", enabled ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground", LOCKED_COLUMNS.has(column) && "cursor-default")}>
                    <span>{COLUMN_META[column].label}</span>
                    {enabled ? <Check className="h-3.5 w-3.5" /> : null}
                  </button>
                )
              })}
            </div>
          </div>
        ) : null}

        {showWatchlistPanel ? (
          <div className="border-b border-border px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <Input value={watchlistDraft} onChange={(event) => setWatchlistDraft(event.target.value)} className="h-8 max-w-[220px] text-xs" placeholder="Sembol ekle (THYAO veya Kripto:BTCUSDT)" onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addDraftToWatchlist() } }} />
              <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={addDraftToWatchlist}>Ekle</Button>
              <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={createWatchlist}>Yeni Liste</Button>
              <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={renameWatchlist}>Isim Degistir</Button>
              <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={deleteWatchlist}>Liste Sil</Button>
            </div>
            {watchlistNotice ? <div className="mt-2 text-[11px] text-muted-foreground">{watchlistNotice}</div> : null}
          </div>
        ) : null}
      </section>

      <section className="border border-border bg-surface">
        <div className="border-b border-border px-3 py-2">
          <div className="flex items-center justify-between gap-2">
            <div className="label-uppercase">Tarama Tablosu</div>
            <div className="mono-numbers text-[11px] text-muted-foreground">{formatCount(sortedRows.length)} satir | Sort: {COLUMN_META[sortBy].label} ({sortDirection})</div>
          </div>
        </div>

        {isScreenerDataLoading ? (
          <div className="space-y-2 px-3 py-3">
            {Array.from({ length: 8 }).map((_, index) => (
              <div key={`scanner-skeleton-${index}`} className="h-7 animate-pulse border border-border bg-base" />
            ))}
          </div>
        ) : hasScreenerDataError ? (
          <div className="flex flex-col items-center justify-center gap-3 px-3 py-12 text-center">
            <div className="flex h-10 w-10 items-center justify-center border border-loss/40 bg-loss/10 text-loss">
              <AlertTriangle className="h-4 w-4" />
            </div>
            <div className="space-y-1">
              <p className="text-xs font-semibold text-loss">Tarama verisi yuklenemedi.</p>
              <p className="max-w-3xl text-[11px] text-muted-foreground">{screenerDataErrorMessage}</p>
            </div>
            <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={() => void refreshAll()}>
              Tekrar dene
            </Button>
          </div>
        ) : sortedRows.length === 0 ? (
          <div className="px-3 py-12 text-center text-xs text-muted-foreground">Filtreye uygun kayit bulunamadi.</div>
        ) : (
          <div className="max-h-[640px] overflow-auto">
            <table className="w-full min-w-[1680px] text-[11px]">
              <thead className="sticky top-0 z-20 bg-surface">
                <tr className="border-b border-border">
                  {visibleColumnsSafe.map((column) => {
                    const meta = COLUMN_META[column]
                    const numericColumn = toNumericFilterColumn(column)
                    const columnFilter = numericColumn ? columnFilterInputs[numericColumn] : null
                    const hasFilter = columnFilter && hasColumnFilterInput(columnFilter)
                    return (
                      <th key={column} className={cn("px-2 py-2", meta.align === "right" ? "text-right" : "text-left")}>
                        <div className={cn("flex flex-col gap-1", meta.align === "right" ? "items-end" : "items-start")}>
                          <button type="button" onClick={() => handleSort(column)} title={COLUMN_HELP[column]} className={cn("inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.04em]", sortBy === column ? "text-foreground" : "text-muted-foreground")}>
                            <span>{meta.label}</span>
                            <span className="mono-numbers text-[10px]">{sortIconForColumn(column)}</span>
                            <span className="cursor-help text-[9px] text-muted-foreground/70 hover:text-muted-foreground" title={COLUMN_HELP[column]}>?</span>
                          </button>
                          {numericColumn ? (
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation()
                                  applyColumnFilterPrompt(numericColumn)
                                }}
                                className={cn(
                                  "h-5 rounded-sm border px-1.5 text-[10px]",
                                  hasFilter
                                    ? "border-foreground/70 bg-raised text-foreground"
                                    : "border-border bg-base text-muted-foreground hover:text-foreground"
                                )}
                                title={`${COLUMN_META[numericColumn].label} filtresi`}
                              >
                                {hasFilter ? summarizeColumnFilterInput(columnFilter) : "filtre"}
                              </button>
                              {hasFilter ? (
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    clearColumnFilterInput(numericColumn)
                                  }}
                                  className="h-5 rounded-sm border border-border bg-base px-1 text-[10px] text-muted-foreground hover:text-foreground"
                                  title="Filtreyi kaldir"
                                >
                                  x
                                </button>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row) => {
                  const isSelected = row.key === selectedRow?.key
                  return (
                    <tr
                      key={row.key}
                      onClick={() => setSelectedRowKey(row.key)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault()
                          setSelectedRowKey(row.key)
                        }
                      }}
                      tabIndex={0}
                      aria-selected={isSelected}
                      aria-label={`${row.symbol} satırını seç`}
                      className={cn(
                        "cursor-pointer border-b border-[rgba(255,255,255,0.04)] last:border-b-0 odd:bg-surface even:bg-[rgba(255,255,255,0.01)] hover:bg-raised/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
                        isSelected && "border-l-2 border-foreground bg-raised/60"
                      )}
                    >
                      {visibleColumnsSafe.map((column) => (
                        <td key={`${row.key}:${column}`} className={cn("px-2 py-2", COLUMN_META[column].align === "right" ? "text-right" : "text-left")}>
                          {renderCellContent(column, row, activeWatchSet, toggleWatchSymbol)}
                        </td>
                      ))}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel title="Secili Sembol Akisi" subtitle="Son 16 sinyal kaydi">
          {selectedRow ? (
            <div className="space-y-2">
              <div className="grid gap-2 border border-border bg-base p-2 md:grid-cols-4">
                <MetricCell label="Sembol" value={`${selectedRow.symbol} (${selectedRow.marketType})`} />
                <MetricCell label="Son Fiyat" value={formatPrice(selectedRow.latestPrice, selectedRow.marketType)} />
                <MetricCell label="Degisim" value={formatPercent(selectedRow.changePct)} tone={toneFromPercent(selectedRow.changePct)} />
                <MetricCell label="Sinyal Yogunlugu" value={`${selectedRow.signals24h} / ${selectedRow.totalSignals}`} />
              </div>

              <div className="max-h-[300px] overflow-auto border border-border bg-base">
                <ul className="divide-y divide-[rgba(255,255,255,0.04)]">
                  {selectedSignals.map((signal) => (
                    <li key={signal.id} className="px-2 py-1.5 text-[11px]">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={cn("signal-badge", signal.signalType === "AL" ? "signal-buy" : "signal-sell")}>{signal.signalType}</span>
                          <span className="font-medium text-foreground">{signal.strategy}</span>
                          <span className="label-uppercase">{normalizeTimeframe(signal.timeframe)}</span>
                        </div>
                        <span className="mono-numbers text-[10px] text-muted-foreground">{formatClock(signal.createdAt)}</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between">
                        <span className="mono-numbers text-muted-foreground">{signal.score || "--"}</span>
                        <span className="mono-numbers text-muted-foreground">{formatPrice(signal.price, signal.marketType)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ) : (
            <div className="px-2 py-8 text-center text-xs text-muted-foreground">Satir seciniz.</div>
          )}
        </Panel>

        <Panel title="Sistem Sagligi" subtitle="Tarama ritmi ve kritik log ozetleri">
          <div className="space-y-2">
            <div className={cn("border p-2", specialTagHealth?.missing_total ? "border-[rgba(255,77,109,0.4)] bg-[rgba(97,26,40,0.35)]" : "border-border bg-base")}>
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="label-uppercase">Ozel Etiket Kapsama</span>
                <span
                  className={cn(
                    "signal-badge",
                    specialTagHealthQuery.isLoading
                      ? "signal-neutral"
                      : specialTagHealthQuery.isError || specialTagHealth?.missing_total
                        ? "signal-sell"
                        : "signal-buy"
                  )}
                >
                  {specialTagHealthQuery.isLoading
                    ? "CHECKING"
                    : specialTagHealthQuery.isError
                      ? "UNAVAILABLE"
                      : specialTagHealth?.missing_total
                        ? "ALERT"
                        : "OK"}
                </span>
              </div>

              {specialTagHealthQuery.isError ? (
                <div className="text-[11px] text-loss">Ops health endpoint okunamadi.</div>
              ) : specialTagHealth ? (
                <div className="space-y-2">
                  <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                    <span className="text-muted-foreground">Missing toplam</span>
                    <span className={cn("mono-numbers text-right", specialTagHealth.missing_total > 0 ? "text-loss" : "text-profit")}>
                      {formatCount(specialTagHealth.missing_total)}
                    </span>
                    <span className="text-muted-foreground">Son kontrol</span>
                    <span className="mono-numbers text-right">
                      {specialTagHealth.last_checked_at ? getTimeAgo(specialTagHealth.last_checked_at) : "--"}
                    </span>
                    <span className="text-muted-foreground">Pencere</span>
                    <span className="mono-numbers text-right">{specialTagHealth.checked_window_hours}sa / {specialTagHealth.checked_window_seconds}sn</span>
                    <span className="text-muted-foreground">Kaynak state</span>
                    <span className="mono-numbers text-right">{(specialTagHealth.stored_state || specialTagHealth.status).toUpperCase()}</span>
                  </div>

                  <div className="grid gap-1">
                    {specialTagHealth.rows.map((row) => (
                      <div key={`${row.strategy}:${row.tag}`} className="grid grid-cols-[1fr_auto_auto] items-center gap-2 border border-border bg-surface px-2 py-1 text-[10px]">
                        <div className="min-w-0">
                          <div className="truncate font-medium text-foreground">
                            {row.strategy} {formatSpecialTagLabel(row.tag)}
                          </div>
                          <div className="mono-numbers text-muted-foreground">
                            {row.signal_type} | {normalizeTimeframe(row.target_timeframe)}
                          </div>
                        </div>
                        <div className="mono-numbers text-muted-foreground">
                          {row.tagged}/{row.candidates}
                        </div>
                        <div className={cn("mono-numbers", row.missing > 0 ? "text-loss" : "text-profit")}>
                          {row.missing > 0 ? `-${row.missing}` : "0"}
                        </div>
                      </div>
                    ))}
                  </div>

                  {specialTagIssues.length > 0 && specialTagHealth.summary ? (
                    <div className="whitespace-pre-line border border-[rgba(255,77,109,0.28)] bg-[rgba(97,26,40,0.18)] px-2 py-1.5 text-[10px] text-loss">
                      {specialTagHealth.summary}
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-[11px] text-muted-foreground">Health verisi bekleniyor.</div>
              )}
            </div>

            <div className="border border-border bg-base p-2">
              <div className="mb-2 flex items-center justify-between">
                <span className="label-uppercase">Tarama Ozet</span>
                <span className={cn("signal-badge", health.isScanning ? "signal-neutral" : "signal-buy")}>{health.isScanning ? "SCAN ACTIVE" : "IDLE"}</span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
                <span className="text-muted-foreground">Toplam tarama</span>
                <span className="mono-numbers text-right">{formatCount(health.scanCount)}</span>
                <span className="text-muted-foreground">Son tarama</span>
                <span className="mono-numbers text-right">{latestScan ? getTimeAgo(latestScan.created_at) : "--"}</span>
                <span className="text-muted-foreground">Log warning</span>
                <span className="mono-numbers text-right text-neutral">{formatCount(warningLogCount)}</span>
                <span className="text-muted-foreground">Log error</span>
                <span className={cn("mono-numbers text-right", errorLogCount > 0 ? "text-loss" : "text-muted-foreground")}>{formatCount(errorLogCount)}</span>
              </div>
            </div>

            <div className="max-h-[320px] overflow-auto border border-border bg-base">
              <ul className="divide-y divide-[rgba(255,255,255,0.04)]">
                {(criticalLogs.length > 0 ? criticalLogs : logs.slice(0, 12)).map((entry, index) => {
                  const level = toLogLevel(entry.level)
                  return (
                    <li key={`${entry.timestamp}-${index}`} className="grid grid-cols-[62px_56px_1fr] gap-2 px-2 py-1.5 text-[11px]">
                      <span className="mono-numbers text-muted-foreground">{formatClock(entry.timestamp)}</span>
                      <span className={cn("mono-numbers", level === "ERROR" ? "text-loss" : level === "WARNING" ? "text-neutral" : "text-muted-foreground")}>{level}</span>
                      <span className="text-foreground">{entry.message}</span>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>
        </Panel>
      </section>

      <ActionDialog
        open={dialogState !== null}
        title={
          dialogState?.type === "columnFilter"
            ? `${COLUMN_META[dialogState.column].label} filtresi`
            : dialogState?.type === "createWatchlist"
              ? "Yeni watchlist"
              : dialogState?.type === "renameWatchlist"
                ? "Watchlist adini guncelle"
                : dialogState?.type === "deleteWatchlist"
                  ? "Watchlist silinecek"
                  : ""
        }
        description={
          dialogState?.type === "columnFilter"
            ? "Ornek: >= 7, <= 10, = 30, 20..40. Bos birakirsan filtre kaldirilir."
            : dialogState?.type === "deleteWatchlist"
              ? `${dialogState.watchlistName} listesini silmek istiyor musunuz?`
              : "Deger girip onaylayin."
        }
        mode={dialogState?.type === "deleteWatchlist" ? "confirm" : "prompt"}
        variant={dialogState?.type === "deleteWatchlist" ? "danger" : "default"}
        value={dialogState && "value" in dialogState ? dialogState.value : ""}
        placeholder={
          dialogState?.type === "columnFilter"
            ? ">= 7"
            : dialogState?.type === "createWatchlist" || dialogState?.type === "renameWatchlist"
              ? "Watchlist adi"
              : undefined
        }
        confirmLabel={
          dialogState?.type === "columnFilter"
            ? "Uygula"
            : dialogState?.type === "createWatchlist"
              ? "Olustur"
              : dialogState?.type === "renameWatchlist"
                ? "Guncelle"
                : dialogState?.type === "deleteWatchlist"
                  ? "Sil"
                  : "Onayla"
        }
        cancelLabel="Vazgec"
        onValueChange={(value) =>
          setDialogState((prev) => (prev && "value" in prev ? { ...prev, value } : prev))
        }
        onCancel={closeDialog}
        onConfirm={handleDialogConfirm}
      />
    </div>
  )
}

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <section className="border border-border bg-surface">
      <div className="border-b border-border px-3 py-2">
        <div className="label-uppercase">{title}</div>
        {subtitle ? <div className="mt-1 text-[10px] text-muted-foreground">{subtitle}</div> : null}
      </div>
      <div className="p-2">{children}</div>
    </section>
  )
}

function RibbonCell({ label, value, tone }: { label: string; value: string; tone?: "profit" | "loss" | "neutral" }) {
  return (
    <div className="flex h-16 min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0">
      <span className="label-uppercase">{label}</span>
      <span className={cn("mono-numbers truncate text-[16px] font-semibold", tone === "profit" && "text-profit", tone === "loss" && "text-loss", tone === "neutral" && "text-neutral")}>{value}</span>
    </div>
  )
}

function MetricCell({ label, value, tone }: { label: string; value: string; tone?: "profit" | "loss" | "neutral" }) {
  return (
    <div className="border border-border bg-surface px-2 py-1.5">
      <div className="label-uppercase">{label}</div>
      <div className={cn("mono-numbers mt-1 text-sm", tone === "profit" && "text-profit", tone === "loss" && "text-loss", tone === "neutral" && "text-neutral")}>{value}</div>
    </div>
  )
}

function renderCellContent(column: ColumnId, row: ScreenerRow, watchSet: Set<string>, onToggleWatch: (symbolKey: string) => void) {
  switch (column) {
    case "symbol":
      return (
        <div className="flex min-w-[190px] items-center gap-2">
          <button type="button" onClick={(event) => { event.stopPropagation(); onToggleWatch(row.key) }} className="inline-flex h-5 w-5 items-center justify-center text-muted-foreground hover:text-foreground" aria-label="Watchlist toggle">
            {watchSet.has(row.key) ? <Star className="h-3.5 w-3.5 fill-current" /> : <StarOff className="h-3.5 w-3.5" />}
          </button>
          <span className="font-medium text-foreground">{row.symbol}</span>
        </div>
      )
    case "market":
      return <span className="label-uppercase">{row.marketType}</span>
    case "price":
      return <span className="mono-numbers text-foreground">{formatPrice(row.latestPrice, row.marketType)}</span>
    case "changePct":
      return <span className={cn("mono-numbers", toneClassFromPercent(row.changePct))}>{formatPercent(row.changePct)}</span>
    case "perf7d":
      return <span className={cn("mono-numbers", toneClassFromPercent(row.perf7d))}>{formatPercent(row.perf7d)}</span>
    case "perf30d":
      return <span className={cn("mono-numbers", toneClassFromPercent(row.perf30d))}>{formatPercent(row.perf30d)}</span>
    case "lastSignal":
      return <span className={cn("signal-badge", row.lastSignalType === "AL" ? "signal-buy" : "signal-sell")}>{row.lastSignalType}</span>
    case "strategy":
      return <span className="label-uppercase">{row.lastStrategy}</span>
    case "timeframe":
      return <span className="mono-numbers text-muted-foreground">{row.lastTimeframe}</span>
    case "rsi14":
      return <span className={cn("mono-numbers", oscillatorToneClass(row.rsi14))}>{formatDecimal(row.rsi14)}</span>
    case "rsiFast":
      return <span className={cn("mono-numbers", oscillatorToneClass(row.rsiFast))}>{formatDecimal(row.rsiFast)}</span>
    case "cci":
      return <span className={cn("mono-numbers", oscillatorToneClass(row.cci))}>{formatDecimal(row.cci)}</span>
    case "macd":
      return <span className={cn("mono-numbers", toneClassFromPercent(row.macd))}>{formatDecimal(row.macd)}</span>
    case "wr":
      return <span className={cn("mono-numbers", williamsToneClass(row.wr))}>{formatDecimal(row.wr)}</span>
    case "roc":
      return <span className={cn("mono-numbers", toneClassFromPercent(row.roc))}>{formatDecimal(row.roc)}</span>
    case "ult":
      return <span className={cn("mono-numbers", oscillatorToneClass(row.ult))}>{formatDecimal(row.ult)}</span>
    case "bbp":
      return <span className={cn("mono-numbers", bollingerPercentToneClass(row.bbp))}>{formatDecimal(row.bbp)}</span>
    case "psy":
      return <span className={cn("mono-numbers", oscillatorToneClass(row.psy))}>{formatDecimal(row.psy)}</span>
    case "zScore":
      return <span className={cn("mono-numbers", zScoreToneClass(row.zScore))}>{formatDecimal(row.zScore)}</span>
    case "signals24h":
      return <span className="mono-numbers text-foreground">{formatCount(row.signals24h)}</span>
    case "signalsTotal":
      return <span className="mono-numbers text-muted-foreground">{formatCount(row.totalSignals)}</span>
    case "bias": {
      const bias = row.buySignals - row.sellSignals
      return <span className={cn("mono-numbers", bias > 0 ? "text-profit" : bias < 0 ? "text-loss" : "text-muted-foreground")}>{bias > 0 ? `+${bias}` : String(bias)}</span>
    }
    case "score":
      return <span className="mono-numbers text-muted-foreground">{row.lastScore || "--"}</span>
    case "lastSeen":
      return <span className="mono-numbers text-muted-foreground">{getTimeAgo(row.lastSeenIso)}</span>
  }
}

function formatSpecialTagLabel(tag: ApiSpecialTagHealth["rows"][number]["tag"]) {
  switch (tag) {
    case "BELES":
      return "Beles"
    case "COK_UCUZ":
      return "Cok Ucuz"
    case "PAHALI":
      return "Pahali"
    case "FAHIS_FIYAT":
      return "Fahis Fiyat"
    default:
      return tag
  }
}

function mapApiSignal(signal: ApiSignal): ScannerSignal {
  const withDetails = signal as ApiSignal & { details?: unknown }
  return {
    id: signal.id,
    symbol: signal.symbol?.toUpperCase() ?? "-",
    marketType: signal.market_type === "BIST" ? "BIST" : "Kripto",
    strategy: signal.strategy === "HUNTER" ? "HUNTER" : "COMBO",
    signalType: signal.signal_type === "SAT" ? "SAT" : "AL",
    timeframe: normalizeTimeframe(signal.timeframe),
    score: signal.score || "",
    price: Number.isFinite(signal.price) ? signal.price : 0,
    createdAt: signal.created_at || new Date().toISOString(),
    details: parseDetailsObject(withDetails.details),
  }
}

function parseDetailsObject(raw: unknown): Record<string, unknown> | null {
  if (!raw) return null
  if (typeof raw === "object" && !Array.isArray(raw)) return raw as Record<string, unknown>
  if (typeof raw !== "string") return null
  try {
    const parsed = JSON.parse(raw)
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed as Record<string, unknown>
    return null
  } catch {
    return null
  }
}

function buildScreenerRows(signals: ScannerSignal[]): ScreenerRow[] {
  const grouped = new Map<string, MutableScreenerRow>()
  const dayAgo = Date.now() - 86_400_000
  for (const signal of signals) {
    const key = symbolKey(signal.marketType, signal.symbol)
    const ts = parseDate(signal.createdAt)?.getTime() ?? 0
    const current = grouped.get(key)
    if (!current) {
      const baseRow: ScreenerRow = {
        key,
        symbol: signal.symbol,
        marketType: signal.marketType,
        latestPrice: signal.price,
        changePct: null,
        perf7d: null,
        perf30d: null,
        lastSignalType: signal.signalType,
        lastStrategy: signal.strategy,
        lastTimeframe: signal.timeframe,
        lastScore: signal.score,
        lastSeenIso: signal.createdAt,
        lastSeenTs: ts,
        buySignals: signal.signalType === "AL" ? 1 : 0,
        sellSignals: signal.signalType === "SAT" ? 1 : 0,
        comboSignals: signal.strategy === "COMBO" ? 1 : 0,
        hunterSignals: signal.strategy === "HUNTER" ? 1 : 0,
        totalSignals: 1,
        signals24h: ts >= dayAgo ? 1 : 0,
        rsi14: null,
        rsiFast: null,
        cci: null,
        macd: null,
        wr: null,
        roc: null,
        ult: null,
        bbp: null,
        psy: null,
        zScore: null,
      }
      mergeIndicatorSnapshot(baseRow, signal.details)
      grouped.set(key, {
        row: baseRow,
        timeline: signal.price > 0 ? [{ ts, price: signal.price }] : [],
      })
      continue
    }
    current.row.totalSignals += 1
    if (signal.signalType === "AL") current.row.buySignals += 1
    if (signal.signalType === "SAT") current.row.sellSignals += 1
    if (signal.strategy === "COMBO") current.row.comboSignals += 1
    if (signal.strategy === "HUNTER") current.row.hunterSignals += 1
    if (ts >= dayAgo) current.row.signals24h += 1
    if (signal.price > 0) current.timeline.push({ ts, price: signal.price })
    mergeIndicatorSnapshot(current.row, signal.details)

    if (ts >= current.row.lastSeenTs) {
      current.row.latestPrice = signal.price
      current.row.lastSignalType = signal.signalType
      current.row.lastStrategy = signal.strategy
      current.row.lastTimeframe = signal.timeframe
      current.row.lastScore = signal.score
      current.row.lastSeenIso = signal.createdAt
      current.row.lastSeenTs = ts
    }
  }

  return Array.from(grouped.values()).map(({ row, timeline }) => {
    const sorted = [...timeline].sort((left, right) => right.ts - left.ts)
    const latest = sorted[0]
    const previous = sorted[1]
    row.changePct = percentageChange(latest?.price ?? null, previous?.price ?? null)
    row.perf7d = percentageChange(latest?.price ?? null, findLookbackPrice(sorted, 7))
    row.perf30d = percentageChange(latest?.price ?? null, findLookbackPrice(sorted, 30))
    return row
  })
}

function mergeIndicatorSnapshot(row: ScreenerRow, details: Record<string, unknown> | null) {
  const pick = (current: number | null, keys: string[]) => current ?? readNumeric(details, keys)
  row.rsi14 = pick(row.rsi14, ["RSI", "rsi", "RSI14", "rsi14"])
  row.rsiFast = pick(row.rsiFast, ["RSI_Fast", "RSI_FAST", "rsi_fast", "RSI2", "rsi2"])
  row.cci = pick(row.cci, ["CCI", "cci"])
  row.macd = pick(row.macd, ["MACD", "macd"])
  row.wr = pick(row.wr, ["W%R", "WR", "wr", "w%r"])
  row.roc = pick(row.roc, ["ROC", "roc"])
  row.ult = pick(row.ult, ["ULT", "ult", "ULTOSC", "ultimate"])
  row.bbp = pick(row.bbp, ["BBP", "bbp", "BB%", "bollinger_percent_b"])
  row.psy = pick(row.psy, ["PSY", "psy"])
  row.zScore = pick(row.zScore, ["ZScore", "zscore", "ZSCORE"])
}

function findLookbackPrice(timeline: Array<{ ts: number; price: number }>, lookbackDays: number) {
  if (timeline.length === 0) return null
  const latestTs = timeline[0].ts
  const targetTs = latestTs - lookbackDays * 86_400_000
  const hit = timeline.find((point) => point.ts <= targetTs)
  return hit?.price ?? null
}

function percentageChange(current: number | null, past: number | null) {
  if (current === null || past === null || !Number.isFinite(current) || !Number.isFinite(past) || past === 0) return null
  return ((current - past) / past) * 100
}

function readNumeric(details: Record<string, unknown> | null, keys: string[]) {
  if (!details) return null
  for (const key of keys) {
    if (!(key in details)) continue
    const parsed = parseNumber(details[key])
    if (parsed !== null) return parsed
  }
  return null
}

function parseNumber(value: unknown): number | null {
  if (typeof value === "number") return Number.isFinite(value) ? value : null
  if (typeof value !== "string") return null
  const normalized = value.replace(",", ".")
  const match = normalized.match(/-?\d+(\.\d+)?/)
  if (!match) return null
  const numeric = Number(match[0])
  return Number.isFinite(numeric) ? numeric : null
}

function symbolKey(marketType: MarketKind, symbol: string) {
  return `${marketType}:${symbol.toUpperCase()}`
}

function normalizeTimeframe(raw: string | null | undefined) {
  const value = (raw ?? "").trim().toUpperCase()
  if (!value) return "-"
  return value
    .replace("GUNLUK", "1 GUN")
    .replace("GÜNLÜK", "1 GUN")
    .replace("HAFTALIK", "1 HAFTA")
    .replace("AYLIK", "1 AY")
    .replace("SAATLIK", "1 SAAT")
    .replace("SAATLİK", "1 SAAT")
    .replace(/\s+/g, " ")
}

function timeframeRank(timeframe: string) {
  const normalized = normalizeTimeframe(timeframe)
  const knownIndex = KNOWN_TIMEFRAME_ORDER.indexOf(normalized)
  if (knownIndex >= 0) return knownIndex
  const numberMatch = normalized.match(/\d+/)
  const amount = numberMatch ? Number(numberMatch[0]) : 1
  if (normalized.includes("DAKIKA")) return amount
  if (normalized.includes("SAAT")) return amount * 60
  if (normalized.includes("GUN")) return amount * 1_440
  if (normalized.includes("HAFTA")) return amount * 10_080
  if (normalized.includes("AY")) return amount * 43_200
  return Number.MAX_SAFE_INTEGER
}

function sortSignalsByDateDesc(left: ScannerSignal, right: ScannerSignal) {
  return (parseDate(right.createdAt)?.getTime() ?? 0) - (parseDate(left.createdAt)?.getTime() ?? 0)
}

function parseDate(value: string | null | undefined) {
  if (!value) return null
  const normalized = value.includes("T") ? value : value.replace(" ", "T")
  const parsed = new Date(normalized)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed
}

function formatClock(value: string | null | undefined) {
  const date = parseDate(value)
  if (!date) return "--:--"
  return date.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })
}

function formatCount(value: number) {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 }).format(value)
}

function formatDecimal(value: number | null) {
  if (value === null) return "--"
  return new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
}

function formatPercent(value: number | null) {
  if (value === null) return "--"
  const formatted = new Intl.NumberFormat("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Math.abs(value))
  return `${value >= 0 ? "+" : "-"}${formatted}%`
}

function formatPrice(value: number, marketType: MarketKind) {
  const digits = marketType === "Kripto" ? 4 : 2
  return new Intl.NumberFormat("tr-TR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value)
}

function toLogLevel(level: string | null | undefined): "INFO" | "WARNING" | "ERROR" {
  const text = (level ?? "").toUpperCase()
  if (text.includes("ERR")) return "ERROR"
  if (text.includes("WARN")) return "WARNING"
  return "INFO"
}

function toneClassFromPercent(value: number | null) {
  if (value === null) return "text-muted-foreground"
  if (value > 0) return "text-profit"
  if (value < 0) return "text-loss"
  return "text-muted-foreground"
}

function toneFromPercent(value: number | null): "profit" | "loss" | "neutral" {
  if (value === null || value === 0) return "neutral"
  return value > 0 ? "profit" : "loss"
}

function oscillatorToneClass(value: number | null) {
  if (value === null) return "text-muted-foreground"
  if (value >= 70) return "text-loss"
  if (value <= 30) return "text-profit"
  return "text-foreground"
}

function williamsToneClass(value: number | null) {
  if (value === null) return "text-muted-foreground"
  if (value >= -20) return "text-loss"
  if (value <= -80) return "text-profit"
  return "text-foreground"
}

function bollingerPercentToneClass(value: number | null) {
  if (value === null) return "text-muted-foreground"
  if (value >= 1) return "text-loss"
  if (value <= 0) return "text-profit"
  return "text-foreground"
}

function zScoreToneClass(value: number | null) {
  if (value === null) return "text-muted-foreground"
  if (value >= 2) return "text-loss"
  if (value <= -2) return "text-profit"
  return "text-foreground"
}

function getNumericValue(row: ScreenerRow, column: NumericFilterColumnId): number | null {
  switch (column) {
    case "price":
      return row.latestPrice
    case "changePct":
      return row.changePct
    case "perf7d":
      return row.perf7d
    case "perf30d":
      return row.perf30d
    case "rsi14":
      return row.rsi14
    case "rsiFast":
      return row.rsiFast
    case "cci":
      return row.cci
    case "macd":
      return row.macd
    case "wr":
      return row.wr
    case "roc":
      return row.roc
    case "ult":
      return row.ult
    case "bbp":
      return row.bbp
    case "psy":
      return row.psy
    case "zScore":
      return row.zScore
    case "signals24h":
      return row.signals24h
    case "signalsTotal":
      return row.totalSignals
    case "bias":
      return row.buySignals - row.sellSignals
  }
}

function matchesNumericFilters(row: ScreenerRow, filters: NumericFilterRule[]) {
  for (const filter of filters) {
    const value = getNumericValue(row, filter.column)
    if (value === null || !Number.isFinite(value)) return false
    if (!matchesNumericRule(value, filter)) return false
  }
  return true
}

function matchesNumericRule(value: number, filter: NumericFilterRule) {
  switch (filter.operator) {
    case "gt":
      return value > filter.value
    case "gte":
      return value >= filter.value
    case "lt":
      return value < filter.value
    case "lte":
      return value <= filter.value
    case "eq":
      return value === filter.value
    case "between": {
      if (filter.valueTo === null) return false
      const low = Math.min(filter.value, filter.valueTo)
      const high = Math.max(filter.value, filter.valueTo)
      return value >= low && value <= high
    }
  }
}

function toNumericFilterColumn(column: ColumnId): NumericFilterColumnId | null {
  return NUMERIC_FILTER_COLUMNS.includes(column as NumericFilterColumnId)
    ? (column as NumericFilterColumnId)
    : null
}

function buildNumericFiltersFromInputs(
  inputs: Partial<Record<NumericFilterColumnId, NumericColumnFilterInput>>
) {
  const filters: NumericFilterRule[] = []
  for (const column of NUMERIC_FILTER_COLUMNS) {
    const input = inputs[column]
    if (!input) continue
    const value = parseNumber(input.value)
    if (value === null) continue
    const valueTo = input.operator === "between" ? parseNumber(input.valueTo) : null
    if (input.operator === "between" && valueTo === null) continue
    filters.push({
      column,
      operator: input.operator,
      value,
      valueTo,
    })
  }
  return filters
}

function sanitizeColumnFilterInputs(
  rawInputs: Partial<Record<NumericFilterColumnId, NumericColumnFilterInput>>
) {
  const sanitized: Partial<Record<NumericFilterColumnId, NumericColumnFilterInput>> = {}
  for (const column of NUMERIC_FILTER_COLUMNS) {
    const candidate = rawInputs[column]
    if (!candidate || typeof candidate !== "object") continue
    const operator = NUMERIC_FILTER_OPERATORS.some((item) => item.value === candidate.operator)
      ? candidate.operator
      : "gte"
    sanitized[column] = {
      operator,
      value: typeof candidate.value === "string" ? candidate.value : "",
      valueTo: typeof candidate.valueTo === "string" ? candidate.valueTo : "",
    }
  }
  return sanitized
}

function parseColumnFilterExpression(expression: string): NumericColumnFilterInput | null {
  const compact = expression.replace(/\s+/g, "")
  if (!compact) return null

  const betweenMatch = compact.match(/^(-?\d+(?:[.,]\d+)?)\.\.(-?\d+(?:[.,]\d+)?)$/)
  if (betweenMatch) {
    return {
      operator: "between",
      value: betweenMatch[1].replace(",", "."),
      valueTo: betweenMatch[2].replace(",", "."),
    }
  }

  const withOperator = compact.match(/^(>=|<=|>|<|=)(-?\d+(?:[.,]\d+)?)$/)
  if (withOperator) {
    const operatorMap: Record<string, NumericFilterOperator> = {
      ">": "gt",
      ">=": "gte",
      "<": "lt",
      "<=": "lte",
      "=": "eq",
    }
    return {
      operator: operatorMap[withOperator[1]],
      value: withOperator[2].replace(",", "."),
      valueTo: "",
    }
  }

  const bareNumber = compact.match(/^-?\d+(?:[.,]\d+)?$/)
  if (bareNumber) {
    return {
      operator: "eq",
      value: bareNumber[0].replace(",", "."),
      valueTo: "",
    }
  }

  return null
}

function summarizeColumnFilterInput(input: NumericColumnFilterInput | null | undefined) {
  if (!input || !input.value.trim()) return ""
  if (input.operator === "between") {
    if (!input.valueTo.trim()) return ""
    return `${input.value}..${input.valueTo}`
  }
  const symbol = NUMERIC_FILTER_OPERATORS.find((operator) => operator.value === input.operator)?.label ?? "="
  return `${symbol}${input.value}`
}

function hasColumnFilterInput(input: NumericColumnFilterInput | null | undefined) {
  return summarizeColumnFilterInput(input).length > 0
}

function applyMarketMetrics(
  rows: ScreenerRow[],
  metrics: Record<string, MarketMetricSnapshot>
) {
  if (Object.keys(metrics).length === 0) return rows
  return rows.map((row) => {
    const metric = metrics[row.key]
    if (!metric) return row
    return {
      ...row,
      latestPrice: Number.isFinite(metric.latestPrice) ? metric.latestPrice : row.latestPrice,
      changePct: metric.changePct ?? row.changePct,
      perf7d: metric.perf7d ?? row.perf7d,
      perf30d: metric.perf30d ?? row.perf30d,
    }
  })
}

async function fetchMarketMetricsForTargets(targets: ScannerMetricTarget[]) {
  const metrics: Record<string, MarketMetricSnapshot> = {}
  if (targets.length === 0) return metrics

  const chunkSize = 120
  for (let index = 0; index < targets.length; index += chunkSize) {
    const chunk = targets.slice(index, index + chunkSize)
    try {
      const keys = chunk.map((target) => target.key)
      const response = await fetchMarketMetrics(keys)
      for (const key of keys) {
        const item = response[key]
        if (!item) continue
        metrics[key] = {
          latestPrice: Number.isFinite(item.latest_price) ? (item.latest_price as number) : Number.NaN,
          changePct: toFiniteOrNull(item.change_pct),
          perf7d: toFiniteOrNull(item.perf_7d),
          perf30d: toFiniteOrNull(item.perf_30d),
        }
      }
    } catch {
      continue
    }
  }

  return metrics
}

function toFiniteOrNull(value: number | null | undefined) {
  return Number.isFinite(value) ? (value as number) : null
}

function sortColumns(columns: ColumnId[]) {
  return [...new Set(columns)].sort((left, right) => COLUMN_ORDER.indexOf(left) - COLUMN_ORDER.indexOf(right))
}

function addLockedColumns(columns: ColumnId[]) {
  const withLocked = [...columns]
  for (const column of LOCKED_COLUMNS) {
    if (!withLocked.includes(column)) withLocked.push(column)
  }
  return sortColumns(withLocked)
}

function makeWatchlistId(name: string) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") + `-${Date.now()}`
}
