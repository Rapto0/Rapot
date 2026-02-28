"use client"

import { useEffect, useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Brain, RefreshCw, Target } from "lucide-react"

import {
  fetchAIAnalysis,
  fetchTicker,
  type ApiStrategyInspectorTimeframe,
  type StructuredAIAnalysisResponse,
  type TickerData,
} from "@/lib/api/client"
import { useAnalyses, useRecentAnalyses, type AIAnalysis } from "@/lib/hooks/use-analyses"
import { useSignals, type Signal } from "@/lib/hooks/use-signals"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn, getTimeAgo } from "@/lib/utils"

type MarketType = "AUTO" | "BIST" | "Kripto"
type StrategyType = "COMBO" | "HUNTER"
type TimeframeType = "ALL" | "1D" | "1W" | "2W" | "3W" | "1M"

type WatchRow = {
  key: string
  symbol: string
  marketType: "BIST" | "Kripto"
  price: number
  changePercent: number | null
  signalType: "AL" | "SAT"
  strategy: "COMBO" | "HUNTER"
  timeframe: string
  score: string
  specialTag: Signal["specialTag"]
  createdAt: string
}

const EMPTY_RESULT: StructuredAIAnalysisResponse | null = null

export function AITerminal() {
  const [selectedKey, setSelectedKey] = useState<string>("")
  const [symbol, setSymbol] = useState("")
  const [marketType, setMarketType] = useState<MarketType>("AUTO")
  const [strategy, setStrategy] = useState<StrategyType>("HUNTER")
  const [timeframe, setTimeframe] = useState<TimeframeType>("ALL")
  const [result, setResult] = useState<StructuredAIAnalysisResponse | null>(EMPTY_RESULT)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const tickerQuery = useQuery({
    queryKey: ["ticker", "ai-terminal"],
    queryFn: fetchTicker,
    refetchInterval: 30_000,
  })

  const signalsQuery = useSignals({ limit: 240 })
  const recentAnalysesQuery = useRecentAnalyses(16)

  const watchRows = useMemo(
    () => buildWatchRows(signalsQuery.data ?? [], tickerQuery.data ?? []),
    [signalsQuery.data, tickerQuery.data]
  )

  useEffect(() => {
    if (!selectedKey && watchRows[0]) {
      setSelectedKey(watchRows[0].key)
    }
  }, [selectedKey, watchRows])

  const selectedRow = useMemo(
    () => watchRows.find((row) => row.key === selectedKey) ?? watchRows[0] ?? null,
    [selectedKey, watchRows]
  )

  useEffect(() => {
    if (!selectedRow) return
    setSymbol(selectedRow.symbol)
    setMarketType(selectedRow.marketType)
    setStrategy(selectedRow.strategy)
  }, [selectedRow])

  const symbolSignals = useMemo(() => {
    if (!selectedRow) return []
    return (signalsQuery.data ?? [])
      .filter(
        (signal) =>
          signal.symbol === selectedRow.symbol && signal.marketType === selectedRow.marketType
      )
      .slice(0, 12)
  }, [selectedRow, signalsQuery.data])

  const symbolAnalysesQuery = useAnalyses({
    symbol: selectedRow?.symbol,
    marketType: selectedRow?.marketType,
    limit: 12,
  })

  const averageConfidence = useMemo(() => {
    const scores = (recentAnalysesQuery.data ?? [])
      .map((analysis) => analysis.confidenceScore)
      .filter((value): value is number => typeof value === "number")
    if (scores.length === 0) return "--"
    return `${Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)}`
  }, [recentAnalysesQuery.data])

  const refreshPageData = async () => {
    await Promise.all([
      tickerQuery.refetch(),
      signalsQuery.refetch(),
      recentAnalysesQuery.refetch(),
      symbolAnalysesQuery.refetch(),
    ])
  }

  const runAnalysis = async () => {
    const normalizedSymbol = symbol.trim().toUpperCase()
    if (!normalizedSymbol) {
      setError("Sembol girin.")
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const analysis = await fetchAIAnalysis({
        symbol: normalizedSymbol,
        market_type: marketType,
        strategy,
        timeframe,
      })
      setResult(analysis)
    } catch (analysisError) {
      setResult(null)
      setError(
        analysisError instanceof Error ? analysisError.message : "AI analizi alinamadi."
      )
    } finally {
      setIsLoading(false)
    }
  }

  const applySelectedRow = () => {
    if (!selectedRow) return
    setSymbol(selectedRow.symbol)
    setMarketType(selectedRow.marketType)
    setStrategy(selectedRow.strategy)
    setTimeframe("ALL")
  }

  const loadAnalysisContext = (analysis: AIAnalysis) => {
    setSymbol(analysis.symbol)
    setMarketType(analysis.marketType)
    setStrategy(resolveAnalysisStrategy(analysis.scenarioName))
    setTimeframe("ALL")
  }

  const structured = result?.structured_analysis ?? null
  const inspectionRows = result?.inspection.timeframes ?? []
  const isRefreshing = tickerQuery.isFetching || signalsQuery.isFetching || recentAnalysesQuery.isFetching

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface px-4 py-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">AI</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em] text-foreground">
              Manuel yorum motoru
            </h1>
            <p className="mt-1 text-xs text-muted-foreground">
              Gercek teknik baglam, secilen strateji ve periyot setiyle tek bir calisma alani.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={refreshPageData} disabled={isRefreshing}>
              <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
              Veri tazele
            </Button>
          </div>
        </div>
      </section>

      <section className="grid min-h-16 grid-cols-2 border border-border bg-surface md:grid-cols-4">
        <RibbonStat label="Izlenen" value={`${watchRows.length}`} />
        <RibbonStat label="AI Kaydi" value={`${recentAnalysesQuery.data?.length ?? 0}`} />
        <RibbonStat label="Ort. Guven" value={averageConfidence} tone="profit" />
        <RibbonStat
          label="Secili"
          value={selectedRow ? `${selectedRow.symbol} / ${selectedRow.strategy}` : "--"}
        />
      </section>

      <section className="grid gap-3 xl:grid-cols-[290px_minmax(0,1fr)_360px]">
        <aside className="border border-border bg-surface">
          <div className="flex h-10 items-center justify-between border-b border-border px-3">
            <span className="label-uppercase">Sembol akisi</span>
            <span className="text-[10px] text-muted-foreground">{watchRows.length} kayit</span>
          </div>
          <div className="max-h-[calc(100vh-220px)] overflow-auto">
            {watchRows.length === 0 ? (
              <div className="px-3 py-8 text-center text-xs text-muted-foreground">
                Sembol akisi bulunamadi.
              </div>
            ) : (
              watchRows.map((row) => {
                const active = row.key === selectedRow?.key
                return (
                  <button
                    key={row.key}
                    type="button"
                    onClick={() => setSelectedKey(row.key)}
                    className={cn(
                      "grid w-full grid-cols-[1fr_88px] gap-2 border-b border-[rgba(255,255,255,0.04)] px-3 py-2 text-left hover:bg-raised",
                      active && "border-l-2 border-l-foreground bg-raised"
                    )}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate text-xs font-semibold text-foreground">{row.symbol}</span>
                        <span className={cn("signal-badge", row.marketType === "BIST" ? "bg-[rgba(255,255,255,0.06)] text-foreground" : "bg-[rgba(59,130,246,0.12)] text-[var(--chart-1)]")}>
                          {row.marketType}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>{row.strategy}</span>
                        <span>{row.timeframe}</span>
                        {row.specialTag ? <span>{specialTagLabel(row.specialTag)}</span> : null}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="mono-numbers text-xs text-foreground">{formatInstrumentPrice(row)}</div>
                      <div className={cn("mono-numbers mt-1 text-[10px]", row.changePercent !== null && row.changePercent >= 0 ? "text-profit" : row.changePercent !== null ? "text-loss" : "text-muted-foreground")}>
                        {formatChange(row.changePercent)}
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">{getTimeAgo(row.createdAt)}</div>
                    </div>
                  </button>
                )
              })
            )}
          </div>
        </aside>

        <main className="flex min-w-0 flex-col gap-3">
          <section className="border border-border bg-surface">
            <div className="border-b border-border px-3 py-2">
              <span className="label-uppercase">Komut satiri</span>
            </div>
            <div className="grid gap-2 p-3 xl:grid-cols-[minmax(0,220px)_140px_150px_150px_auto_auto]">
              <Input
                value={symbol}
                onChange={(event) => setSymbol(event.target.value.toUpperCase())}
                placeholder="THYAO veya BTCUSDT"
                className="h-9 text-xs uppercase"
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    event.preventDefault()
                    void runAnalysis()
                  }
                }}
              />

              <select
                value={strategy}
                onChange={(event) => setStrategy(event.target.value as StrategyType)}
                className="h-9 border border-border bg-base px-2 text-xs text-foreground outline-none"
              >
                <option value="HUNTER">HUNTER</option>
                <option value="COMBO">COMBO</option>
              </select>

              <select
                value={marketType}
                onChange={(event) => setMarketType(event.target.value as MarketType)}
                className="h-9 border border-border bg-base px-2 text-xs text-foreground outline-none"
              >
                <option value="AUTO">AUTO</option>
                <option value="BIST">BIST</option>
                <option value="Kripto">Kripto</option>
              </select>

              <select
                value={timeframe}
                onChange={(event) => setTimeframe(event.target.value as TimeframeType)}
                className="h-9 border border-border bg-base px-2 text-xs text-foreground outline-none"
              >
                <option value="ALL">Tum Periyotlar</option>
                <option value="1D">1 Gunluk</option>
                <option value="1W">1 Haftalik</option>
                <option value="2W">2 Haftalik</option>
                <option value="3W">3 Haftalik</option>
                <option value="1M">1 Aylik</option>
              </select>

              <Button type="button" variant="outline" className="h-9 text-xs" onClick={runAnalysis} disabled={isLoading}>
                <Brain className="mr-1.5 h-3.5 w-3.5" />
                {isLoading ? "Yorumlaniyor" : "AI Yorumla"}
              </Button>

              <Button type="button" variant="outline" className="h-9 text-xs" onClick={applySelectedRow} disabled={!selectedRow}>
                <Target className="mr-1.5 h-3.5 w-3.5" />
                Secili satir
              </Button>
            </div>
          </section>

          {error ? (
            <section className="border border-[rgba(239,68,68,0.35)] bg-surface px-3 py-3 text-xs text-loss">
              {error}
            </section>
          ) : null}

          {!result && !error ? (
            <section className="border border-dashed border-border bg-surface px-4 py-12">
              <div className="label-uppercase">Hazir</div>
              <div className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
                Sol akistan bir sembol sec, strateji ve periyot ayarla, sonra yorumu calistir.
                Bu ekran sadece gercek teknik baglam ve haber birlesimiyle yorum uretir.
              </div>
            </section>
          ) : null}

          {result && structured ? (
            <>
              <section className="grid gap-3 xl:grid-cols-[minmax(0,1.45fr)_320px]">
                <div className="border border-border bg-surface p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border pb-3">
                    <div>
                      <div className="label-uppercase">AI cikti</div>
                      <div className="mt-1 flex items-center gap-2">
                        <span className={cn("signal-badge", toneClass(toneFromLabel(structured.sentiment_label)))}>
                          {structured.sentiment_label}
                        </span>
                        <span className="mono-numbers text-sm text-foreground">
                          Guven {structured.confidence_score}
                        </span>
                        <span className="mono-numbers text-sm text-muted-foreground">
                          Risk {structured.risk_level}
                        </span>
                      </div>
                    </div>
                    <div className="text-right text-[10px] text-muted-foreground">
                      <div>{result.symbol} / {result.market_type}</div>
                      <div>{timeframeLabel(result.timeframe)}</div>
                      <div>{getTimeAgo(result.updated_at)}</div>
                    </div>
                  </div>

                  <div className="mt-4 max-w-4xl text-sm leading-7 text-foreground">
                    {structured.explanation}
                  </div>

                  <div className="mt-4 grid gap-2">
                    {structured.summary.map((item, index) => (
                      <div
                        key={`${item}:${index}`}
                        className="border border-[rgba(255,255,255,0.04)] bg-base px-3 py-2 text-xs text-foreground"
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-3">
                  <section className="border border-border bg-surface p-3">
                    <div className="label-uppercase">Model izi</div>
                    <div className="mt-3 grid gap-2">
                      <MetricRow label="Provider" value={structured.provider || "--"} />
                      <MetricRow label="Model" value={structured.model || "--"} />
                      <MetricRow label="Prompt" value={structured.prompt_version || "--"} />
                      <MetricRow label="Teknik bias" value={`${structured.technical_view.bias} / ${structured.technical_view.strength}`} />
                      <MetricRow label="Haber bias" value={`${structured.news_view.bias} / ${structured.news_view.strength}`} />
                      <MetricRow label="Baslik" value={`${structured.news_view.headline_count}`} />
                    </div>
                  </section>

                  <section className="border border-border bg-surface p-3">
                    <div className="label-uppercase">Seviye matrisi</div>
                    <div className="mt-3 grid gap-2 lg:grid-cols-2 xl:grid-cols-1">
                      <LevelCluster title="Destek" values={structured.key_levels.support} tone="profit" />
                      <LevelCluster title="Direnc" values={structured.key_levels.resistance} tone="loss" />
                    </div>
                  </section>
                </div>
              </section>

              <section className="border border-border bg-surface">
                <div className="border-b border-border px-3 py-2">
                  <span className="label-uppercase">Periyot matrisi</span>
                </div>
                <div className="grid gap-px bg-[rgba(255,255,255,0.04)] md:grid-cols-2 xl:grid-cols-5">
                  {inspectionRows.map((timeframeRow) => (
                    <TimeframeMatrixCard key={timeframeRow.code} timeframe={timeframeRow} />
                  ))}
                </div>
              </section>
            </>
          ) : null}
        </main>

        <aside className="flex min-h-0 flex-col gap-3">
          <section className="border border-border bg-surface">
            <div className="border-b border-border px-3 py-2">
              <span className="label-uppercase">Secili sembol sinyalleri</span>
            </div>
            <div className="max-h-[300px] overflow-auto">
              {symbolSignals.length === 0 ? (
                <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                  Kayit bulunamadi.
                </div>
              ) : (
                symbolSignals.map((signal) => (
                  <button
                    key={signal.id}
                    type="button"
                    onClick={() => {
                      setSymbol(signal.symbol)
                      setMarketType(signal.marketType)
                      setStrategy(signal.strategy)
                      setTimeframe(toCommandTimeframe(signal.timeframe))
                    }}
                    className="block w-full border-b border-[rgba(255,255,255,0.04)] px-3 py-2 text-left last:border-b-0 hover:bg-raised"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className={cn("signal-badge", signal.signalType === "AL" ? "signal-buy" : "signal-sell")}>
                        {signal.signalType}
                      </span>
                      <span className="text-[10px] text-muted-foreground">{signal.timeframe}</span>
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-foreground">
                      <span>{signal.strategy}</span>
                      {signal.specialTag ? <span className="text-muted-foreground">{specialTagLabel(signal.specialTag)}</span> : null}
                    </div>
                    <div className="mt-1 mono-numbers text-[10px] text-muted-foreground">
                      {signal.score || "--"} / {getTimeAgo(signal.createdAt)}
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="min-h-0 flex-1 border border-border bg-surface">
            <div className="border-b border-border px-3 py-2">
              <span className="label-uppercase">AI arsivi</span>
            </div>
            <div className="max-h-[420px] overflow-auto">
              {symbolAnalysesQuery.isLoading ? (
                <div className="px-3 py-6 text-center text-xs text-muted-foreground">Yukleniyor...</div>
              ) : (symbolAnalysesQuery.data?.length ?? 0) === 0 ? (
                <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                  Secili sembol icin AI kaydi yok.
                </div>
              ) : (
                (symbolAnalysesQuery.data ?? []).map((analysis) => (
                  <button
                    key={analysis.id}
                    type="button"
                    onClick={() => loadAnalysisContext(analysis)}
                    className="block w-full border-b border-[rgba(255,255,255,0.04)] px-3 py-2 text-left last:border-b-0 hover:bg-raised"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="truncate text-xs font-semibold text-foreground">
                          {analysis.scenarioName || analysis.symbol}
                        </div>
                        <div className="mt-1 text-[10px] text-muted-foreground">
                          {analysis.model || "--"}
                        </div>
                      </div>
                      <span className={cn("signal-badge", toneClass(toneFromLabel(analysis.sentimentLabel)))}>
                        {analysis.sentimentLabel || "--"}
                      </span>
                    </div>
                    <div className="mt-2 flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                      <span>Guven {analysis.confidenceScore ?? "--"}</span>
                      <span>{getTimeAgo(analysis.createdAt)}</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </section>
        </aside>
      </section>
    </div>
  )
}

function RibbonStat({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "profit" | "loss"
}) {
  return (
    <div className="border-r border-border px-3 py-2 last:border-r-0">
      <div className="label-uppercase">{label}</div>
      <div className={cn("mono-numbers mt-1 text-sm text-foreground", tone === "profit" && "text-profit", tone === "loss" && "text-loss")}>
        {value}
      </div>
    </div>
  )
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border border-[rgba(255,255,255,0.04)] bg-base px-2 py-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="mono-numbers text-right text-foreground">{value}</span>
    </div>
  )
}

function LevelCluster({
  title,
  values,
  tone,
}: {
  title: string
  values: string[]
  tone: "profit" | "loss"
}) {
  return (
    <div className="border border-[rgba(255,255,255,0.04)] bg-base p-2">
      <div className="label-uppercase">{title}</div>
      <div className="mt-2 flex flex-wrap gap-2">
        {(values.length > 0 ? values : ["--"]).map((value) => (
          <span key={`${title}:${value}`} className={cn("signal-badge", tone === "profit" ? "signal-buy" : "signal-sell")}>
            {value}
          </span>
        ))}
      </div>
    </div>
  )
}

function TimeframeMatrixCard({ timeframe }: { timeframe: ApiStrategyInspectorTimeframe }) {
  return (
    <div className="bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="label-uppercase">{timeframe.label}</div>
          <div className="mono-numbers mt-1 text-[10px] text-muted-foreground">{timeframe.code}</div>
        </div>
        <span className={cn("signal-badge", toneClass(toneFromLabel(timeframe.signal_status)))}>
          {timeframe.signal_status}
        </span>
      </div>
      <div className="mt-3 grid gap-1 text-[11px]">
        <MatrixRow label="Fiyat" value={formatTimeframePrice(timeframe.price)} />
        <MatrixRow label="Tarih" value={timeframe.date || "--"} />
        <MatrixRow label={timeframe.primary_score_label} value={timeframe.primary_score || "--"} />
        <MatrixRow label={timeframe.secondary_score_label} value={timeframe.secondary_score || "--"} />
        <MatrixRow label="Aktif" value={timeframe.active_indicators || "--"} />
      </div>
    </div>
  )
}

function MatrixRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-[rgba(255,255,255,0.04)] py-1 last:border-b-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="mono-numbers text-right text-foreground">{value}</span>
    </div>
  )
}

function buildWatchRows(signals: Signal[], tickers: TickerData[]): WatchRow[] {
  const tickerMap = new Map(tickers.map((ticker) => [ticker.symbol, ticker]))
  const rows: WatchRow[] = []
  const seen = new Set<string>()

  const orderedSignals = [...signals].sort(
    (left, right) => new Date(right.createdAt).getTime() - new Date(left.createdAt).getTime()
  )

  for (const signal of orderedSignals) {
    const key = `${signal.marketType}:${signal.symbol}`
    if (seen.has(key)) continue
    seen.add(key)

    const ticker = tickerMap.get(signal.symbol)
    rows.push({
      key,
      symbol: signal.symbol,
      marketType: signal.marketType,
      price: ticker?.price ?? signal.price,
      changePercent: typeof ticker?.changePercent === "number" ? ticker.changePercent : null,
      signalType: signal.signalType,
      strategy: signal.strategy,
      timeframe: signal.timeframe,
      score: signal.score,
      specialTag: signal.specialTag,
      createdAt: signal.createdAt,
    })

    if (rows.length >= 48) break
  }

  return rows
}

function formatInstrumentPrice(row: WatchRow): string {
  const symbol = row.marketType === "Kripto" ? "$" : "₺"
  const maximumFractionDigits = row.marketType === "Kripto" ? 4 : 2
  return `${symbol}${row.price.toLocaleString("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits,
  })}`
}

function formatChange(value: number | null): string {
  if (value === null) return "--"
  const prefix = value >= 0 ? "+" : ""
  return `${prefix}${value.toFixed(2)}%`
}

function specialTagLabel(value: Signal["specialTag"]) {
  switch (value) {
    case "BELES":
      return "BELES"
    case "COK_UCUZ":
      return "COK UCUZ"
    case "PAHALI":
      return "PAHALI"
    case "FAHIS_FIYAT":
      return "FAHIS"
    default:
      return "--"
  }
}

function timeframeLabel(value: string) {
  switch (value) {
    case "ALL":
      return "Tum Periyotlar"
    case "1D":
      return "1 Gunluk"
    case "1W":
    case "W-FRI":
      return "1 Haftalik"
    case "2W":
    case "2W-FRI":
      return "2 Haftalik"
    case "3W":
    case "3W-FRI":
      return "3 Haftalik"
    case "1M":
    case "ME":
      return "1 Aylik"
    default:
      return value
  }
}

function toCommandTimeframe(value: string): TimeframeType {
  switch (value) {
    case "1D":
      return "1D"
    case "W-FRI":
      return "1W"
    case "2W-FRI":
      return "2W"
    case "3W-FRI":
      return "3W"
    case "ME":
      return "1M"
    default:
      return "ALL"
  }
}

function toneFromLabel(value: string | null | undefined): "profit" | "loss" | "neutral" {
  const normalized = (value || "").toUpperCase()
  if (normalized.includes("AL")) return "profit"
  if (normalized.includes("SAT")) return "loss"
  return "neutral"
}

function toneClass(tone: "profit" | "loss" | "neutral") {
  if (tone === "profit") return "signal-buy"
  if (tone === "loss") return "signal-sell"
  return "bg-[rgba(245,158,11,0.12)] text-[var(--neutral)]"
}

function resolveAnalysisStrategy(value: string) {
  return value.toUpperCase().includes("HUNTER") ? "HUNTER" : "COMBO"
}

function formatTimeframePrice(value: number | string | null): string {
  if (value === null || value === "") return "--"
  if (typeof value === "number") {
    return value.toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 4 })
  }
  return String(value)
}
