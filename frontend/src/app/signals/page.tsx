"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useSignals } from "@/lib/hooks/use-signals"
import { formatDate, cn } from "@/lib/utils"
import { EmptyState } from "@/components/shared/error-boundary"
import { Search, RefreshCw, Download, Bell } from "lucide-react"

type MarketFilter = "all" | "BIST" | "Kripto"
type StrategyFilter = "all" | "COMBO" | "HUNTER"
type DirectionFilter = "all" | "AL" | "SAT"

export default function SignalsPage() {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("all")
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("all")
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>("all")
  const [searchQuery, setSearchQuery] = useState("")

  const { data: signals, isLoading, isError, refetch, isFetching } = useSignals({
    marketType: marketFilter,
    strategy: strategyFilter,
    direction: directionFilter,
    searchQuery,
  })

  const rows = signals ?? []

  const stats = {
    total: rows.length,
    buyCount: rows.filter((row) => row.signalType === "AL").length,
    sellCount: rows.filter((row) => row.signalType === "SAT").length,
  }

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">Sinyaller</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Canlı sinyal akışı</h1>
            <p className="mt-1 text-xs text-muted-foreground">COMBO ve HUNTER stratejilerinden gelen kayıtlar.</p>
          </div>
          <div className="flex items-center gap-2">
            <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
              Yenile
            </Button>
            <Button type="button" variant="outline" size="sm" className="gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Dışa aktar
            </Button>
          </div>
        </div>
      </section>

      <section className="grid h-16 shrink-0 grid-cols-3 border border-border bg-surface">
        <RibbonItem label="Toplam" value={`${stats.total}`} />
        <RibbonItem label="AL" value={`${stats.buyCount}`} tone="profit" />
        <RibbonItem label="SAT" value={`${stats.sellCount}`} tone="loss" />
      </section>

      <section className="border border-border bg-surface p-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Sembol ara"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              className="pl-8"
            />
          </div>

          <FilterGroup
            label="Piyasa"
            options={[
              ["all", "Tümü"],
              ["BIST", "BIST"],
              ["Kripto", "Kripto"],
            ]}
            value={marketFilter}
            onChange={(value) => setMarketFilter(value as MarketFilter)}
          />

          <FilterGroup
            label="Strateji"
            options={[
              ["all", "Tümü"],
              ["COMBO", "COMBO"],
              ["HUNTER", "HUNTER"],
            ]}
            value={strategyFilter}
            onChange={(value) => setStrategyFilter(value as StrategyFilter)}
          />

          <FilterGroup
            label="Yön"
            options={[
              ["all", "Tümü"],
              ["AL", "AL"],
              ["SAT", "SAT"],
            ]}
            value={directionFilter}
            onChange={(value) => setDirectionFilter(value as DirectionFilter)}
          />
        </div>
      </section>

      <section className="border border-border bg-surface">
        <div className="border-b border-border px-3 py-2">
          <span className="label-uppercase">Kayıtlar</span>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sembol</TableHead>
              <TableHead>Piyasa</TableHead>
              <TableHead>Strateji</TableHead>
              <TableHead>Yön</TableHead>
              <TableHead>Zaman Dilimi</TableHead>
              <TableHead>Skor</TableHead>
              <TableHead className="text-right">Fiyat</TableHead>
              <TableHead className="text-right">Tarih</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-xs text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : null}

            {isError ? (
              <TableRow>
                <TableCell colSpan={8} className="py-8 text-center text-xs text-loss">
                  Sinyaller yüklenemedi.
                </TableCell>
              </TableRow>
            ) : null}

            {!isLoading && !isError && rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>
                  <EmptyState
                    icon={Bell}
                    title="Sinyal bulunamadı"
                    description="Seçili filtrelere uygun kayıt yok."
                  />
                </TableCell>
              </TableRow>
            ) : null}

            {!isLoading &&
              !isError &&
              rows.map((signal) => (
                <TableRow key={signal.id} className="hover:bg-raised">
                  <TableCell className="font-semibold text-foreground">{signal.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={signal.marketType === "BIST" ? "bist" : "crypto"}>{signal.marketType}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={signal.strategy === "HUNTER" ? "hunter" : "combo"}>{signal.strategy}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className={cn("signal-badge", signal.signalType === "AL" ? "signal-buy" : "signal-sell")}>
                      {signal.signalType}
                    </span>
                  </TableCell>
                  <TableCell>{signal.timeframe}</TableCell>
                  <TableCell className="mono-numbers">{signal.score || "--"}</TableCell>
                  <TableCell className="mono-numbers text-right">
                    {signal.marketType === "Kripto" ? "$" : "₺"}
                    {signal.price.toLocaleString("tr-TR", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: signal.marketType === "Kripto" ? 4 : 2,
                    })}
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">{formatDate(signal.createdAt)}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </section>
    </div>
  )
}

function RibbonItem({
  label,
  value,
  tone,
}: {
  label: string
  value: string
  tone?: "profit" | "loss"
}) {
  return (
    <div className="flex min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0">
      <span className="label-uppercase">{label}</span>
      <span className={cn("mono-numbers truncate text-lg font-semibold", tone === "profit" && "text-profit", tone === "loss" && "text-loss")}>
        {value}
      </span>
    </div>
  )
}

function FilterGroup({
  label,
  options,
  value,
  onChange,
}: {
  label: string
  options: readonly [string, string][]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <div className="flex items-center gap-1">
        {options.map(([optionValue, optionLabel]) => (
          <Button
            key={optionValue}
            type="button"
            size="sm"
            variant={value === optionValue ? "default" : "outline"}
            onClick={() => onChange(optionValue)}
          >
            {optionLabel}
          </Button>
        ))}
      </div>
    </div>
  )
}
