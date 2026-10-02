"use client"

import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageShell } from "@/components/ui/page-shell"
import { KpiRibbon } from "@/components/ui/kpi-ribbon"
import type { FilterChipOption } from "@/components/ui/filter-chips"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useSignals } from "@/lib/hooks/use-signals"
import { buildSignalCsv, SIGNAL_EXPORT_LIMIT } from "@/lib/signal-export"
import { formatDate, cn } from "@/lib/utils"
import { EmptyState } from "@/components/shared/error-boundary"
import { StrategyInspectorPanel } from "@/components/signals/strategy-inspector-panel"
import { Search, RefreshCw, Download, Bell, X } from "lucide-react"

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
  const [exportError, setExportError] = useState<string | null>(null)

  const { data: signals, isLoading, isError, refetch, isFetching, fetchStatus } = useSignals({
    marketType: marketFilter,
    strategy: strategyFilter,
    direction: directionFilter,
    specialTag: specialFilter,
    searchQuery,
    limit: SIGNAL_EXPORT_LIMIT,
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
  const exportDisabled = isLoading || isFetching || isError || rows.length === 0
  const hasRows = rows.length > 0
  const waitingForData = !isError && (isLoading || signals === undefined)
  const countsAvailable = !waitingForData && (!isError || hasRows)
  const activeFilters = [
    ...(marketFilter !== "all" ? [{ label: `Piyasa: ${marketFilter}`, clear: () => setMarketFilter("all"), focusId: "signal-market-all" }] : []),
    ...(strategyFilter !== "all" ? [{ label: `Strateji: ${strategyFilter}`, clear: () => setStrategyFilter("all"), focusId: "signal-strategy-all" }] : []),
    ...(directionFilter !== "all" ? [{ label: `Yön: ${directionFilter}`, clear: () => setDirectionFilter("all"), focusId: "signal-direction-all" }] : []),
    ...(specialFilter !== "all" ? [{ label: `Özel etiket: ${specialTagLabel(specialFilter)}`, clear: () => setSpecialFilter("all"), focusId: "signal-special-all" }] : []),
    ...(searchQuery ? [{ label: `Sembol: ${searchQuery}`, clear: () => setSearchQuery(""), focusId: "signals-search" }] : []),
  ]
  const hasFilters = activeFilters.length > 0

  function clearFilters() {
    setMarketFilter("all")
    setStrategyFilter("all")
    setDirectionFilter("all")
    setSpecialFilter("all")
    setSearchQuery("")
    document.getElementById("signals-search")?.focus()
  }

  function handleExport() {
    if (exportDisabled) return
    setExportError(null)
    let objectUrl: string | null = null
    let link: HTMLAnchorElement | null = null
    try {
      const file = new Blob([buildSignalCsv(rows)], { type: "text/csv;charset=utf-8" })
      objectUrl = URL.createObjectURL(file)
      link = document.createElement("a")
      link.href = objectUrl
      link.download = `rapot-sinyaller-${new Date().toISOString().slice(0, 10)}.csv`
      document.body.appendChild(link)
      link.click()
    } catch {
      setExportError("CSV dosyası indirilemedi. Lütfen tekrar deneyin.")
    } finally {
      link?.remove()
      if (objectUrl) {
        const completedUrl = objectUrl
        // Let the browser consume the click before releasing the temporary URL.
        window.setTimeout(() => URL.revokeObjectURL(completedUrl), 1000)
      }
    }
  }

  return (
    <PageShell
      label="Sinyaller"
      title="Sinyal kayıtları"
      description="COMBO ve HUNTER kayıtlarını filtreleyin; incelemek için bir sembol seçin."
      className="min-w-0"
      contentClassName="min-w-0"
      actions={
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" className="min-h-[44px] gap-1.5" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw aria-hidden="true" className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
            {isFetching ? "Yenileniyor" : "Yenile"}
          </Button>
          <Button type="button" variant="outline" className="min-h-[44px] gap-1.5" onClick={handleExport} disabled={exportDisabled} aria-describedby="signal-export-scope">
            <Download aria-hidden="true" className="h-3.5 w-3.5" />
            Dışa aktar
          </Button>
        </div>
      }
    >
      <KpiRibbon
        items={[
          { label: "Gösterilen", value: countsAvailable ? `${stats.total}` : "—" },
          { label: "AL", value: countsAvailable ? `${stats.buyCount}` : "—", tone: "profit" },
          { label: "SAT", value: countsAvailable ? `${stats.sellCount}` : "—", tone: "loss" },
        ]}
        columnsClassName="grid-cols-3"
      />

      <p id="signal-export-scope" className="text-xs text-muted-foreground">
        Dışa aktarım, seçili filtreler için yüklenen en fazla {SIGNAL_EXPORT_LIMIT} kayıttan aramaya uyan ve ekranda görünen satırları içerir.
      </p>
      {exportError ? <p role="alert" className="text-xs text-loss">{exportError}</p> : null}

      <section aria-labelledby="signals-filters-heading" className="min-w-0 border border-border bg-surface p-3">
        <h2 id="signals-filters-heading" className="text-sm font-semibold">Filtreler ve sembol araması</h2>
        <div className="mt-3">
          <label htmlFor="signals-search" className="text-xs text-muted-foreground">Sembol ara</label>
          <div className="relative mt-1">
            <Search aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="signals-search"
              type="search"
              autoComplete="off"
              placeholder="Örn. THYAO veya BTCUSDT"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              aria-describedby="signals-search-help"
              className="h-[44px] min-w-0 pl-8 text-[16px] sm:text-sm"
              style={{ fontSize: 16 }}
            />
          </div>
          <p id="signals-search-help" className="mt-1 text-xs text-muted-foreground">
            Arama yalnız yüklenen kayıtlarda sembol adına göre yapılır; tüm geçmişi taramaz.
          </p>
        </div>

        <div className="mt-4 grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <SignalFilterGroup
            id="signal-market"
            label="Piyasa"
            options={MARKET_OPTIONS}
            value={marketFilter}
            onChange={setMarketFilter}
          />

          <SignalFilterGroup
            id="signal-strategy"
            label="Strateji"
            options={STRATEGY_OPTIONS}
            value={strategyFilter}
            onChange={setStrategyFilter}
          />

          <SignalFilterGroup
            id="signal-direction"
            label="Yön"
            options={DIRECTION_OPTIONS}
            value={directionFilter}
            onChange={setDirectionFilter}
          />

          <SignalFilterGroup
            id="signal-special"
            label="Özel etiket"
            options={SPECIAL_OPTIONS}
            value={specialFilter}
            onChange={setSpecialFilter}
          />
        </div>
        <div className="mt-4 border-t border-border pt-3">
          <p className="text-xs text-muted-foreground">
            {hasFilters ? `Etkin seçimler: ${activeFilters.length}` : "Etkin filtre veya sembol araması yok."}
          </p>
          {hasFilters ? (
            <div className="mt-2 flex min-w-0 flex-wrap gap-2">
              {activeFilters.map((filter) => (
                <Button key={filter.focusId} type="button" variant="outline"
                  className="min-h-[44px] max-w-full whitespace-normal py-2 text-left"
                  aria-label={`${filter.label} seçimini temizle`}
                  onClick={() => { filter.clear(); document.getElementById(filter.focusId)?.focus() }}>
                  <span className="min-w-0 break-all">{filter.label}</span>
                  <X aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />
                </Button>
              ))}
              <Button type="button" variant="ghost" className="min-h-[44px]" onClick={clearFilters}>
                Tümünü temizle
              </Button>
            </div>
          ) : null}
        </div>
      </section>

      {!waitingForData && hasRows ? <StrategyInspectorPanel
        selectedSymbol={selectedSignal?.symbol ?? null}
        selectedMarketType={selectedSignal?.marketType ?? null}
      /> : null}

      <section aria-labelledby="signals-results-heading" className="min-w-0 border border-border bg-surface">
        <div className="space-y-1 border-b border-border px-3 py-3">
          <h2 id="signals-results-heading" className="text-sm font-semibold">Sonuçlar</h2>
          <p role="status" aria-atomic="true" className="text-xs text-muted-foreground">
            {waitingForData ? (fetchStatus === "paused" ? "Bağlantı bekleniyor; henüz kayıt alınmadı." : "Sinyaller yükleniyor…") : isError ? (hasRows
              ? `${rows.length} önceki kayıt gösteriliyor.` : "Sonuçlar alınamadı.")
              : `${rows.length} kayıt gösteriliyor.${isFetching ? " Liste yenileniyor…" : ""}`}
          </p>
          <p id="signals-result-scope" className="text-xs text-muted-foreground">
            Sayılar bu listeye aittir; tüm kayıtların toplamı değildir. {marketFilter === "all"
              ? `BIST ve Kripto için ayrı ayrı en fazla ${SIGNAL_EXPORT_LIMIT / 2} kayıt alınır.`
              : `Seçili piyasada en fazla ${SIGNAL_EXPORT_LIMIT} kayıt alınır.`}
          </p>
        </div>

        {isError ? (
          <div role="alert" className="space-y-2 border-b border-border p-3">
            <p className="text-sm font-medium text-loss">{hasRows ? "Sinyaller yenilenemedi." : "Sinyaller yüklenemedi."}</p>
            <p className="text-xs text-muted-foreground">{hasRows
              ? "Son alınan kayıtlar gösteriliyor; güncel olmayabilir. Yeniden deneyin."
              : "Bağlantıyı kontrol edip yeniden deneyin. Bu durum, kayıt olmadığı anlamına gelmez."}</p>
            <Button type="button" variant="outline" className="min-h-[44px]" onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? "Yeniden deneniyor" : "Tekrar dene"}
            </Button>
          </div>
        ) : null}

        {!waitingForData && !isError && !hasRows ? (
          <EmptyState icon={Bell}
            title={hasFilters ? "Seçimlere uygun sinyal bulunamadı" : "Gösterilecek sinyal kaydı yok"}
            description={hasFilters
              ? "Yüklenen kayıtlarda bu filtre ve sembol aramasına uyan sinyal yok. Seçimleri genişletin veya temizleyin."
              : "BIST ve Kripto listeleri boş döndü. Yeni kayıtlar için daha sonra yenileyebilirsiniz."}
            action={hasFilters
              ? <Button type="button" variant="outline" className="min-h-[44px]" onClick={clearFilters}>Filtreleri ve aramayı temizle</Button>
              : <Button type="button" variant="outline" className="min-h-[44px]" onClick={() => refetch()} disabled={isFetching}>Yeniden kontrol et</Button>}
          />
        ) : null}

        {!waitingForData && hasRows ? <>
        <p id="signals-table-help" className="px-3 py-2 text-xs text-muted-foreground">İncelemek için sembol düğmesini seçin. Dar ekranda tabloyu yana kaydırabilirsiniz; klavyede tablo alanına odaklanıp yön tuşlarını kullanın.</p>
        <div role="region" aria-label="Sinyal tablosu" aria-describedby="signals-table-help" tabIndex={0}
          className="max-w-full overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&>div]:overflow-visible">
        <Table className="min-w-[760px]" aria-label="Sinyal kayıtları" aria-describedby="signals-result-scope">
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
            {rows.map((signal) => (
                <TableRow
                  key={signal.id}
                  className={cn(
                    "cursor-pointer hover:bg-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background",
                    selectedSignal?.id === signal.id && "bg-raised/70"
                  )}
                  onClick={() => setSelectedSignalId(signal.id)}
                >
                  <TableCell className="py-1 font-semibold text-foreground">
                    <Button type="button" variant="ghost" className="min-h-[44px] min-w-[44px] text-foreground"
                      aria-label={`${signal.symbol} ${signal.strategy} ${signal.signalType} sinyalini incele`}
                      aria-pressed={selectedSignal?.id === signal.id}
                      onClick={() => setSelectedSignalId(signal.id)}>{signal.symbol}</Button>
                  </TableCell>
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
        </div>
        </> : null}
      </section>
    </PageShell>
  )
}

function SignalFilterGroup<T extends string>({ id, label, options, value, onChange }: {
  id: string
  label: string
  options: readonly FilterChipOption<T>[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <fieldset className="min-w-0">
      <legend className="mb-1 text-xs text-muted-foreground">{label}</legend>
      <div className="flex flex-wrap gap-1">
        {options.map((option) => (
          <Button key={option.value} id={`${id}-${option.value}`} type="button"
            variant={value === option.value ? "default" : "outline"}
            className="min-h-[44px] min-w-[44px]"
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}>{option.label}</Button>
        ))}
      </div>
    </fieldset>
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
