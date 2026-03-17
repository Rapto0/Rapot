"use client"

import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
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
import { useSignals } from "@/lib/hooks/use-signals"
import { formatDate, cn } from "@/lib/utils"
import { EmptyState } from "@/components/shared/error-boundary"
import { StrategyInspectorPanel } from "@/components/signals/strategy-inspector-panel"
import { Search, RefreshCw, Download, Bell } from "lucide-react"

type MarketFilter = "all" | "BIST" | "Kripto"
type StrategyFilter = "all" | "COMBO" | "HUNTER"
type DirectionFilter = "all" | "AL" | "SAT"
type SpecialFilter = "all" | "BELES" | "COK_UCUZ" | "PAHALI" | "FAHIS_FIYAT"

const MARKET_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "BIST", label: "BIST" },
  { value: "Kripto", label: "Kripto" },
] as const satisfies readonly FilterChipOption<MarketFilter>[]

const STRATEGY_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "COMBO", label: "COMBO" },
  { value: "HUNTER", label: "HUNTER" },
] as const satisfies readonly FilterChipOption<StrategyFilter>[]

const DIRECTION_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "AL", label: "AL" },
  { value: "SAT", label: "SAT" },
] as const satisfies readonly FilterChipOption<DirectionFilter>[]

const SPECIAL_OPTIONS = [
  { value: "all", label: "Tümü" },
  { value: "BELES", label: "BELEŞ" },
  { value: "COK_UCUZ", label: "ÇOK UCUZ" },
  { value: "PAHALI", label: "PAHALI" },
  { value: "FAHIS_FIYAT", label: "FAHİŞ FİYAT" },
] as const satisfies readonly FilterChipOption<SpecialFilter>[]

export default function SignalsPage() {
  const [marketFilter, setMarketFilter] = useState<MarketFilter>("all")
  const [strategyFilter, setStrategyFilter] = useState<StrategyFilter>("all")
  const [directionFilter, setDirectionFilter] = useState<DirectionFilter>("all")
  const [specialFilter, setSpecialFilter] = useState<SpecialFilter>("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSignalId, setSelectedSignalId] = useState<number | null>(null)

  const { data: signals, isLoading, isError, refetch, isFetching } = useSignals({
    marketType: marketFilter,
    strategy: strategyFilter,
    direction: directionFilter,
    specialTag: specialFilter,
    searchQuery,
  })

  const rows = useMemo(() => signals ?? [], [signals])
  const selectedSignal = useMemo(
    () => rows.find((row) => row.id === selectedSignalId) ?? rows[0] ?? null,
    [rows, selectedSignalId]
  )

  const stats = {
    total: rows.length,
    buyCount: rows.filter((row) => row.signalType === "AL").length,
    sellCount: rows.filter((row) => row.signalType === "SAT").length,
  }

  return (
    <PageShell
      label="Sinyaller"
      title="Canlı sinyal akışı"
      description="COMBO ve HUNTER stratejilerinden gelen kayıtlar, özel durum etiketleriyle birlikte."
      actions={
        <>
          <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
            Yenile
          </Button>
          <Button type="button" variant="outline" size="sm" className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            Dışa aktar
          </Button>
        </>
      }
    >
      <KpiRibbon
        items={[
          { label: "Toplam", value: `${stats.total}` },
          { label: "AL", value: `${stats.buyCount}`, tone: "profit" },
          { label: "SAT", value: `${stats.sellCount}`, tone: "loss" },
        ]}
        columnsClassName="grid-cols-3"
      />

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

          <FilterChips
            label="Piyasa"
            options={MARKET_OPTIONS}
            value={marketFilter}
            onChange={setMarketFilter}
          />

          <FilterChips
            label="Strateji"
            options={STRATEGY_OPTIONS}
            value={strategyFilter}
            onChange={setStrategyFilter}
          />

          <FilterChips
            label="Yön"
            options={DIRECTION_OPTIONS}
            value={directionFilter}
            onChange={setDirectionFilter}
          />

          <FilterChips
            label="Özel"
            options={SPECIAL_OPTIONS}
            value={specialFilter}
            onChange={setSpecialFilter}
          />
        </div>
      </section>

      <StrategyInspectorPanel
        selectedSymbol={selectedSignal?.symbol ?? null}
        selectedMarketType={selectedSignal?.marketType ?? null}
      />

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
              <TableHead>Özel</TableHead>
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
                <TableCell colSpan={9} className="py-8 text-center text-xs text-muted-foreground">
                  Yükleniyor...
                </TableCell>
              </TableRow>
            ) : null}

            {isError ? (
              <TableRow>
                <TableCell colSpan={9} className="py-8 text-center text-xs text-loss">
                  Sinyaller yüklenemedi.
                </TableCell>
              </TableRow>
            ) : null}

            {!isLoading && !isError && rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9}>
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
                <TableRow
                  key={signal.id}
                  className={cn(
                    "cursor-pointer hover:bg-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
                    selectedSignal?.id === signal.id && "bg-raised/70"
                  )}
                  onClick={() => setSelectedSignalId(signal.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault()
                      setSelectedSignalId(signal.id)
                    }
                  }}
                  tabIndex={0}
                  aria-selected={selectedSignal?.id === signal.id}
                  aria-label={`${signal.symbol} satırını seç`}
                >
                  <TableCell className="font-semibold text-foreground">{signal.symbol}</TableCell>
                  <TableCell>
                    <Badge variant={signal.marketType === "BIST" ? "bist" : "crypto"}>{signal.marketType}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={signal.strategy === "HUNTER" ? "hunter" : "combo"}>{signal.strategy}</Badge>
                  </TableCell>
                  <TableCell>
                    {signal.specialTag ? (
                      <span className={cn("signal-badge", specialTagTone(signal.specialTag))}>
                        {specialTagLabel(signal.specialTag)}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">--</span>
                    )}
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
    </PageShell>
  )
}

function specialTagLabel(tag: "BELES" | "COK_UCUZ" | "PAHALI" | "FAHIS_FIYAT") {
  switch (tag) {
    case "BELES":
      return "BELEŞ"
    case "COK_UCUZ":
      return "ÇOK UCUZ"
    case "PAHALI":
      return "PAHALI"
    case "FAHIS_FIYAT":
      return "FAHİŞ FİYAT"
    default:
      return tag
  }
}

function specialTagTone(tag: "BELES" | "COK_UCUZ" | "PAHALI" | "FAHIS_FIYAT") {
  if (tag === "BELES" || tag === "COK_UCUZ") return "signal-buy"
  return "signal-sell"
}
