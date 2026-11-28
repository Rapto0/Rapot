"use client"

import { useMemo, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import Link from "next/link"
import { fetchLogs } from "@/lib/api/client"
import { fetchResearchConnection } from "@/lib/api/borsapy-api"
import { useApiHealth, useAlarmRuntimeHealth } from "@/lib/hooks/use-health"
import { lastHealthMeasurementAt } from "@/lib/health-status"
import { useSession } from "@/lib/hooks/use-session"
import { cn } from "@/lib/utils"
import { PageShell } from "@/components/ui/page-shell"
import { KpiRibbon } from "@/components/ui/kpi-ribbon"
import { BistSessionStatus } from "@/components/dashboard/bist-session-status"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

type LogLevelFilter = "ALL" | "ERROR" | "WARNING" | "INFO"

const LEVEL_OPTIONS: readonly { value: LogLevelFilter; label: string }[] = [
  { value: "ALL", label: "Tümü" },
  { value: "ERROR", label: "Hata" },
  { value: "WARNING", label: "Uyarı" },
  { value: "INFO", label: "Bilgi" },
]

const MARKET_STATE_LABELS: Record<string, string> = {
  ok: "Taze fiyat alınıyor",
  connected: "Bağlantı açık",
  running: "Veri takibi açık",
  warming: "Veri hazırlanıyor",
  waiting: "İlk fiyat bekleniyor",
  provider_paused: "Hesap koruması için duraklatıldı",
  auth_required: "Hesap doğrulaması gerekli",
  reconnecting: "Yeniden bağlanıyor",
  error: "Bağlantı sorunu",
  disabled: "Veri takibi kapalı",
}

const formatCount = (value: number | null | undefined) =>
  typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("tr-TR") : "—"

const formatDuration = (value: number | null | undefined, unit: string) =>
  value == null ? "—" : `${value.toLocaleString("tr-TR", { maximumFractionDigits: 2 })} ${unit}`

function MeasurementTime({ value }: { value?: number | null }) {
  if (value == null) return <>Henüz yok</>
  const date = new Date(value)
  return <time dateTime={date.toISOString()}>{date.toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })}</time>
}

export default function HealthPage() {
  const health = useApiHealth()
  const alarms = useAlarmRuntimeHealth()
  const session = useSession()
  const allowed = Boolean(session?.user.is_admin && !session.user.disabled)
  const identity = [session?.user.username, session?.expiresAt]
  const [logLevel, setLogLevel] = useState<LogLevelFilter>("ALL")
  const [logSearch, setLogSearch] = useState("")
  const [logsPaused, setLogsPaused] = useState(false)

  const {
    data: logs,
    isLoading: logsLoading,
    isError: logsError,
    error: logsErrorObj,
    refetch: refetchLogs,
    isFetching: logsFetching,
  } = useQuery({
    queryKey: ["logs", ...identity],
    queryFn: () => fetchLogs(120),
    enabled: allowed,
    refetchInterval: logsPaused ? false : 15_000,
    refetchIntervalInBackground: false,
  })

  const connection = useQuery({
    queryKey: ["health-provider-connection", ...identity],
    queryFn: ({ signal }) => fetchResearchConnection(signal),
    enabled: allowed,
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    retry: false,
  })

  const filteredLogs = useMemo(() => {
    const query = logSearch.trim().toLocaleLowerCase("tr-TR")
    return (logs ?? []).filter((entry) => {
      const level = (entry.level || "").toUpperCase()
      if (logLevel === "ERROR" && level !== "ERROR" && level !== "CRITICAL") return false
      if (logLevel === "WARNING" && level !== "WARNING" && level !== "WARN") return false
      if (logLevel === "INFO" && level !== "INFO") return false
      if (query && !`${entry.level} ${entry.message} ${entry.timestamp}`.toLocaleLowerCase("tr-TR").includes(query)) {
        return false
      }
      return true
    })
  }, [logs, logLevel, logSearch])

  if (!allowed) return <PageShell label="Sağlık" title="Sistem sağlığı" description="API ve sunucu alarm motorunun durumu.">
    <p className="text-sm text-muted-foreground">Bu ekran yönetici oturumu gerektirir.</p>
    <Link href="/login?next=%2Fhealth" className="text-sm text-primary underline">Giriş yap</Link>
  </PageShell>

  const protection = connection.data?.provider_protection
  const providerMeasuredAt = lastHealthMeasurementAt(connection)
  const providerVerified = !connection.isError && Boolean(connection.data?.authenticated)

  return (
    <PageShell
      label="Sağlık"
      title="Sistem sağlığı"
      description="Ana API, sunucu alarm motoru, sağlayıcı hesap koruması ve kayıtlar."
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
      <p className="text-xs text-muted-foreground">Son başarılı API sorgusu <MeasurementTime value={health.lastMeasuredAt} /></p>

      <section className="space-y-3 border border-border bg-surface p-4" aria-labelledby="provider-protection-heading">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="provider-protection-heading" className="text-sm font-semibold text-foreground">Sağlayıcı, hesap koruması ve akış bütçesi</h2>
          <span className={cn("signal-badge", protection?.blocked ? "signal-sell" : providerVerified ? "signal-buy" : "signal-neutral")}>
            {connection.isError ? connection.data ? "Yenileme başarısız" : "Doğrulanamadı" : protection?.blocked ? "Koruma etkin (duraklatıldı)" : providerVerified ? "Hesap koruması engelsiz" : "Durum bekleniyor"}
          </span>
        </div>
        <p className="text-xs text-muted-foreground">Son alınan sağlayıcı durumu <MeasurementTime value={providerMeasuredAt} /></p>
        {connection.isError && connection.data && (
          <p role="status" className="text-xs text-warning">Bağlantı ve hesap koruması bilgileri son başarılı sorgudan gösteriliyor.</p>
        )}
        {protection?.blocked && (
          <p role="alert" className="border border-loss/40 bg-loss/5 p-3 text-xs text-loss">
            TradingView hesap koruması tetiklendi ({protection.reason || "kısıtlama"}). Otomatik sağlayıcı erişimi duraklatıldı; alarm ayarları korunur.
          </p>
        )}
        <dl className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <dt className="text-muted-foreground">TradingView oturumu</dt>
            <dd className="mt-1 font-medium">{connection.data ? (connection.data.authenticated ? "Doğrulanmış" : connection.data.state) : "—"}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Ortak hız bütçesi</dt>
            <dd className="mono-numbers mt-1">
              {protection ? `${protection.requests_per_second} iş/sn · burst ${protection.burst}` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Kabul edilen iş / bekleme</dt>
            <dd className="mono-numbers mt-1">
              {protection ? `${formatCount(protection.requests_admitted)} / ${formatCount(protection.budget_waits)}` : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Piyasa akışı</dt>
            <dd className="mt-1">
              {alarms.marketState ? (MARKET_STATE_LABELS[alarms.marketState] ?? alarms.marketState) : "—"}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">BIST seans takvimi</dt>
            <dd className="mt-1"><BistSessionStatus /></dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Son fiyat alımının yaşı</dt>
            <dd className="mono-numbers mt-1">{formatDuration(alarms.quoteAge, "sn")}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Kaynak zamanının yaşı</dt>
            <dd className="mono-numbers mt-1">{formatDuration(alarms.sourceAge, "sn")}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Güncel / izlenen sembol</dt>
            <dd className="mono-numbers mt-1">{formatCount(alarms.freshSymbols)} / {formatCount(alarms.trackedSymbols)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Native bağlantı / abonelik</dt>
            <dd className="mono-numbers mt-1">
              {formatCount(alarms.nativeStreamsConnected)} akış · {formatCount(alarms.nativeRegistered)} / {formatCount(alarms.nativeCapacity)}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Uzun periyot tanıkları</dt>
            <dd className="mono-numbers mt-1">
              {formatCount(alarms.nativeLeaseCertified)} hazır · {formatCount(alarms.nativeLeasePending)} bekleyen
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Canlı fiyat kuyruğu / taşma</dt>
            <dd className={cn("mono-numbers mt-1", (alarms.liveOverflowCount ?? 0) > 0 && "text-warning")}>
              {formatCount(alarms.liveQueuePending)} / {formatCount(alarms.liveQueueLimit)} · taşma {formatCount(alarms.liveOverflowCount)}
            </dd>
          </div>
        </dl>
        <div className="flex flex-wrap gap-4">
          <Link href="/research?tab=connections" className="inline-flex min-h-11 items-center text-xs text-primary underline">Bağlantı ayarlarını aç</Link>
          <Link href="/scanner" className="inline-flex min-h-11 items-center text-xs text-primary underline">RSI takipçisini aç</Link>
        </div>
      </section>

      <section className="space-y-3 border border-border bg-surface p-4" aria-labelledby="alarm-runtime-heading">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 id="alarm-runtime-heading" className="text-sm font-semibold text-foreground">Sunucu alarm motoru</h2>
          <span className={cn("signal-badge", alarms.tone === "profit" ? "signal-buy" : alarms.tone === "loss" ? "signal-sell" : "signal-neutral")}>{alarms.label}</span>
        </div>
        <p className="text-xs text-muted-foreground">API bağlantısı ve alarm motoru ayrı kontrol edilir. Motorun çalışması, bütün fiyatların güncel veya bütün kuralların kontrol edilmiş olduğu anlamına gelmez.</p>
        <dl className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
          <div><dt className="text-muted-foreground">Son başarılı alarm durumu sorgusu</dt><dd><MeasurementTime value={alarms.lastMeasuredAt} /></dd></div>
          <div><dt className="text-muted-foreground">Son kontrol turu</dt><dd>{alarms.lastCycle === null ? "—" : new Date(alarms.lastCycle).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })}</dd></div>
          <div><dt className="text-muted-foreground">Son kontrol turunun süresi</dt><dd>{formatDuration(alarms.lastCycleDuration, "ms")}</dd></div>
          <div><dt className="text-muted-foreground">Bekleyen bildirim</dt><dd>{alarms.pendingDeliveries ?? "—"}</dd></div>
          <div><dt className="text-muted-foreground">Telegram bağlantısı</dt><dd>{alarms.telegramConfigured === null ? "Bilinmiyor" : alarms.telegramConfigured ? "Tanımlı" : "Tanımlı değil"}</dd></div>
        </dl>
        <p className="text-xs text-muted-foreground">Telegram yalnız kendi alarmınızda bildirim seçeneğini açtığınızda kullanılır.</p>
        <Link href="/alarms" className="inline-flex min-h-11 items-center text-xs text-primary underline">Alarm merkezini aç</Link>
      </section>

      <section className="grid min-h-0 flex-1 gap-3">
        <div className="min-h-[420px] border border-border bg-surface">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-3 py-2">
            <div className="flex items-center gap-2">
              <span className="label-uppercase">Loglar</span>
              <span className="mono-numbers text-[11px] text-muted-foreground">
                {filteredLogs.length} / {logs?.length ?? 0} satır
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex gap-1" role="group" aria-label="Log seviyesi filtresi">
                {LEVEL_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    aria-pressed={logLevel === option.value}
                    onClick={() => setLogLevel(option.value)}
                    className={cn(
                      "min-h-9 rounded-sm border px-2.5 text-xs transition-colors",
                      logLevel === option.value ? "border-foreground/40 bg-raised text-foreground" : "border-border text-muted-foreground hover:bg-raised"
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <Input
                type="search"
                aria-label="Loglarda ara"
                placeholder="Log ara…"
                value={logSearch}
                onChange={(event) => setLogSearch(event.target.value)}
                className="min-h-11 w-44 text-base sm:min-h-9 sm:text-xs"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-9 text-xs"
                aria-pressed={logsPaused}
                onClick={() => setLogsPaused((value) => !value)}
              >
                {logsPaused ? "Akışı sürdür" : "Duraklat"}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-9 text-xs"
                onClick={() => void refetchLogs()}
                disabled={logsFetching}
              >
                {logsFetching ? "Yenileniyor..." : "Yenile"}
              </Button>
            </div>
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

            {!logsLoading && !logsError && filteredLogs.length === 0 ? (
              <div className="px-2 py-6 text-center text-xs text-muted-foreground">
                {logs && logs.length > 0 ? "Filtreye uyan log satırı yok." : "Log bulunamadı."}
              </div>
            ) : null}

            {!logsLoading &&
              !logsError &&
              filteredLogs.map((log, index) => (
                <LogLine key={`${log.timestamp}-${index}`} log={log} />
              ))}
          </div>
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
        ? "text-warning"
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
