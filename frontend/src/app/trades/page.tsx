"use client"

import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
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
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">İşlemler</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">İşlem geçmişi</h1>
            <p className="mt-1 text-xs text-muted-foreground">Açık ve kapalı pozisyon kayıtları.</p>
          </div>
          <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
            Yenile
          </Button>
        </div>
      </section>

      <section className="grid h-16 shrink-0 grid-cols-2 border border-border bg-surface md:grid-cols-4">
        <RibbonItem
          label="Toplam PnL"
          value={`${ribbon.totalPnl >= 0 ? "+" : ""}${formatCurrency(ribbon.totalPnl)}`}
          tone={ribbon.totalPnl >= 0 ? "profit" : "loss"}
        />
        <RibbonItem label="Açık" value={`${ribbon.open}`} />
        <RibbonItem label="Kapalı" value={`${ribbon.closed}`} />
        <RibbonItem label="Win Rate" value={`${ribbon.winRate.toFixed(1)}%`} tone={ribbon.winRate >= 50 ? "profit" : "loss"} />
      </section>

      <section className="border border-border bg-surface p-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Durum</span>
          {(["all", "OPEN", "CLOSED"] as const).map((status) => (
            <Button
              key={status}
              type="button"
              variant={statusFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(status)}
            >
              {status === "all" ? "Tümü" : status === "OPEN" ? "Açık" : "Kapalı"}
            </Button>
          ))}
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
