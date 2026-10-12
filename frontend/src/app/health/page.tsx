"use client"

import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { fetchLogs, fetchScanHistory } from "@/lib/api/client"
import { useApiHealth, useAlarmRuntimeHealth } from "@/lib/hooks/use-health"
import { useSession } from "@/lib/hooks/use-session"
import { cn } from "@/lib/utils"
import { PageShell } from "@/components/ui/page-shell"
import { KpiRibbon } from "@/components/ui/kpi-ribbon"
import { Button } from "@/components/ui/button"
import { ScanStatus } from "@/components/scanner/scan-status"

export default function HealthPage() {
  const health = useApiHealth()
  const alarms = useAlarmRuntimeHealth()
  const session = useSession()
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
  const identity = [session?.user.username, session?.expiresAt]

  const {
    data: logs,
    isLoading: logsLoading,
    isError: logsError,
    error: logsErrorObj,
    refetch: refetchLogs,
    isFetching: logsFetching,
  } = useQuery({
    queryKey: ["logs", ...identity],
    queryFn: () => fetchLogs(60),
    enabled: allowed,
    refetchInterval: 15_000,
    refetchIntervalInBackground: false,
  })

  const {
    data: recentScans,
    isLoading: scansLoading,
    isError: scansError,
    error: scansErrorObj,
    refetch: refetchScans,
    isFetching: scansFetching,
  } = useQuery({
    queryKey: ["scanHistory", "health", ...identity],
    queryFn: () => fetchScanHistory(10),
    enabled: allowed,
    refetchInterval: false,
    refetchIntervalInBackground: false,
  })

  if (!allowed) return <PageShell label="Sağlık" title="Sistem sağlığı" description="API ve sunucu alarm motorunun durumu.">
    <p className="text-sm text-muted-foreground">Bu ekran yönetici oturumu gerektirir.</p>
    <Link href="/login?next=%2Fhealth" className="text-sm text-primary underline">Giriş yap</Link>
  </PageShell>

  return (
    <PageShell
      label="Sağlık"
      title="Sistem sağlığı"
      description="Ana API, sunucu alarm motoru ve kayıtlar."
      actions={
        <span className={cn("signal-badge", health.apiState === "connected" ? "signal-buy" : health.apiState === "error" ? "signal-sell" : "signal-neutral")}>
          API: {health.label}
        </span>
      }
    >
      <KpiRibbon
        items={[
          { label: "API", value: health.label, tone: health.tone },
          { label: "Veritabanı", value: health.database },
          { label: "Realtime servisi", value: health.realtime },
          { label: "API çalışma süresi", value: health.uptime },
        ]}
      />

      <section className="space-y-3 border border-border bg-surface p-4" aria-labelledby="alarm-runtime-heading">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="alarm-runtime-heading" className="text-sm font-semibold text-foreground">Sunucu alarm motoru</h2>
          <span className={cn("signal-badge", alarms.tone === "profit" ? "signal-buy" : alarms.tone === "loss" ? "signal-sell" : "signal-neutral")}>{alarms.label}</span>
        </div>
        <p className="text-xs text-muted-foreground">API bağlantısı ve alarm motoru ayrı kontrol edilir. Motorun çalışması, bütün fiyatların güncel veya bütün kuralların kontrol edilmiş olduğu anlamına gelmez.</p>
        <dl className="grid gap-2 text-xs sm:grid-cols-3">
          <div><dt className="text-muted-foreground">Son kontrol turu</dt><dd>{alarms.lastCycle === null ? "—" : new Date(alarms.lastCycle).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })}</dd></div>
          <div><dt className="text-muted-foreground">Bekleyen bildirim</dt><dd>{alarms.pendingDeliveries ?? "—"}</dd></div>
          <div><dt className="text-muted-foreground">Telegram bağlantısı</dt><dd>{alarms.telegramConfigured === null ? "Bilinmiyor" : alarms.telegramConfigured ? "Tanımlı" : "Tanımlı değil"}</dd></div>
        </dl>
        <p className="text-xs text-muted-foreground">Telegram yalnız kendi alarmınızda bildirim seçeneğini açtığınızda kullanılır. Otomatik COMBO / HUNTER botu ve Telegram AI komutları kaldırıldı.</p>
        <Link href="/alarms" className="inline-flex min-h-11 items-center text-xs text-primary underline">Alarm merkezini aç</Link>
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

            {!logsLoading && logsError ? (
              <div className="space-y-2 px-2 py-6 text-center">
                <div className="text-xs text-loss">Loglar yüklenemedi.</div>
                {logsErrorObj instanceof Error ? (
                  <div className="text-[11px] text-muted-foreground">{logsErrorObj.message}</div>
                ) : null}
                <Button type="button" variant="outline" size="sm" className="h-7 text-xs" onClick={() => void refetchLogs()} disabled={logsFetching}>
                  {logsFetching ? "Yenileniyor..." : "Tekrar dene"}
                </Button>
              </div>
            ) : null}

            {!logsLoading && !logsError && (!logs || logs.length === 0) ? (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">Log bulunamadı.</div>
            ) : null}

            {!logsLoading &&
              !logsError &&
              logs?.map((log, index) => (
                <LogLine key={`${log.timestamp}-${index}`} log={log} />
              ))}
          </div>
        </div>

        <div className="min-h-[420px] border border-border bg-surface">
          <div className="border-b border-border px-3 py-2">
            <span className="label-uppercase">Tarama arşivi</span>
            <p className="mt-1 text-xs text-muted-foreground">Önceki otomatik taramalar korunur. Yeni otomatik tarama çalıştırılmaz.</p>
          </div>

          {scansLoading ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">Yükleniyor...</div>
          ) : null}

          {!scansLoading && scansError ? (
            <div className="space-y-2 px-3 py-8 text-center">
              <div className="text-xs text-loss">Taramalar yüklenemedi.</div>
              {scansErrorObj instanceof Error ? (
                <div className="text-[11px] text-muted-foreground">{scansErrorObj.message}</div>
              ) : null}
              <Button type="button" variant="outline" size="sm" className="h-7 text-xs" onClick={() => void refetchScans()} disabled={scansFetching}>
                {scansFetching ? "Yenileniyor..." : "Tekrar dene"}
              </Button>
            </div>
          ) : null}

          {!scansLoading && !scansError && (!recentScans || recentScans.length === 0) ? (
            <div className="px-3 py-8 text-center text-xs text-muted-foreground">Kayıt bulunamadı.</div>
          ) : null}

          {!scansLoading && !scansError && recentScans && recentScans.length > 0 ? (
            <div className="divide-y divide-border">
              {recentScans.map((scan) => (
                <div key={scan.id} className="grid grid-cols-[48px_1fr_72px_48px] items-center gap-2 px-3 py-2">
                  <div className="mono-numbers text-xs text-muted-foreground">#{scan.id}</div>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2 text-xs text-foreground">
                      <span>{scan.scan_type}</span>
                      <ScanStatus status={scan.status} />
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {scan.symbols_scanned} sembol • {scan.duration_seconds.toFixed(1)} sn
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {scan.errors_count == null ? "Hata sayısı bilinmiyor" : `${scan.errors_count} hata`}
                      {scan.mode === "sync" || scan.mode === "async" ? ` • ${scan.mode}` : ""}
                    </div>
                  </div>
                  <div className="text-right text-muted-foreground">
                    <div className="mono-numbers text-xs">{scan.signals_found}</div>
                    <div className="text-[10px]">{scan.status && scan.status !== "unknown" ? "yeni sinyal" : "sinyal"}</div>
                  </div>
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
    </PageShell>
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
