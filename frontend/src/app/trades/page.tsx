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
import { formatDate, formatCurrency, cn } from "@/lib/utils"
import { EmptyState } from "@/components/shared/error-boundary"
import { History, RefreshCw } from "lucide-react"

type StatusFilter = "all" | "OPEN" | "CLOSED"

const STATUS_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "OPEN", label: "Açık" },
  { value: "CLOSED", label: "Kapalı" },
] as const satisfies readonly FilterChipOption<StatusFilter>[]

export default function TradesPage() {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all")

  const { data: trades, isLoading, isError, refetch, isFetching } = useTrades({ status: statusFilter })
  const { data: stats } = useTradeStats()

  const rows = trades ?? []

  const ribbon = useMemo(() => {
    return {
      totalPnl: stats?.totalPnL ?? 0,
      open: stats?.open ?? 0,
      closed: stats?.closed ?? 0,
      winRate: stats?.winRate ?? 0,
    }
  }, [stats])

  return (
    <PageShell
      label="İşlemler"
      title="İşlem geçmişi"
      description="Açık ve kapalı pozisyon kayıtları."
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
            label: "Toplam PnL",
            value: `${ribbon.totalPnl >= 0 ? "+" : ""}${formatCurrency(ribbon.totalPnl)}`,
            tone: ribbon.totalPnl >= 0 ? "profit" : "loss",
          },
          { label: "Açık", value: `${ribbon.open}` },
          { label: "Kapalı", value: `${ribbon.closed}` },
          {
            label: "Win Rate",
            value: `${ribbon.winRate.toFixed(1)}%`,
            tone: ribbon.winRate >= 50 ? "profit" : "loss",
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
              <TableHead className="text-right">PnL</TableHead>
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
                    <span className={cn("signal-badge", trade.direction === "BUY" ? "signal-buy" : "signal-sell")}>
                      {trade.direction === "BUY" ? "AL" : "SAT"}
                    </span>
                  </TableCell>
                  <TableCell className="mono-numbers text-right">
                    {trade.marketType === "Kripto" ? "$" : "₺"}
                    {trade.entryPrice.toLocaleString("tr-TR", { maximumFractionDigits: 4 })}
                  </TableCell>
                  <TableCell className="mono-numbers text-right">
                    {trade.marketType === "Kripto" ? "$" : "₺"}
                    {trade.currentPrice.toLocaleString("tr-TR", { maximumFractionDigits: 4 })}
                  </TableCell>
                  <TableCell className="mono-numbers text-right">{trade.quantity.toLocaleString("tr-TR")}</TableCell>
                  <TableCell className="text-right">
                    <div className={cn("mono-numbers", trade.pnl >= 0 ? "text-profit" : "text-loss")}>
                      {trade.pnl >= 0 ? "+" : ""}
                      {formatCurrency(trade.pnl)}
                    </div>
                    <div className={cn("mono-numbers text-[10px]", trade.pnlPercent >= 0 ? "text-profit" : "text-loss")}>
                      {trade.pnlPercent >= 0 ? "+" : ""}
                      {trade.pnlPercent.toFixed(2)}%
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={trade.status === "OPEN" ? "default" : "secondary"}>
                      {trade.status === "OPEN" ? "Açık" : "Kapalı"}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">{formatDate(trade.createdAt)}</TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </section>
    </PageShell>
  )
}
