"use client"

import Link from "next/link"
import { useMemo, useState } from "react"
import { Brain, Loader2, RefreshCw } from "lucide-react"

import {
  fetchAIAnalysis,
  type ApiStrategyInspectorTimeframe,
  type StructuredAIAnalysisResponse,
} from "@/lib/api/client"
import { useRecentAnalyses, type AIAnalysis } from "@/lib/hooks/use-analyses"
import { StrategyInspectorPanel } from "@/components/indicators/strategy-inspector-panel"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn, getTimeAgo } from "@/lib/utils"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"

type MarketType = "AUTO" | "BIST" | "Kripto"
type StrategyType = "COMBO" | "HUNTER"
type TimeframeType = "ALL" | "1D" | "1W" | "2W" | "3W" | "1M"

const EMPTY_RESULT: StructuredAIAnalysisResponse | null = null

export function AITerminal() {
  const { allowed, sessionKey } = usePrivateMarket()
  if (!allowed) return <section className="m-4 space-y-3 border border-border bg-surface p-4"><h1 className="text-xl font-semibold text-foreground">Manuel AI analizi</h1><p className="text-sm text-muted-foreground">Bu ekran yönetici oturumu gerektirir.</p><Link href="/login?next=%2Fai" className="text-sm text-primary underline">Giriş yap</Link></section>
  return <ManualAITerminal key={sessionKey} />
}

function ManualAITerminal() {
  const { allowed } = usePrivateMarket()
  const [symbol, setSymbol] = useState("")
  const [marketType, setMarketType] = useState<MarketType>("AUTO")
  const [strategy, setStrategy] = useState<StrategyType>("HUNTER")
  const [timeframe, setTimeframe] = useState<TimeframeType>("ALL")
  const [result, setResult] = useState<StructuredAIAnalysisResponse | null>(EMPTY_RESULT)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const recentAnalysesQuery = useRecentAnalyses(16)

  const averageConfidence = useMemo(() => {
    const scores = (recentAnalysesQuery.data ?? [])
      .map((analysis) => analysis.confidenceScore)
      .filter((value): value is number => typeof value === "number")
    if (scores.length === 0) return "--"
    return `${Math.round(scores.reduce((sum, value) => sum + value, 0) / scores.length)}`
  }, [recentAnalysesQuery.data])

  const refreshPageData = () => recentAnalysesQuery.refetch()

  const runAnalysis = async () => {
    const normalizedSymbol = symbol.trim().toUpperCase()
    if (!allowed || isLoading) return
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

  const loadAnalysisContext = (analysis: AIAnalysis) => {
    setSymbol(analysis.symbol)
    setMarketType(analysis.marketType)
    setStrategy(resolveAnalysisStrategy(analysis.scenarioName))
    setTimeframe("ALL")
  }

  const structured = result?.structured_analysis ?? null
  const inspectionRows = result?.inspection.timeframes ?? []
  const isRefreshing = recentAnalysesQuery.isFetching

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
              Bir sembol, gösterge ve periyot seçerek kendi analizinizi başlatın. Analiz alarm veya emir oluşturmaz.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="gap-1.5"
              onClick={refreshPageData}
              disabled={isRefreshing}
              aria-busy={isRefreshing}
            >
              <RefreshCw className={cn("h-3.5 w-3.5", isRefreshing && "animate-spin")} />
              Veri tazele
            </Button>
          </div>
        </div>
      </section>

      <section className="grid min-h-16 grid-cols-2 border border-border bg-surface md:grid-cols-4">
        <RibbonStat label="Sembol" value={symbol || "—"} />
        <RibbonStat label="AI Kaydi" value={`${recentAnalysesQuery.data?.length ?? 0}`} />
        <RibbonStat label="Ort. Guven" value={averageConfidence} tone="profit" />
        <RibbonStat
          label="Secili"
          value={strategy}
        />
      </section>

      <section className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
        <main className="flex min-w-0 flex-col gap-3">
          <section className="border border-border bg-surface">
            <div className="border-b border-border px-3 py-2">
              <span className="label-uppercase">Komut satiri</span>
            </div>
            <div className="grid gap-2 p-3 lg:grid-cols-[minmax(0,1fr)_120px_120px_140px_auto]">
              <Input
                aria-label="Analiz sembolü"
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
                aria-label="Gösterge"
                value={strategy}
                onChange={(event) => setStrategy(event.target.value as StrategyType)}
                className="h-9 border border-border bg-base px-2 text-xs text-foreground outline-none"
              >
                <option value="HUNTER">HUNTER</option>
                <option value="COMBO">COMBO</option>
              </select>

              <select
                aria-label="Piyasa"
                value={marketType}
                onChange={(event) => setMarketType(event.target.value as MarketType)}
                className="h-9 border border-border bg-base px-2 text-xs text-foreground outline-none"
              >
                <option value="AUTO">AUTO</option>
                <option value="BIST">BIST</option>
                <option value="Kripto">Kripto</option>
              </select>

              <select
                aria-label="Periyot"
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

              <Button
                type="button"
                variant="outline"
                className="h-9 text-xs"
                onClick={runAnalysis}
                disabled={isLoading || !allowed}
                aria-busy={isLoading}
              >
                {isLoading ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Brain className="mr-1.5 h-3.5 w-3.5" />}
                {isLoading ? "Yorumlaniyor" : "AI Yorumla"}
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
                Sembolü girin, gösterge ve periyodu seçin, ardından AI Yorumla düğmesine basın.
                Sonuçlar yalnız sizin isteğinizle oluşturulur; sağlayıcı verisi ve model erişimi gerekir.
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
          <section className="min-h-0 flex-1 border border-border bg-surface">
            <div className="border-b border-border px-3 py-2">
              <span className="label-uppercase">Manuel analizler</span>
            </div>
            <div className="max-h-[420px] overflow-auto">
              {recentAnalysesQuery.isLoading ? (
                <div className="px-3 py-6 text-center text-xs text-muted-foreground">Yukleniyor...</div>
              ) : (recentAnalysesQuery.data?.length ?? 0) === 0 ? (
                <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                  Henüz manuel analiz kaydı yok.
                </div>
              ) : (
                (recentAnalysesQuery.data ?? []).filter(analysis => analysis.signalId === null).map((analysis) => (
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
      <details className="border border-border bg-surface p-3"><summary className="cursor-pointer text-sm font-medium text-foreground">Göstergeleri AI olmadan incele</summary><div className="mt-3"><StrategyInspectorPanel selectedSymbol={symbol} selectedMarketType={marketType === "AUTO" ? null : marketType} /></div></details>
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
