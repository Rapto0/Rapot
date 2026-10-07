import type { Candle } from "@/lib/api/types"

export function hasDisplayableCandles(candles: readonly Candle[]): boolean {
    return candles.some(({ time, open, high, low, close }) =>
        Number.isFinite(Date.parse(time))
        && [open, high, low, close].every(Number.isFinite)
        && low > 0 && high >= Math.max(open, low, close) && low <= Math.min(open, close))
}

interface ChartDataErrorProps {
    mode: "fatal" | "refresh"
    message: string
    fetching: boolean
    onRetry: () => void
}

/** A failed refresh must remain visible without covering candles already on the chart. */
export function ChartDataError({ mode, message, fetching, onRetry }: ChartDataErrorProps) {
    const fatal = mode === "fatal"
    return (
        <div role="alert" className={fatal
            ? "absolute inset-0 z-10 flex items-center justify-center bg-background/90 backdrop-blur-sm"
            : "flex shrink-0 flex-wrap items-center justify-between gap-2 border-b border-loss/30 bg-loss/5 px-4 py-2"}>
            <div className={fatal ? "max-w-sm space-y-3 border border-loss/40 bg-surface p-4 text-center" : "contents"}>
                <div className="min-w-0 space-y-1">
                    <div className="text-xs font-semibold text-loss">{fatal
                        ? "Grafik verisi yüklenemedi"
                        : "Mum geçmişi yenilenemedi · mevcut mumlar gösteriliyor"}</div>
                    {!fatal && <div className="text-xs text-muted-foreground">Geçmiş veriler güncel olmayabilir.</div>}
                    <div className="break-words text-xs text-muted-foreground">{message}</div>
                </div>
                <button type="button" onClick={onRetry} disabled={fetching}
                    className="inline-flex h-8 shrink-0 items-center justify-center rounded-sm border border-border px-3 text-xs text-foreground hover:bg-raised disabled:cursor-not-allowed disabled:opacity-50">
                    {fetching ? "Yenileniyor..." : "Tekrar dene"}
                </button>
            </div>
        </div>
    )
}
