"use client"

import { useEffect, useMemo, useState, type ReactNode } from "react"
import { useQuery } from "@tanstack/react-query"
import { Check, ListPlus, RefreshCw, Search, Settings2, Star, StarOff } from "lucide-react"
import {
  fetchLogs,
  fetchScanHistory,
  fetchSignals,
  type ApiSignal,
  type LogEntry,
  type ScanHistory,
} from "@/lib/api/client"
import { useBotHealth } from "@/lib/hooks/use-health"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
  | "signals24h"
  | "signalsTotal"
  | "bias"
  | "score"
  | "lastSeen"

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
  signals24h: { label: "Sinyal 24s", align: "right", sortValue: (row) => row.signals24h },
  signalsTotal: { label: "Sinyal Toplam", align: "right", sortValue: (row) => row.totalSignals },
  bias: { label: "Bias", align: "right", sortValue: (row) => row.buySignals - row.sellSignals },
  score: { label: "Skor", align: "left", sortValue: (row) => row.lastScore },
  lastSeen: { label: "Son Guncelleme", align: "right", sortValue: (row) => row.lastSeenTs },
}

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
    columns: ["symbol", "price", "changePct", "perf7d", "perf30d", "rsi14", "rsiFast", "cci", "bias", "lastSeen"],
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
    columns: ["symbol", "price", "changePct", "rsi14", "cci", "bias", "signals24h", "lastSignal", "lastSeen"],
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

export default function ScannerPage() {
  const health = useBotHealth()

  const [searchQuery, setSearchQuery] = useState("")
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL")
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("ALL")
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("ALL")
  const [timeframeFilter, setTimeframeFilter] = useState<string[]>([])

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
  const bistSignals = useMemo(() => bistSignalsQuery.data ?? EMPTY_SIGNALS, [bistSignalsQuery.data])
  const kriptoSignals = useMemo(() => kriptoSignalsQuery.data ?? EMPTY_SIGNALS, [kriptoSignalsQuery.data])
  const allSignals = useMemo(() => [...bistSignals, ...kriptoSignals].sort(sortSignalsByDateDesc), [bistSignals, kriptoSignals])
  const screenerRows = useMemo(() => buildScreenerRows(allSignals), [allSignals])

  const timeframeOptions = useMemo(() => {
    const values = new Set<string>()
    for (const row of screenerRows) values.add(row.lastTimeframe)
    return Array.from(values).sort((left, right) => timeframeRank(left) - timeframeRank(right))
  }, [screenerRows])

  const activeWatchlist = useMemo(
    () => watchlists.find((watchlist) => watchlist.id === activeWatchlistId) ?? watchlists[0] ?? null,
    [watchlists, activeWatchlistId]
  )
  const activeWatchSet = useMemo(() => new Set(activeWatchlist?.symbols ?? []), [activeWatchlist])

  const filteredRows = useMemo(() => {
    const keyword = searchQuery.trim().toUpperCase()
    const timeframeSet = new Set(timeframeFilter)
    return screenerRows.filter((row) => {
      if (marketFilter !== "ALL" && row.marketType !== marketFilter) return false
      if (strategyFilter !== "ALL" && row.lastStrategy !== strategyFilter) return false
      if (signalFilter !== "ALL" && row.lastSignalType !== signalFilter) return false
      if (timeframeSet.size > 0 && !timeframeSet.has(row.lastTimeframe)) return false
      if (keyword && !`${row.symbol} ${row.marketType}`.toUpperCase().includes(keyword)) return false
      if (watchOnly && !activeWatchSet.has(row.key)) return false
      return true
    })
  }, [screenerRows, searchQuery, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly, activeWatchSet])

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
  const warningLogCount = logs.filter((entry) => toLogLevel(entry.level) === "WARNING").length
  const errorLogCount = logs.filter((entry) => toLogLevel(entry.level) === "ERROR").length
  const signals24h = allSignals.filter((signal) => Date.now() - (parseDate(signal.createdAt)?.getTime() ?? 0) <= 86_400_000).length
  const buyCountFiltered = filteredRows.reduce((sum, row) => sum + row.buySignals, 0)
  const sellCountFiltered = filteredRows.reduce((sum, row) => sum + row.sellSignals, 0)

  const isRefreshing = scansQuery.isFetching || logsQuery.isFetching || bistSignalsQuery.isFetching || kriptoSignalsQuery.isFetching

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
        const prefs = JSON.parse(rawPrefs) as Partial<{ activeView: ViewKey; visibleColumns: ColumnId[]; sortBy: ColumnId; sortDirection: SortDirection; marketFilter: MarketFilter; strategyFilter: StrategyFilter; signalFilter: SignalFilter; timeframeFilter: string[]; watchOnly: boolean }>
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
    window.localStorage.setItem(PREF_STORAGE_KEY, JSON.stringify({ activeView, visibleColumns, sortBy, sortDirection, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly }))
  }, [hydrated, watchlists, activeWatchlistId, activeView, visibleColumns, sortBy, sortDirection, marketFilter, strategyFilter, signalFilter, timeframeFilter, watchOnly])

  useEffect(() => {
    if (!watchlistNotice) return
    const timer = window.setTimeout(() => setWatchlistNotice(null), 2400)
    return () => window.clearTimeout(timer)
  }, [watchlistNotice])

  const refreshAll = async () => {
    await Promise.all([scansQuery.refetch(), logsQuery.refetch(), bistSignalsQuery.refetch(), kriptoSignalsQuery.refetch()])
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
    const nextName = window.prompt("Yeni liste adi")
    if (!nextName || !nextName.trim()) return
    const model: WatchlistModel = { id: makeWatchlistId(nextName.trim()), name: nextName.trim(), symbols: [] }
    setWatchlists((prev) => [model, ...prev])
    setActiveWatchlistId(model.id)
    setWatchOnly(true)
    setWatchlistNotice("Yeni liste olusturuldu.")
  }

  const renameWatchlist = () => {
    if (!activeWatchlist) return
    const nextName = window.prompt("Liste adi", activeWatchlist.name)
    if (!nextName || !nextName.trim()) return
    upsertActiveWatchlist((watchlist) => ({ ...watchlist, name: nextName.trim() }))
    setWatchlistNotice("Liste adi guncellendi.")
  }

  const deleteWatchlist = () => {
    if (!activeWatchlist) return
    if (watchlists.length <= 1) {
      setWatchlistNotice("En az bir watchlist kalmali.")
      return
    }
    if (!window.confirm(`${activeWatchlist.name} silinsin mi?`)) return
    const fallback = watchlists.find((watchlist) => watchlist.id !== activeWatchlist.id)
    setWatchlists((prev) => prev.filter((watchlist) => watchlist.id !== activeWatchlist.id))
    if (fallback) setActiveWatchlistId(fallback.id)
    setWatchlistNotice("Watchlist silindi.")
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
            <select value={marketFilter} onChange={(event) => setMarketFilter(event.target.value as MarketFilter)} className="h-8 min-w-[130px] bg-base px-2 text-xs">
              <option value="ALL">Pazar: Tum</option>
              <option value="BIST">Pazar: BIST</option>
              <option value="Kripto">Pazar: Kripto</option>
            </select>
            <select value={strategyFilter} onChange={(event) => setStrategyFilter(event.target.value as StrategyFilter)} className="h-8 min-w-[150px] bg-base px-2 text-xs">
              <option value="ALL">Strateji: Tum</option>
              <option value="COMBO">Strateji: COMBO</option>
              <option value="HUNTER">Strateji: HUNTER</option>
            </select>
            <select value={signalFilter} onChange={(event) => setSignalFilter(event.target.value as SignalFilter)} className="h-8 min-w-[120px] bg-base px-2 text-xs">
              <option value="ALL">Tip: Tum</option>
              <option value="AL">Tip: AL</option>
              <option value="SAT">Tip: SAT</option>
            </select>
            <select value={activeWatchlist?.id ?? ""} onChange={(event) => setActiveWatchlistId(event.target.value)} className="h-8 min-w-[180px] bg-base px-2 text-xs">
              {watchlists.map((watchlist) => (
                <option key={watchlist.id} value={watchlist.id}>
                  {watchlist.name}
                </option>
              ))}
            </select>
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
            <button type="button" onClick={() => { setSearchQuery(""); setMarketFilter("ALL"); setStrategyFilter("ALL"); setSignalFilter("ALL"); setTimeframeFilter([]); setWatchOnly(false) }} className="h-8 rounded-sm border border-border bg-base px-2 text-xs text-muted-foreground hover:text-foreground">
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
                  <button key={column} type="button" onClick={() => toggleColumn(column)} className={cn("flex h-8 items-center justify-between rounded-sm border px-2 text-xs", enabled ? "border-foreground bg-raised text-foreground" : "border-border bg-base text-muted-foreground", LOCKED_COLUMNS.has(column) && "cursor-default")}>
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

        {sortedRows.length === 0 ? (
          <div className="px-3 py-12 text-center text-xs text-muted-foreground">Filtreye uygun kayit bulunamadi.</div>
        ) : (
          <div className="max-h-[640px] overflow-auto">
            <table className="w-full min-w-[1320px] text-[11px]">
              <thead className="sticky top-0 z-20 bg-surface">
                <tr className="border-b border-border">
                  {visibleColumnsSafe.map((column) => {
                    const meta = COLUMN_META[column]
                    return (
                      <th key={column} className={cn("px-2 py-2", meta.align === "right" ? "text-right" : "text-left")}>
                        <button type="button" onClick={() => handleSort(column)} className={cn("inline-flex items-center gap-1 text-[10px] font-medium uppercase tracking-[0.06em]", sortBy === column ? "text-foreground" : "text-muted-foreground")}>
                          <span>{meta.label}</span>
                          <span className="mono-numbers text-[10px]">{sortIconForColumn(column)}</span>
                        </button>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row) => {
                  const isSelected = row.key === selectedRow?.key
                  return (
                    <tr key={row.key} onClick={() => setSelectedRowKey(row.key)} className={cn("cursor-pointer border-b border-[rgba(255,255,255,0.04)] last:border-b-0 hover:bg-raised/40", isSelected && "border-l-2 border-foreground bg-raised/60")}>
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
      grouped.set(key, {
        row: {
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
          rsi14: readNumeric(signal.details, ["RSI", "rsi", "RSI14", "rsi14"]),
          rsiFast: readNumeric(signal.details, ["RSI_FAST", "rsi_fast", "RSI2", "rsi2"]),
          cci: readNumeric(signal.details, ["CCI", "cci"]),
        },
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

    if (ts >= current.row.lastSeenTs) {
      current.row.latestPrice = signal.price
      current.row.lastSignalType = signal.signalType
      current.row.lastStrategy = signal.strategy
      current.row.lastTimeframe = signal.timeframe
      current.row.lastScore = signal.score
      current.row.lastSeenIso = signal.createdAt
      current.row.lastSeenTs = ts
      current.row.rsi14 = readNumeric(signal.details, ["RSI", "rsi", "RSI14", "rsi14"])
      current.row.rsiFast = readNumeric(signal.details, ["RSI_FAST", "rsi_fast", "RSI2", "rsi2"])
      current.row.cci = readNumeric(signal.details, ["CCI", "cci"])
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
