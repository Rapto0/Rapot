"use client"

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchLogs, fetchScanHistory } from "@/lib/api/client"
import { useBotHealth } from "@/lib/hooks/use-health"
import { cn } from "@/lib/utils"

export default function HealthPage() {
  const health = useBotHealth()

  const { data: logs, isLoading: logsLoading } = useQuery({
    queryKey: ["logs"],
    queryFn: () => fetchLogs(60),
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  })

  const { data: recentScans, isLoading: scansLoading } = useQuery({
    queryKey: ["scanHistory", "health"],
    queryFn: () => fetchScanHistory(10),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  })

  const apiState = useMemo(() => {
    if (health.isError) return "Hata"
    if (health.isLoading) return "Yükleniyor"
    return "Sağlıklı"
  }, [health.isError, health.isLoading])

  return (
    <div className="mx-auto flex w-full max-w-[1680px] flex-col gap-3 p-3">
      <section className="border border-border bg-surface p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="label-uppercase">Sağlık</div>
            <h1 className="mt-1 text-lg font-semibold tracking-[-0.02em]">Bot durum ekranı</h1>
            <p className="mt-1 text-xs text-muted-foreground">Süreç durumu, log akışı ve son taramalar.</p>
          </div>
          <span className={health.isRunning ? "signal-badge signal-buy" : "signal-badge signal-sell"}>
            {health.isRunning ? "ÇALIŞIYOR" : "DURDU"}
          </span>
        </div>
      </section>

      <section className="grid h-16 shrink-0 grid-cols-2 border border-border bg-surface md:grid-cols-4">
        <RibbonItem label="API" value={apiState} tone={health.isError ? "loss" : "profit"} />
        <RibbonItem label="Tarama" value={health.isScanning ? "Sürüyor" : "Hazır"} tone={health.isScanning ? "neutral" : undefined} />
        <RibbonItem label="Toplam" value={`${health.scanCount}`} />
        <RibbonItem label="Uptime" value={health.uptime} />
      </section>

      <section className="grid min-h-0 flex-1 gap-3 lg:grid-cols-2">
        <div className="min-h-[420px] border border-border bg-surface">
          <div className="border-b border-border px-3 py-2">
            <span className="label-uppercase">Loglar</span>
          </div>

          <div className="max-h-[520px] overflow-auto bg-base p-2">
            {logsLoading ? (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">Yükleniyor...</div>
            ) : null}

            {!logsLoading && (!logs || logs.length === 0) ? (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">Log bulunamadı.</div>
            ) : null}

            {!logsLoading &&
              logs?.map((log, index) => (
                <LogLine key={`${log.timestamp}-${index}`} log={log} />
              ))}
          </div>
        </div>

        <div className="min-h-[420px] border border-border bg-surface">
          <div className="border-b border-border px-3 py-2">
            <span className="label-uppercase">Son taramalar</span>
          </div>

          {scansLoading ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">Yükleniyor...</div>
          ) : null}

          {!scansLoading && (!recentScans || recentScans.length === 0) ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">Kayıt bulunamadı.</div>
          ) : null}

          {!scansLoading && recentScans && recentScans.length > 0 ? (
            <div className="divide-y divide-border">
              {recentScans.map((scan) => (
                <div key={scan.id} className="grid grid-cols-[72px_1fr_96px_80px] items-center gap-2 px-3 py-2">
                  <div className="mono-numbers text-xs text-muted-foreground">#{scan.id}</div>
                  <div className="min-w-0">
                    <div className="text-xs text-foreground">{scan.scan_type}</div>
                    <div className="text-[10px] text-muted-foreground">
                      {scan.symbols_scanned} sembol • {scan.duration_seconds.toFixed(1)} sn
                    </div>
                  </div>
                  <div className="mono-numbers text-right text-xs text-profit">{scan.signals_found}</div>
                  <div className="mono-numbers text-right text-[10px] text-muted-foreground">
                    {new Date(scan.created_at).toLocaleTimeString("tr-TR", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : null}
        </div>
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
        className={cn(
          "mono-numbers truncate text-lg font-semibold",
          tone === "profit" && "text-profit",
          tone === "loss" && "text-loss",
          tone === "neutral" && "text-neutral"
        )}
      >
        {value}
      </span>
    </div>
  )
}

function LogLine({
  log,
}: {
  log: {
    timestamp: string
    level: string
    message: string
  }
}) {
  const levelClass =
    log.level === "ERROR" || log.level === "CRITICAL"
      ? "text-loss"
      : log.level === "WARNING"
        ? "text-neutral"
        : "text-muted-foreground"

  const date = new Date((log.timestamp || "").replace(" ", "T"))
  const timeLabel = Number.isNaN(date.getTime())
    ? log.timestamp || "--"
    : date.toLocaleTimeString("tr-TR", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })

  return (
    <div className="grid grid-cols-[74px_64px_1fr] gap-2 border-b border-[rgba(255,255,255,0.04)] px-2 py-1 text-[11px] last:border-b-0">
      <span className="mono-numbers text-muted-foreground">{timeLabel}</span>
      <span className={cn("mono-numbers", levelClass)}>{log.level}</span>
      <span className="text-foreground">{log.message}</span>
    </div>
  )
}
