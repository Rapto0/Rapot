"use client"

import { useEffect, useMemo, useState } from "react"
import { Search, Target } from "lucide-react"

import {
  fetchStrategyInspector,
  type ApiStrategyInspector,
  type ApiStrategyInspectorTimeframe,
} from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn, getTimeAgo } from "@/lib/utils"

type MarketType = "AUTO" | "BIST" | "Kripto"
type StrategyType = "COMBO" | "HUNTER"

interface StrategyInspectorPanelProps {
  selectedSymbol?: string | null
  selectedMarketType?: "BIST" | "Kripto" | null
}

const SUMMARY_ROWS = [
  { key: "signal", label: "Sinyal" },
  { key: "price", label: "Fiyat" },
  { key: "date", label: "Tarih" },
  { key: "active", label: "Aktif" },
  { key: "primary", label: "Ana Skor" },
  { key: "secondary", label: "Ikinci Skor" },
  { key: "raw", label: "Ham Skor" },
] as const

export function StrategyInspectorPanel({
  selectedSymbol,
  selectedMarketType,
}: StrategyInspectorPanelProps) {
  const [symbol, setSymbol] = useState(selectedSymbol ?? "")
  const [marketType, setMarketType] = useState<MarketType>(selectedMarketType ?? "AUTO")
  const [strategy, setStrategy] = useState<StrategyType>("HUNTER")
  const [report, setReport] = useState<ApiStrategyInspector | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (!selectedSymbol || symbol.trim().length > 0) return
    setSymbol(selectedSymbol)
    if (selectedMarketType) setMarketType(selectedMarketType)
  }, [selectedMarketType, selectedSymbol, symbol])

  const timeframes = report?.timeframes ?? []
  const indicatorRows = useMemo(
    () =>
      report?.indicator_order.map((key) => ({
        key,
        label: report.indicator_labels[key] ?? key,
      })) ?? [],
    [report]
  )

  const applySelectedSymbol = () => {
    if (!selectedSymbol) return
    setSymbol(selectedSymbol)
    setMarketType(selectedMarketType ?? "AUTO")
  }

  const runInspection = async () => {
    const normalizedSymbol = symbol.trim().toUpperCase()
    if (!normalizedSymbol) {
      setError("Sembol girin.")
      return
    }

    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchStrategyInspector({
        symbol: normalizedSymbol,
        strategy,
        market_type: marketType,
      })
      setReport(data)
    } catch (inspectionError) {
      setReport(null)
      setError(
        inspectionError instanceof Error
          ? inspectionError.message
          : "Inspector verisi alinamadi."
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <section className="border border-border bg-surface">
      <div className="border-b border-border px-3 py-2">
        <div className="label-uppercase">Strateji Laboratuvari</div>
        <div className="mt-1 text-[10px] text-muted-foreground">
          Telegram inspector aracinin frontend karsiligi. Tek sembol icin tum
          strateji indikatorlerini 5 periyotta yanyana gorursun.
        </div>
      </div>

      <div className="space-y-3 p-3">
        <div className="grid gap-2 xl:grid-cols-[minmax(0,220px)_150px_160px_auto_auto]">
          <Input
            value={symbol}
            onChange={(event) => setSymbol(event.target.value.toUpperCase())}
            placeholder="THYAO veya BTCUSDT"
            className="h-9 text-xs uppercase"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault()
                void runInspection()
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

          <Button
            type="button"
            variant="outline"
            className="h-9 text-xs"
            onClick={runInspection}
            disabled={isLoading}
          >
            <Search className="mr-1.5 h-3.5 w-3.5" />
            {isLoading ? "Hesaplaniyor" : "Hesapla"}
          </Button>

          <Button
            type="button"
            variant="outline"
            className="h-9 text-xs"
            onClick={applySelectedSymbol}
            disabled={!selectedSymbol}
          >
            <Target className="mr-1.5 h-3.5 w-3.5" />
            Secili Sembol
          </Button>
        </div>

        <div className="grid gap-2 border border-border bg-base p-2 md:grid-cols-4">
          <InspectorMetric
            label="Sembol"
            value={report ? `${report.symbol} (${report.market_type})` : selectedSymbol || "--"}
          />
          <InspectorMetric
            label="Strateji"
            value={report?.strategy || strategy}
          />
          <InspectorMetric
            label="Uretilen"
            value={report?.generated_at ? getTimeAgo(report.generated_at) : "--"}
          />
          <InspectorMetric
            label="Periyot"
            value={`${timeframes.length || 0} / 5`}
          />
        </div>

        {error ? (
          <div className="border border-[rgba(255,77,109,0.35)] bg-[rgba(97,26,40,0.25)] px-3 py-2 text-xs text-loss">
            {error}
          </div>
        ) : null}

        {!report && !error ? (
          <div className="border border-dashed border-border px-3 py-8 text-center text-xs text-muted-foreground">
            Bir sembol ve strateji secip inspector sonucunu getir.
          </div>
        ) : null}

        {report ? (
          <>
            <div className="grid gap-2 xl:grid-cols-5">
              {timeframes.map((timeframe) => (
                <div
                  key={timeframe.code}
                  className="border border-border bg-base p-2"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <div>
                      <div className="label-uppercase">{timeframe.label}</div>
                      <div className="mono-numbers mt-1 text-[10px] text-muted-foreground">
                        {timeframe.code}
                      </div>
                    </div>
                    <span className={signalBadgeClass(timeframe.signal_status)}>
                      {timeframe.signal_status}
                    </span>
                  </div>
                  <div className="space-y-1 text-[11px]">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-muted-foreground">Fiyat</span>
                      <span className="mono-numbers">
                        {formatValue(timeframe.price)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-muted-foreground">Tarih</span>
                      <span className="mono-numbers">{timeframe.date || "--"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-muted-foreground">Aktif</span>
                      <span className="mono-numbers">
                        {timeframe.active_indicators || "--"}
                      </span>
                    </div>
                  </div>
                  {!timeframe.available && timeframe.reason ? (
                    <div className="mt-2 border border-border bg-surface px-2 py-1 text-[10px] text-muted-foreground">
                      {timeframe.reason}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>

            <div className="overflow-auto border border-border bg-base">
              <table className="min-w-[1180px] w-full text-[11px]">
                <thead className="sticky top-0 z-10 bg-surface">
                  <tr className="border-b border-border">
                    <th className="px-2 py-2 text-left text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
                      Indikator
                    </th>
                    {timeframes.map((timeframe) => (
                      <th
                        key={timeframe.code}
                        className="px-2 py-2 text-right text-[10px] uppercase tracking-[0.06em] text-muted-foreground"
                      >
                        {timeframe.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SUMMARY_ROWS.map((row) => (
                    <tr
                      key={row.key}
                      className="border-b border-[rgba(255,255,255,0.04)]"
                    >
                      <td className="px-2 py-2 font-medium text-foreground">
                        {row.label}
                      </td>
                      {timeframes.map((timeframe) => (
                        <td
                          key={`${row.key}:${timeframe.code}`}
                          className="px-2 py-2 text-right"
                        >
                          {renderSummaryValue(row.key, timeframe)}
                        </td>
                      ))}
                    </tr>
                  ))}

                  {indicatorRows.map((indicator) => (
                    <tr
                      key={indicator.key}
                      className="border-b border-[rgba(255,255,255,0.04)] last:border-b-0"
                    >
                      <td className="px-2 py-2 text-foreground">{indicator.label}</td>
                      {timeframes.map((timeframe) => (
                        <td
                          key={`${indicator.key}:${timeframe.code}`}
                          className="px-2 py-2 text-right"
                        >
                          <span className="mono-numbers text-muted-foreground">
                            {formatValue(timeframe.indicators[indicator.key])}
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </div>
    </section>
  )
}

function InspectorMetric({
  label,
  value,
}: {
  label: string
  value: string
}) {
  return (
    <div className="border border-border bg-surface px-2 py-1.5">
      <div className="label-uppercase">{label}</div>
      <div className="mono-numbers mt-1 text-sm text-foreground">{value}</div>
    </div>
  )
}

function renderSummaryValue(
  key: (typeof SUMMARY_ROWS)[number]["key"],
  timeframe: ApiStrategyInspectorTimeframe
) {
  if (key === "signal") {
    return <span className={signalBadgeClass(timeframe.signal_status)}>{timeframe.signal_status}</span>
  }

  if (!timeframe.available) {
    return (
      <span className="mono-numbers text-muted-foreground">
        {timeframe.reason || "--"}
      </span>
    )
  }

  switch (key) {
    case "price":
      return <span className="mono-numbers text-foreground">{formatValue(timeframe.price)}</span>
    case "date":
      return <span className="mono-numbers text-muted-foreground">{timeframe.date || "--"}</span>
    case "active":
      return (
        <span className="mono-numbers text-muted-foreground">
          {timeframe.active_indicators || "--"}
        </span>
      )
    case "primary":
      return (
        <span className="mono-numbers text-foreground">
          {timeframe.primary_score || "--"}
        </span>
      )
    case "secondary":
      return (
        <span className="mono-numbers text-muted-foreground">
          {timeframe.secondary_score || "--"}
        </span>
      )
    case "raw":
      return (
        <span className="mono-numbers text-muted-foreground">
          {timeframe.raw_score || "--"}
        </span>
      )
  }
}

function signalBadgeClass(signalStatus: string) {
  return cn(
    "signal-badge",
    signalStatus === "AL"
      ? "signal-buy"
      : signalStatus === "SAT"
        ? "signal-sell"
        : "signal-neutral"
  )
}

function formatValue(value: number | string | null | undefined) {
  if (value === null || value === undefined || value === "") return "--"
  if (typeof value === "number") {
    return value.toLocaleString("tr-TR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 4,
    })
  }
  return String(value)
}
