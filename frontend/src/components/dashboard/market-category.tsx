import { RefreshCw, AlertCircle } from "lucide-react"
import { finiteNumber, isFeedStale, receivedAge, type FeedNotice } from "@/lib/market-feed"
import { cn } from "@/lib/utils"

export interface MarketRow {
  key: string
  label: string
  value?: number
  change?: number
  receivedAt?: number
}

export function MarketCategoryPanel({
  id, label, description, rows, notice, now, receivedAt, onRefresh, refreshing, streaming,
}: {
  id: string
  label: string
  description: string
  rows: MarketRow[]
  notice: FeedNotice
  now: number
  receivedAt?: number
  onRefresh: () => void
  refreshing: boolean
  streaming: boolean
}) {
  const available = rows.filter((row) => finiteNumber(row.value)).length
  return (
    <article aria-labelledby={`${id}-heading`} className="min-w-0 border border-border bg-surface p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 id={`${id}-heading`} className="label-uppercase">{label}</h2>
          <p className="mt-1 text-[10px] text-muted-foreground">{description}</p>
        </div>
        <span className="mono-numbers text-[10px] text-muted-foreground">{available}/{rows.length} fiyat</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2">
        <div className="min-w-0 flex-1">
          <p role="status" className={cn("flex items-center gap-1.5 text-xs", notice.warning ? "text-amber-400" : "text-muted-foreground")}>
            {notice.warning && <AlertCircle aria-hidden="true" className="h-3.5 w-3.5 shrink-0" />}
            {notice.label}
          </p>
          {!streaming && receivedAt ? (
            <p className="mt-1 text-[10px] text-muted-foreground">Son başarılı yanıt: {receivedAge(receivedAt, now)}</p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={refreshing}
          aria-label={`${label}: ${streaming ? "bağlantıyı yenile" : "verileri yenile"}`}
          className="flex min-h-[44px] shrink-0 items-center gap-1.5 border border-border px-3 text-xs hover:bg-raised disabled:cursor-wait disabled:opacity-50"
        >
          <RefreshCw aria-hidden="true" className={cn("h-3.5 w-3.5", refreshing && "animate-spin motion-reduce:animate-none")} />
          {refreshing ? "Yenileniyor" : "Yenile"}
        </button>
      </div>
      <p className="mt-2 min-h-8 text-[11px] leading-relaxed text-muted-foreground">{notice.description}</p>
      <div className="mt-2 grid grid-cols-2 gap-2">
        {rows.map((row) => <MarketStrip key={row.key} row={row} now={now} streaming={streaming} loading={notice.loading && !notice.warning} />)}
      </div>
    </article>
  )
}

export function MarketStrip({ row, now, streaming, loading }: {
  row: MarketRow
  now: number
  streaming: boolean
  loading: boolean
}) {
  const hasValue = finiteNumber(row.value)
  const hasChange = hasValue && finiteNumber(row.change)
  const stale = streaming && isFeedStale(row.receivedAt, now)
  const value = row.value ?? 0
  const change = row.change ?? 0
  const formattedValue = !hasValue ? "—" : value.toLocaleString("tr-TR", {
    minimumFractionDigits: Math.abs(value) >= 1000 ? 0 : Math.abs(value) >= 1 ? 2 : 4,
    maximumFractionDigits: Math.abs(value) >= 1 ? 2 : 4,
  })
  return (
    <div className="min-w-0 border border-border bg-base px-3 py-2">
      <h3 className="label-uppercase mb-1 break-words">{row.label}</h3>
      <div className="mono-numbers break-words text-[16px] font-semibold sm:text-lg">{formattedValue}</div>
      <div className={cn("mono-numbers text-xs", hasChange && change !== 0 ? (change > 0 ? "text-profit" : "text-loss") : "text-muted-foreground")}>
        {hasChange ? `${change > 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
      </div>
      {!hasValue ? (
        <p className="mt-2 text-[10px] text-muted-foreground">{loading ? "Veri bekleniyor" : "Veri yok"}</p>
      ) : streaming ? (
        <p className={cn("mt-2 text-[10px]", stale ? "text-amber-400" : "text-muted-foreground")}>
          {stale ? "Akış gecikti · " : "Son alım: "}{receivedAge(row.receivedAt, now)}
        </p>
      ) : null}
    </div>
  )
}
