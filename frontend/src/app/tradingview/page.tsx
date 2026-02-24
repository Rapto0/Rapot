"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchTicker } from "@/lib/api/client"
import { useSignals } from "@/lib/hooks/use-signals"
import { cn } from "@/lib/utils"

export default function TradingViewPage() {
  const { data: tickers, isLoading: tickersLoading } = useQuery({
    queryKey: ["ticker", "tradingview"],
    queryFn: fetchTicker,
    refetchInterval: 30_000,
  })

  const { data: signals, isLoading: signalsLoading } = useSignals({ limit: 200 })

  const watchRows = useMemo(() => (tickers ?? []).slice(0, 40), [tickers])

  const [selectedSymbol, setSelectedSymbol] = useState<string>(watchRows[0]?.symbol ?? "BTCUSDT")

  const selectedTicker = useMemo(
    () => watchRows.find((row) => row.symbol === selectedSymbol) ?? watchRows[0],
    [selectedSymbol, watchRows]
  )

  const symbolSignals = useMemo(
    () => (signals ?? []).filter((signal) => signal.symbol === selectedTicker?.symbol).slice(0, 12),
    [selectedTicker?.symbol, signals]
  )

  return (
    <div className="mx-auto flex h-[calc(100vh-40px)] w-full max-w-[1680px] gap-3 p-3">
      <section className="flex min-w-0 flex-1 flex-col border border-border bg-surface">
        <div className="flex h-10 items-center justify-between border-b border-border px-3">
          <div className="flex items-center gap-2">
            <span className="label-uppercase">İzleme listesi</span>
            <span className="text-[10px] text-muted-foreground">Canlı fiyat akışı</span>
          </div>
          <span className="text-[10px] text-muted-foreground">{watchRows.length} sembol</span>
        </div>

        <div className="min-h-0 flex-1 overflow-auto">
          <div className="grid grid-cols-[1.2fr_1fr_90px] border-b border-border px-3 py-2 text-[10px] uppercase tracking-[0.06em] text-muted-foreground">
            <span>Sembol</span>
            <span className="text-right">Fiyat</span>
            <span className="text-right">Değişim</span>
          </div>

          {tickersLoading ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">Yükleniyor...</div>
          ) : (
            watchRows.map((row) => {
              const isPositive = row.changePercent >= 0
              const isActive = row.symbol === selectedTicker?.symbol

              return (
                <button
                  key={row.symbol}
                  type="button"
                  onClick={() => setSelectedSymbol(row.symbol)}
                  className={cn(
                    "grid w-full grid-cols-[1.2fr_1fr_90px] items-center border-b border-[rgba(255,255,255,0.04)] px-3 py-2 text-left hover:bg-raised",
                    isActive && "border-l-2 border-l-foreground bg-raised"
                  )}
                >
                  <span className="truncate text-xs font-semibold text-foreground">{row.symbol}</span>
                  <span className="mono-numbers text-right text-xs text-foreground">
                    {row.price.toLocaleString("tr-TR", { maximumFractionDigits: 4 })}
                  </span>
                  <span className={cn("mono-numbers text-right text-xs", isPositive ? "text-profit" : "text-loss")}>
                    {isPositive ? "+" : ""}
                    {row.changePercent.toFixed(2)}%
                  </span>
                </button>
              )
            })
          )}
        </div>
      </section>

      <section className="hidden w-[320px] shrink-0 flex-col gap-3 lg:flex">
        <div className="border border-border bg-surface">
          <div className="border-b border-border px-3 py-2">
            <span className="label-uppercase">Seçili sembol</span>
          </div>
          <div className="space-y-2 px-3 py-3">
            <div className="text-sm font-semibold text-foreground">{selectedTicker?.symbol ?? "--"}</div>
            <div className="mono-numbers text-lg font-semibold text-foreground">
              {selectedTicker ? selectedTicker.price.toLocaleString("tr-TR", { maximumFractionDigits: 4 }) : "--"}
            </div>
            <div
              className={cn(
                "mono-numbers text-xs",
                (selectedTicker?.changePercent ?? 0) >= 0 ? "text-profit" : "text-loss"
              )}
            >
              {(selectedTicker?.changePercent ?? 0) >= 0 ? "+" : ""}
              {(selectedTicker?.changePercent ?? 0).toFixed(2)}%
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 border border-border bg-surface">
          <div className="border-b border-border px-3 py-2">
            <span className="label-uppercase">Son sinyaller</span>
          </div>
          <div className="max-h-[420px] overflow-auto">
            {signalsLoading ? (
              <div className="px-3 py-6 text-center text-xs text-muted-foreground">Yükleniyor...</div>
            ) : symbolSignals.length === 0 ? (
              <div className="px-3 py-6 text-center text-xs text-muted-foreground">Sinyal bulunamadı.</div>
            ) : (
              symbolSignals.map((signal) => (
                <div key={signal.id} className="border-b border-[rgba(255,255,255,0.04)] px-3 py-2 last:border-b-0">
                  <div className="flex items-center justify-between">
                    <span className={cn("signal-badge", signal.signalType === "AL" ? "signal-buy" : "signal-sell")}>
                      {signal.signalType}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{signal.timeframe}</span>
                  </div>
                  <div className="mt-1 text-xs text-foreground">{signal.strategy}</div>
                  <div className="mt-0.5 mono-numbers text-[10px] text-muted-foreground">
                    {new Date(signal.createdAt).toLocaleString("tr-TR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
