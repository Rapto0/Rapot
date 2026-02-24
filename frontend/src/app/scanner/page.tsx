"use client"

import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { useBotHealth } from "@/lib/hooks/use-health"
import { fetchScanHistory } from "@/lib/api/client"
import { RefreshCw, Search } from "lucide-react"

export default function ScannerPage() {
  const health = useBotHealth()

  const { data: recentScans, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["scanHistory"],
    queryFn: () => fetchScanHistory(12),
    refetchInterval: 30_000,
  })

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">Tarayıcı</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Piyasa tarama ekranı</h1>
            <p className="mt-1 text-xs text-muted-foreground">BIST ve Kripto taramalarının durum ve geçmişi.</p>
          </div>
          <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={isFetching ? "h-3.5 w-3.5 animate-spin" : "h-3.5 w-3.5"} />
            Yenile
          </Button>
        </div>
      </section>

      <section className="grid h-16 shrink-0 grid-cols-2 border border-border bg-surface md:grid-cols-4">
        <RibbonItem label="Bot" value={health.isRunning ? "Aktif" : "Kapalı"} tone={health.isRunning ? "profit" : "loss"} />
        <RibbonItem label="Tarama" value={health.isScanning ? "Sürüyor" : "Hazır"} tone={health.isScanning ? "neutral" : undefined} />
        <RibbonItem label="Toplam" value={`${health.scanCount}`} />
        <RibbonItem label="Uptime" value={health.uptime} />
      </section>

      <section className="grid gap-3 border border-border bg-surface p-3 md:grid-cols-2">
        <ScannerBox
          market="BIST"
          active={health.isRunning}
          text="Borsa İstanbul sembolleri periyodik olarak taranıyor."
        />
        <ScannerBox
          market="Kripto"
          active={health.isRunning}
          text="Binance spot çiftleri COMBO ve HUNTER ile izleniyor."
        />
      </section>

      <section className="border border-border bg-surface">
        <div className="border-b border-border px-3 py-2">
          <span className="label-uppercase">Son taramalar</span>
        </div>

        {isLoading ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">Yükleniyor...</div>
        ) : null}

        {!isLoading && (!recentScans || recentScans.length === 0) ? (
          <div className="px-3 py-8 text-center text-xs text-muted-foreground">Kayıt bulunamadı.</div>
        ) : null}

        {!isLoading && recentScans && recentScans.length > 0 ? (
          <div className="divide-y divide-border">
            {recentScans.map((scan) => (
              <div key={scan.id} className="grid grid-cols-[72px_1fr_96px_80px] items-center gap-2 px-3 py-2">
                <div className="mono-numbers text-xs text-muted-foreground">#{scan.id}</div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Badge variant={scan.scan_type === "BIST" ? "bist" : "crypto"}>{scan.scan_type}</Badge>
                    <span className="text-xs text-foreground">{scan.symbols_scanned} sembol</span>
                  </div>
                  <div className="mt-0.5 text-[10px] text-muted-foreground">Süre: {scan.duration_seconds.toFixed(1)} sn</div>
                </div>
                <div className="mono-numbers text-right text-xs text-profit">{scan.signals_found} sinyal</div>
                <div className="mono-numbers text-right text-[10px] text-muted-foreground">
                  {new Date(scan.created_at).toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" })}
                </div>
              </div>
            ))}
          </div>
        ) : null}
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
  tone?: "profit" | "loss" | "neutral"
}) {
  return (
    <div className="flex min-w-0 flex-col justify-center gap-1 border-r border-border px-3 last:border-r-0">
      <span className="label-uppercase">{label}</span>
      <span
        className={
          tone === "profit"
            ? "mono-numbers truncate text-lg font-semibold text-profit"
            : tone === "loss"
              ? "mono-numbers truncate text-lg font-semibold text-loss"
              : tone === "neutral"
                ? "mono-numbers truncate text-lg font-semibold text-neutral"
                : "mono-numbers truncate text-lg font-semibold"
        }
      >
        {value}
      </span>
    </div>
  )
}

function ScannerBox({
  market,
  active,
  text,
}: {
  market: "BIST" | "Kripto"
  active: boolean
  text: string
}) {
  return (
    <div className="border border-border bg-base p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Search className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-sm font-semibold">{market}</span>
        </div>
        <span className={active ? "signal-badge signal-buy" : "signal-badge signal-sell"}>{active ? "AKTİF" : "KAPALI"}</span>
      </div>
      <p className="text-xs text-muted-foreground">{text}</p>
    </div>
  )
}
