"use client"

import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { KpiRibbon } from "@/components/ui/kpi-ribbon"
import { FilterChips, type FilterChipOption } from "@/components/ui/filter-chips"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useTrades, useTradeStats } from "@/lib/hooks/use-trades"
import { formatDate, cn } from "@/lib/utils"
import { formatMetric, formatMetricPercent, formatTradePrice, metricTextClass, metricTone } from "@/lib/metric-display"
import { EmptyState } from "@/components/shared/error-boundary"
import { History, RefreshCw } from "lucide-react"

type StatusFilter = "all" | "OPEN" | "CLOSED" | "CANCELLED"

const STATUS_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "OPEN", label: "Açık" },
  { value: "CLOSED", label: "Kapalı" },
  { value: "CANCELLED", label: "İptal" },
] as const satisfies readonly FilterChipOption<StatusFilter>[]

export default function TradesPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  const { data: trades, isLoading, isError, refetch, isFetching } = useTrades({ status: statusFilter })
  const { data: stats } = useTradeStats()

  const rows = trades ?? []

  const ribbon = useMemo(() => {
    return {
      totalPnl: stats?.totalPnL,
      open: stats?.open,
      closed: stats?.closed,
      winRate: stats?.winRate,
    }
  }, [stats])

  return (
    <PageShell
      label="İşlemler"
      title="İşlem geçmişi"
      description="PnL yalnız kapanmış işlemler için kayıtlıdır. Toplam, işlemlerin kendi para birimlerini toplar; döviz dönüşümü içermez."
      actions={
        <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
          <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
          Yenile
        </Button>
      }
    >
      <KpiRibbon
        items={[
          {
            label: "Gerçekleşmiş PnL",
            value: formatMetric(ribbon.totalPnl, 2, true),
            tone: metricTone(ribbon.totalPnl),
          },
          { label: "Açık", value: formatMetric(ribbon.open, 0) },
          { label: "Kapalı", value: formatMetric(ribbon.closed, 0) },
          {
            label: "Win Rate",
            value: formatMetricPercent(ribbon.winRate, 1),
            tone: metricTone(ribbon.winRate, 50),
          },
        ]}
      />

      <section className="border border-border bg-surface p-3">
        <FilterChips
          label="Durum"
          options={STATUS_OPTIONS}
          value={statusFilter}
          onChange={setStatusFilter}
        />
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
              <TableHead>Yön</TableHead>
              <TableHead className="text-right">Giriş</TableHead>
              <TableHead className="text-right">Güncel</TableHead>
              <TableHead className="text-right">Miktar</TableHead>
              <TableHead className="text-right">Gerçekleşmiş PnL</TableHead>
              <TableHead>Durum</TableHead>
              <TableHead className="text-right">Tarih</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={9} className="py-8 text-center text-xs text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : null}

            {isError ? (
              <TableRow>
                <TableCell colSpan={9} className="py-8 text-center text-xs text-loss">
                  İşlem listesi yüklenemedi.
                </TableCell>
              </TableRow>
            ) : null}

            {!isLoading && !isError && rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9}>
                  <EmptyState icon={History} title="İşlem bulunamadı" description="Seçili filtreye uygun kayıt yok." />
                </TableCell>
              </TableRow>
            ) : null}

            {!isLoading &&
              !isError &&
              rows.map((trade) => (
                <TableRow key={trade.id} className="hover:bg-raised">
                  <TableCell className="font-semibold text-foreground">{trade.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={trade.marketType === "BIST" ? "bist" : "crypto"}>{trade.marketType}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className={cn("signal-badge", trade.direction === "BUY" ? "signal-buy" : trade.direction === "SELL" ? "signal-sell" : "text-muted-foreground")}>
                      {trade.direction === "BUY" ? "AL" : trade.direction === "SELL" ? "SAT" : "—"}
                    </span>
                  </TableCell>
                  <TableCell className="mono-numbers text-right">
                    {formatTradePrice(trade.entryPrice, trade.marketType, 4)}
                  </TableCell>
                  <TableCell className="mono-numbers text-right">
                    {formatTradePrice(trade.currentPrice, trade.marketType, 4)}
                  </TableCell>
                  <TableCell className="mono-numbers text-right">{formatMetric(trade.quantity, 4)}</TableCell>
                  <TableCell className="text-right">
                    <div className={cn("mono-numbers", metricTextClass(trade.pnl))}>
                      {trade.pnl === null ? "—" : `${trade.pnl >= 0 ? "+" : ""}${formatTradePrice(trade.pnl, trade.marketType)}`}
                    </div>
                    <div className={cn("mono-numbers text-[10px]", metricTextClass(trade.pnlPercent))}>
                      {formatMetricPercent(trade.pnlPercent, 2, true)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={trade.status === "OPEN" ? "default" : "secondary"}>
                      {trade.status === "OPEN" ? "Açık" : trade.status === "CLOSED" ? "Kapalı" : trade.status === "CANCELLED" ? "İptal" : "Bilinmiyor"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">{trade.createdAt ? formatDate(trade.createdAt) : "—"}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </section>
    </PageShell>
  )
}
