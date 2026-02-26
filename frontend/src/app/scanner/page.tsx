"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import {
  fetchLogs,
  fetchScanHistory,
  fetchSignals,
  transformSignal,
  type LogEntry,
  type ScanHistory,
} from "@/lib/api/client"
import { useBotHealth } from "@/lib/hooks/use-health"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn, getTimeAgo } from "@/lib/utils"

type UiSignal = ReturnType<typeof transformSignal>
type MarketFilter = "ALL" | "BIST" | "Kripto"
type StrategyFilter = "ALL" | "COMBO" | "HUNTER"

const EMPTY_SCANS: ScanHistory[] = []
const EMPTY_LOGS: LogEntry[] = []
const EMPTY_SIGNALS: UiSignal[] = []

const KNOWN_TIMEFRAME_ORDER = [
  "15 DAKIKA",
  "30 DAKIKA",
  "1 SAAT",
  "4 SAAT",
  "1 GUN",
  "1 HAFTA",
  "2 HAFTA",
  "3 HAFTA",
  "1 AY",
]

export default function ScannerPage() {
  const health = useBotHealth()
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("ALL")
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("ALL")
  const [symbolQuery, setSymbolQuery] = useState("")

  const scansQuery = useQuery({
    queryKey: ["scanner", "scanHistory"],
    queryFn: () => fetchScanHistory(180),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  const logsQuery = useQuery({
    queryKey: ["scanner", "logs"],
    queryFn: () => fetchLogs(120),
    refetchInterval: 20_000,
    refetchIntervalInBackground: false,
  })

  const bistSignalsQuery = useQuery<UiSignal[]>({
    queryKey: ["scanner", "signals", "BIST"],
    queryFn: async () => {
      const rows = await fetchSignals({ market_type: "BIST", limit: 500 })
      return rows.map(transformSignal)
    },
    refetchInterval: 45_000,
    refetchIntervalInBackground: false,
  })

  const kriptoSignalsQuery = useQuery<UiSignal[]>({
    queryKey: ["scanner", "signals", "Kripto"],
    queryFn: async () => {
      const rows = await fetchSignals({ market_type: "Kripto", limit: 500 })
      return rows.map(transformSignal)
    },
    refetchInterval: 45_000,
    refetchIntervalInBackground: false,
  })

  const isRefreshing =
    scansQuery.isFetching ||
    logsQuery.isFetching ||
    bistSignalsQuery.isFetching ||
    kriptoSignalsQuery.isFetching

  const scans = useMemo(() => scansQuery.data ?? EMPTY_SCANS, [scansQuery.data])
  const logs = useMemo(() => logsQuery.data ?? EMPTY_LOGS, [logsQuery.data])
  const bistSignals = useMemo(() => bistSignalsQuery.data ?? EMPTY_SIGNALS, [bistSignalsQuery.data])
  const kriptoSignals = useMemo(() => kriptoSignalsQuery.data ?? EMPTY_SIGNALS, [kriptoSignalsQuery.data])
  const allSignals = useMemo(
    () => [...bistSignals, ...kriptoSignals].sort(sortBySignalDateDesc),
    [bistSignals, kriptoSignals]
  )

  const filteredSignals = useMemo(() => {
    const keyword = symbolQuery.trim().toLocaleUpperCase("tr-TR")
    return allSignals.filter((signal) => {
      if (marketFilter !== "ALL" && signal.marketType !== marketFilter) {
        return false
      }
      if (strategyFilter !== "ALL" && signal.strategy !== strategyFilter) {
        return false
      }
      if (keyword && !signal.symbol.toLocaleUpperCase("tr-TR").includes(keyword)) {
        return false
      }
      return true
    })
  }, [allSignals, marketFilter, strategyFilter, symbolQuery])

  const latestScan = scans[0] ?? null
  const scansWithDuration = scans.filter((item) => item.duration_seconds > 0)
  const averageDurationSec = average(scansWithDuration.map((item) => item.duration_seconds))
  const totalSymbolsScanned = scans.reduce((sum, item) => sum + item.symbols_scanned, 0)
  const totalSignalsFound = scans.reduce((sum, item) => sum + item.signals_found, 0)
  const totalErrors = scans.reduce((sum, item) => sum + item.errors_count, 0)
  const throughput = totalSymbolsScanned > 0 && scansWithDuration.length > 0
    ? totalSymbolsScanned / scansWithDuration.reduce((sum, item) => sum + item.duration_seconds, 0)
    : 0

  const referenceTime =
    parseDate(allSignals[0]?.createdAt)?.getTime() ??
    parseDate(latestScan?.created_at)?.getTime() ??
    0
  const signals24h = allSignals.filter((signal) => {
    const signalDate = parseDate(signal.createdAt)
    return signalDate ? referenceTime - signalDate.getTime() <= 86_400_000 : false
  }).length

  const errorLogCount = logs.filter((log) => toLogLevel(log.level) === "ERROR").length
  const warningLogCount = logs.filter((log) => toLogLevel(log.level) === "WARNING").length

  const scanRhythm = scans.slice(0, 36).reverse()

  const marketScanStats = useMemo(() => {
    const result = {
      BIST: { scans: 0, symbols: 0, signals: 0, errors: 0 },
      Kripto: { scans: 0, symbols: 0, signals: 0, errors: 0 },
      Diger: { scans: 0, symbols: 0, signals: 0, errors: 0 },
    }

    for (const scan of scans.slice(0, 90)) {
      const market = normalizeMarket(scan.scan_type)
      if (market === "BIST") {
        result.BIST.scans += 1
        result.BIST.symbols += scan.symbols_scanned
        result.BIST.signals += scan.signals_found
        result.BIST.errors += scan.errors_count
        continue
      }
      if (market === "Kripto") {
        result.Kripto.scans += 1
        result.Kripto.symbols += scan.symbols_scanned
        result.Kripto.signals += scan.signals_found
        result.Kripto.errors += scan.errors_count
        continue
      }
      result.Diger.scans += 1
      result.Diger.symbols += scan.symbols_scanned
      result.Diger.signals += scan.signals_found
      result.Diger.errors += scan.errors_count
    }

    return result
  }, [scans])

  const marketSignalStats = useMemo(() => {
    const result = {
      BIST: { total: 0, al: 0, sat: 0 },
      Kripto: { total: 0, al: 0, sat: 0 },
    }

    for (const signal of filteredSignals) {
      if (signal.marketType === "BIST") {
        result.BIST.total += 1
        if (signal.signalType === "AL") result.BIST.al += 1
        if (signal.signalType === "SAT") result.BIST.sat += 1
        continue
      }
      result.Kripto.total += 1
      if (signal.signalType === "AL") result.Kripto.al += 1
      if (signal.signalType === "SAT") result.Kripto.sat += 1
    }

    return result
  }, [filteredSignals])

  const timeframeRows = useMemo(() => {
    const matrix = new Map<
      string,
      {
        comboAl: number
        comboSat: number
        hunterAl: number
        hunterSat: number
      }
    >()

    for (const signal of filteredSignals) {
      const timeframe = normalizeTimeframe(signal.timeframe)
      const row = matrix.get(timeframe) ?? {
        comboAl: 0,
        comboSat: 0,
        hunterAl: 0,
        hunterSat: 0,
      }

      if (signal.strategy === "COMBO" && signal.signalType === "AL") row.comboAl += 1
      if (signal.strategy === "COMBO" && signal.signalType === "SAT") row.comboSat += 1
      if (signal.strategy === "HUNTER" && signal.signalType === "AL") row.hunterAl += 1
      if (signal.strategy === "HUNTER" && signal.signalType === "SAT") row.hunterSat += 1

      matrix.set(timeframe, row)
    }

    return Array.from(matrix.entries())
      .sort((left, right) => sortTimeframe(left[0], right[0]))
      .map(([timeframe, row]) => ({ timeframe, ...row }))
  }, [filteredSignals])

  const hotSymbols = useMemo(() => {
    const bySymbol = new Map<
      string,
      {
        symbol: string
        marketType: "BIST" | "Kripto"
        count: number
        latestType: "AL" | "SAT"
        latestPrice: number
        latestAt: string
      }
    >()

    for (const signal of allSignals) {
      const key = `${signal.marketType}:${signal.symbol}`
      const existing = bySymbol.get(key)
      if (!existing) {
        bySymbol.set(key, {
          symbol: signal.symbol,
          marketType: signal.marketType,
          count: 1,
          latestType: signal.signalType,
          latestPrice: signal.price,
          latestAt: signal.createdAt,
        })
        continue
      }

      existing.count += 1
      const currentDate = parseDate(signal.createdAt)
      const storedDate = parseDate(existing.latestAt)
      if ((currentDate?.getTime() ?? 0) > (storedDate?.getTime() ?? 0)) {
        existing.latestType = signal.signalType
        existing.latestPrice = signal.price
        existing.latestAt = signal.createdAt
      }
    }

    return Array.from(bySymbol.values())
      .sort((left, right) => {
        if (right.count !== left.count) return right.count - left.count
        return (parseDate(right.latestAt)?.getTime() ?? 0) - (parseDate(left.latestAt)?.getTime() ?? 0)
      })
      .slice(0, 14)
  }, [allSignals])

  const logRows = useMemo(() => {
    const highPriority = logs.filter((entry) => {
      const level = toLogLevel(entry.level)
      return level === "ERROR" || level === "WARNING"
    })
    return (highPriority.length > 0 ? highPriority : logs).slice(0, 90)
  }, [logs])

  const displayedScans = scans.slice(0, 40)
  const displayedSignals = filteredSignals.slice(0, 60)

  const refreshAll = async () => {
    await Promise.all([
      scansQuery.refetch(),
      logsQuery.refetch(),
      bistSignalsQuery.refetch(),
      kriptoSignalsQuery.refetch(),
    ])
  }

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3 md:p-4">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="label-uppercase">Tarayıcı Terminali</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Piyasa tarama ve sinyal değerlendirme merkezi</h1>
            <p className="mt-1 text-xs text-muted-foreground">
              Bot çıktıları tek ekranda birleştirildi: tarama ritmi, strateji matrisi, sıcak semboller ve kritik log akışı.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className={cn("signal-badge", health.isRunning ? "signal-buy" : "signal-sell")}>
              {health.isRunning ? "BOT AKTİF" : "BOT PASİF"}
            </span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-7"
              disabled={isRefreshing}
              onClick={refreshAll}
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
              Yenile
            </Button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-2 border border-border bg-surface md:grid-cols-3 xl:grid-cols-6">
        <RibbonCell
          label="Tarama Modu"
          value={health.isScanning ? "AKTİF" : "BEKLEME"}
          tone={health.isScanning ? "neutral" : undefined}
        />
        <RibbonCell label="Toplam Tarama" value={formatCount(health.scanCount)} />
        <RibbonCell label="24s Sinyal" value={formatCount(signals24h)} />
        <RibbonCell label="Ort. Süre" value={`${averageDurationSec.toFixed(1)} sn`} />
        <RibbonCell label="Throughput" value={`${throughput.toFixed(1)} sembol/sn`} />
        <RibbonCell
          label="Hata Satırı"
          value={`${errorLogCount} err • ${warningLogCount} warn`}
          tone={errorLogCount > 0 ? "loss" : warningLogCount > 0 ? "neutral" : "profit"}
        />
      </section>

      <section className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex min-h-0 flex-col gap-3">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <Panel title="Tarama Ritmi" subtitle="Son 36 tarama • soldan sağa eski → yeni">
              {scanRhythm.length === 0 ? (
                <EmptyText text="Tarama geçmişi yok." />
              ) : (
                <>
                  <div className="grid h-20 grid-flow-col auto-cols-fr items-end gap-1 border border-border bg-base px-2 py-2">
                    {scanRhythm.map((scan) => {
                      const maxSignals = Math.max(...scanRhythm.map((item) => item.signals_found), 1)
                      const ratio = scan.signals_found / maxSignals
                      const levelClass = barLevelClass(ratio)
                      const hasError = scan.errors_count > 0
                      const toneClass = hasError
                        ? "bg-loss"
                        : scan.signals_found > 0
                          ? "bg-profit"
                          : "bg-[rgba(255,255,255,0.18)]"

                      return (
                        <div
                          key={scan.id}
                          className={cn("w-full min-w-[4px]", levelClass, toneClass)}
                          title={`#${scan.id} • ${scan.signals_found} sinyal • ${scan.symbols_scanned} sembol`}
                        />
                      )
                    })}
                  </div>

                  <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] lg:grid-cols-4">
                    <MiniMetric label="Toplam tarama" value={formatCount(scans.length)} />
                    <MiniMetric label="Toplam sembol" value={formatCount(totalSymbolsScanned)} />
                    <MiniMetric label="Bulunan sinyal" value={formatCount(totalSignalsFound)} tone={totalSignalsFound > 0 ? "profit" : undefined} />
                    <MiniMetric label="Kayıtlı hata" value={formatCount(totalErrors)} tone={totalErrors > 0 ? "loss" : undefined} />
                  </div>
                </>
              )}
            </Panel>

            <Panel title="Pazar Hatları" subtitle="Son 90 tarama dağılımı">
              <div className="space-y-2">
                <MarketLane
                  name="BIST"
                  stats={marketScanStats.BIST}
                  signalStats={marketSignalStats.BIST}
                />
                <MarketLane
                  name="Kripto"
                  stats={marketScanStats.Kripto}
                  signalStats={marketSignalStats.Kripto}
                />
                {marketScanStats.Diger.scans > 0 ? (
                  <MarketLane
                    name="Diğer"
                    stats={marketScanStats.Diger}
                    signalStats={{ total: 0, al: 0, sat: 0 }}
                  />
                ) : null}
              </div>
            </Panel>
          </div>

          <Panel title="Tarama Akışı" subtitle="Son 40 tarama kaydı">
            {scansQuery.isLoading ? (
              <LoadingText text="Tarama geçmişi yükleniyor..." />
            ) : displayedScans.length === 0 ? (
              <EmptyText text="Tarama kaydı bulunamadı." />
            ) : (
              <div className="max-h-[360px] overflow-auto border border-border bg-base">
                <table className="w-full text-[11px]">
                  <thead className="sticky top-0 z-10 bg-surface">
                    <tr className="border-b border-border">
                      <th className="px-2 py-2 text-left font-medium text-muted-foreground">ID</th>
                      <th className="px-2 py-2 text-left font-medium text-muted-foreground">Pazar</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">Sembol</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">Sinyal</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">Hata</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">Süre</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">Zaman</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedScans.map((scan) => {
                      const market = normalizeMarket(scan.scan_type)
                      const timeLabel = formatClock(scan.created_at)
                      return (
                        <tr key={scan.id} className="border-b border-[rgba(255,255,255,0.04)] last:border-b-0">
                          <td className="mono-numbers px-2 py-1.5 text-muted-foreground">#{scan.id}</td>
                          <td className="px-2 py-1.5">
                            <span className={cn("signal-badge", market === "BIST" ? "signal-neutral" : market === "Kripto" ? "signal-buy" : "signal-neutral")}>
                              {market}
                            </span>
                          </td>
                          <td className="mono-numbers px-2 py-1.5 text-right text-foreground">{formatCount(scan.symbols_scanned)}</td>
                          <td className={cn("mono-numbers px-2 py-1.5 text-right", scan.signals_found > 0 ? "text-profit" : "text-muted-foreground")}>
                            {formatCount(scan.signals_found)}
                          </td>
                          <td className={cn("mono-numbers px-2 py-1.5 text-right", scan.errors_count > 0 ? "text-loss" : "text-muted-foreground")}>
                            {formatCount(scan.errors_count)}
                          </td>
                          <td className="mono-numbers px-2 py-1.5 text-right text-muted-foreground">{scan.duration_seconds.toFixed(1)}s</td>
                          <td className="mono-numbers px-2 py-1.5 text-right text-muted-foreground">{timeLabel}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel title="Strateji Matrisi" subtitle="Filtrelenmiş sinyallerin timeframe kırılımı">
            <div className="mb-2 grid gap-2 md:grid-cols-[160px_160px_minmax(0,1fr)]">
              <select
                value={marketFilter}
                onChange={(event) => setMarketFilter(event.target.value as MarketFilter)}
                className="h-8 bg-base px-2 text-xs"
              >
                <option value="ALL">Pazar: Tümü</option>
                <option value="BIST">Pazar: BIST</option>
                <option value="Kripto">Pazar: Kripto</option>
              </select>

              <select
                value={strategyFilter}
                onChange={(event) => setStrategyFilter(event.target.value as StrategyFilter)}
                className="h-8 bg-base px-2 text-xs"
              >
                <option value="ALL">Strateji: Tümü</option>
                <option value="COMBO">Strateji: COMBO</option>
                <option value="HUNTER">Strateji: HUNTER</option>
              </select>

              <Input
                value={symbolQuery}
                onChange={(event) => setSymbolQuery(event.target.value)}
                className="h-8 text-xs"
                placeholder="Sembol filtrele (örn: THYAO, BTC)"
              />
            </div>

            {timeframeRows.length === 0 ? (
              <EmptyText text="Filtre ile eşleşen sinyal yok." />
            ) : (
              <div className="max-h-[280px] overflow-auto border border-border bg-base">
                <table className="w-full text-[11px]">
                  <thead className="sticky top-0 z-10 bg-surface">
                    <tr className="border-b border-border">
                      <th className="px-2 py-2 text-left font-medium text-muted-foreground">Timeframe</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">COMBO AL</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">COMBO SAT</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">HUNTER AL</th>
                      <th className="px-2 py-2 text-right font-medium text-muted-foreground">HUNTER SAT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {timeframeRows.map((row) => (
                      <tr key={row.timeframe} className="border-b border-[rgba(255,255,255,0.04)] last:border-b-0">
                        <td className="px-2 py-1.5 text-foreground">{row.timeframe}</td>
                        <td className={cn("mono-numbers px-2 py-1.5 text-right", row.comboAl > 0 ? "text-profit" : "text-muted-foreground")}>{formatCount(row.comboAl)}</td>
                        <td className={cn("mono-numbers px-2 py-1.5 text-right", row.comboSat > 0 ? "text-loss" : "text-muted-foreground")}>{formatCount(row.comboSat)}</td>
                        <td className={cn("mono-numbers px-2 py-1.5 text-right", row.hunterAl > 0 ? "text-profit" : "text-muted-foreground")}>{formatCount(row.hunterAl)}</td>
                        <td className={cn("mono-numbers px-2 py-1.5 text-right", row.hunterSat > 0 ? "text-loss" : "text-muted-foreground")}>{formatCount(row.hunterSat)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>

        <div className="flex min-h-0 flex-col gap-3">
          <Panel title="Sıcak Semboller" subtitle="Son 1000 sinyalde frekans">
            {hotSymbols.length === 0 ? (
              <EmptyText text="Sembol verisi bulunamadı." />
            ) : (
              <div className="max-h-[300px] overflow-auto border border-border bg-base">
                <ul className="divide-y divide-[rgba(255,255,255,0.04)]">
                  {hotSymbols.map((item, index) => (
                    <li
                      key={`${item.marketType}:${item.symbol}`}
                      className={cn(
                        "grid grid-cols-[1fr_auto] gap-2 px-2 py-2 text-[11px]",
                        index === 0 && "border-l-2 border-foreground bg-raised/60"
                      )}
                    >
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">{item.symbol}</span>
                          <span className={cn("signal-badge", item.latestType === "AL" ? "signal-buy" : "signal-sell")}>
                            {item.latestType}
                          </span>
                          <span className="label-uppercase">{item.marketType}</span>
                        </div>
                        <div className="mt-1 text-[10px] text-muted-foreground">{getTimeAgo(item.latestAt)}</div>
                      </div>
                      <div className="text-right">
                        <div className="mono-numbers text-foreground">{formatCount(item.count)}</div>
                        <div className="mono-numbers text-[10px] text-muted-foreground">{formatPrice(item.latestPrice)}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>

          <Panel title="Canlı Sinyal Akışı" subtitle="Filtre sonrası son 60 kayıt">
            {displayedSignals.length === 0 ? (
              <EmptyText text="Sinyal akışı bulunamadı." />
            ) : (
              <div className="max-h-[320px] overflow-auto border border-border bg-base">
                <ul className="divide-y divide-[rgba(255,255,255,0.04)]">
                  {displayedSignals.map((signal) => (
                    <li key={signal.id} className="px-2 py-2 text-[11px]">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex min-w-0 items-center gap-2">
                          <span className={cn("signal-badge", signal.signalType === "AL" ? "signal-buy" : "signal-sell")}>
                            {signal.signalType}
                          </span>
                          <span className="font-medium text-foreground">{signal.symbol}</span>
                          <span className="label-uppercase">{signal.strategy}</span>
                        </div>
                        <span className="mono-numbers text-[10px] text-muted-foreground">{formatClock(signal.createdAt)}</span>
                      </div>
                      <div className="mt-1 flex items-center justify-between gap-2">
                        <span className="text-[10px] text-muted-foreground">{normalizeTimeframe(signal.timeframe)}</span>
                        <span className="mono-numbers text-[10px] text-muted-foreground">{formatPrice(signal.price)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>

          <Panel title="Kritik Log Akışı" subtitle="Uyarı ve hata satırları">
            {logsQuery.isLoading ? (
              <LoadingText text="Log akışı yükleniyor..." />
            ) : logRows.length === 0 ? (
              <EmptyText text="Log bulunamadı." />
            ) : (
              <div className="max-h-[340px] overflow-auto border border-border bg-base">
                <ul className="divide-y divide-[rgba(255,255,255,0.04)]">
                  {logRows.map((entry, index) => {
                    const level = toLogLevel(entry.level)
                    return (
                      <li key={`${entry.timestamp}-${index}`} className="grid grid-cols-[70px_62px_1fr] gap-2 px-2 py-1.5 text-[11px]">
                        <span className="mono-numbers text-muted-foreground">{formatClock(entry.timestamp)}</span>
                        <span className={cn("mono-numbers", level === "ERROR" ? "text-loss" : level === "WARNING" ? "text-neutral" : "text-muted-foreground")}>
                          {level}
                        </span>
                        <span className="text-foreground">{entry.message}</span>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}
          </Panel>
        </div>
      </section>

      <section className="border border-border bg-surface px-3 py-2 text-[10px] text-muted-foreground">
        Son tarama: {latestScan ? `${formatClock(latestScan.created_at)} • ${latestScan.symbols_scanned} sembol • ${latestScan.signals_found} sinyal` : "--"}
      </section>
    </div>
  )
}

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <section className="border border-border bg-surface">
      <div className="border-b border-border px-3 py-2">
        <div className="label-uppercase">{title}</div>
        {subtitle ? <p className="mt-1 text-[10px] text-muted-foreground">{subtitle}</p> : null}
      </div>
      <div className="p-2">{children}</div>
    </section>
  )
}

function RibbonCell({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "profit" | "loss" | "neutral"
}) {
  return (
    <div className="flex h-16 min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0">
      <span className="label-uppercase">{label}</span>
      <span
        className={cn(
          "mono-numbers truncate text-[16px] font-semibold",
          tone === "profit" && "text-profit",
          tone === "loss" && "text-loss",
          tone === "neutral" && "text-neutral"
        )}
      >
        {value}
      </span>
    </div>
  )
}

function MiniMetric({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "profit" | "loss"
}) {
  return (
    <div className="border border-border bg-surface px-2 py-1.5">
      <div className="label-uppercase">{label}</div>
      <div className={cn("mono-numbers mt-1 text-sm", tone === "profit" && "text-profit", tone === "loss" && "text-loss")}>{value}</div>
    </div>
  )
}

function MarketLane({
  name,
  stats,
  signalStats,
}: {
  name: string
  stats: { scans: number; symbols: number; signals: number; errors: number }
  signalStats: { total: number; al: number; sat: number }
}) {
  return (
    <div className="border border-border bg-base p-2">
      <div className="mb-2 flex items-center justify-between">
        <span className="label-uppercase">{name}</span>
        <span className="mono-numbers text-[10px] text-muted-foreground">{formatCount(stats.scans)} tarama</span>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <span className="text-muted-foreground">Sembol</span>
        <span className="mono-numbers text-right">{formatCount(stats.symbols)}</span>
        <span className="text-muted-foreground">Bulunan sinyal</span>
        <span className="mono-numbers text-right text-profit">{formatCount(stats.signals)}</span>
        <span className="text-muted-foreground">Log hata</span>
        <span className={cn("mono-numbers text-right", stats.errors > 0 ? "text-loss" : "text-muted-foreground")}>{formatCount(stats.errors)}</span>
        <span className="text-muted-foreground">AL / SAT</span>
        <span className="mono-numbers text-right">
          <span className="text-profit">{formatCount(signalStats.al)}</span>
          <span className="text-muted-foreground"> / </span>
          <span className="text-loss">{formatCount(signalStats.sat)}</span>
        </span>
      </div>
    </div>
  )
}

function LoadingText({ text }: { text: string }) {
  return <div className="px-2 py-6 text-center text-xs text-muted-foreground">{text}</div>
}

function EmptyText({ text }: { text: string }) {
  return <div className="px-2 py-6 text-center text-xs text-muted-foreground">{text}</div>
}

function sortBySignalDateDesc(left: UiSignal, right: UiSignal) {
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
  return date.toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
  })
}

function formatCount(value: number) {
  return new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 0 }).format(value)
}

function formatPrice(value: number) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function average(values: number[]) {
  if (values.length === 0) return 0
  return values.reduce((sum, value) => sum + value, 0) / values.length
}

function normalizeMarket(scanType: string | null | undefined): "BIST" | "Kripto" | "Diger" {
  const text = (scanType ?? "").toLocaleUpperCase("tr-TR")
  if (text.includes("BIST")) return "BIST"
  if (text.includes("KRIPTO")) return "Kripto"
  return "Diger"
}

function normalizeTimeframe(timeframe: string | null | undefined) {
  if (!timeframe) return "-"
  const clean = timeframe
    .trim()
    .toLocaleUpperCase("tr-TR")
    .replace("SAATLİK", "SAAT")
    .replace("GÜNLÜK", "1 GUN")
    .replace("HAFTALIK", "HAFTA")
    .replace("AYLIK", "AY")
    .replace("Ü", "U")
    .replace("İ", "I")
    .replace("Ö", "O")
    .replace("Ş", "S")
    .replace("Ç", "C")
    .replace("Ğ", "G")

  return clean
}

function timeframeToMinutes(timeframe: string) {
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

function sortTimeframe(left: string, right: string) {
  const leftMinutes = timeframeToMinutes(left)
  const rightMinutes = timeframeToMinutes(right)
  if (leftMinutes === rightMinutes) return left.localeCompare(right, "tr")
  return leftMinutes - rightMinutes
}

function toLogLevel(level: string | null | undefined): "INFO" | "WARNING" | "ERROR" {
  const text = (level ?? "").toLocaleUpperCase("tr-TR")
  if (text.includes("ERR")) return "ERROR"
  if (text.includes("WARN")) return "WARNING"
  return "INFO"
}

function barLevelClass(ratio: number) {
  if (ratio <= 0.08) return "h-1"
  if (ratio <= 0.16) return "h-2"
  if (ratio <= 0.24) return "h-3"
  if (ratio <= 0.32) return "h-4"
  if (ratio <= 0.4) return "h-5"
  if (ratio <= 0.48) return "h-6"
  if (ratio <= 0.56) return "h-7"
  if (ratio <= 0.64) return "h-8"
  if (ratio <= 0.72) return "h-10"
  if (ratio <= 0.8) return "h-12"
  if (ratio <= 0.9) return "h-14"
  return "h-16"
}
