"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { ActionDialog } from "@/components/ui/action-dialog"
import { Button } from "@/components/ui/button"
import { PageShell } from "@/components/ui/page-shell"
import { cleanupLegacyBrowserSettings, type LegacySettingsCleanupResult } from "@/lib/browser-preferences"
import { useSession } from "@/lib/hooks/use-session"
import { RSI_COLUMNS_STORAGE_KEY } from "@/lib/rsi-tracker"

interface LocalPreferenceItem {
  key: string
  label: string
  description: string
  bytes: number
  present: boolean
}

const MANAGED_BROWSER_KEYS = [
  { key: RSI_COLUMNS_STORAGE_KEY, label: "RSI takipçisi sütunları", description: "Takipçi tablosunda seçili zaman dilimleri." },
  { key: "rapot.dashboard.indicators.v1", label: "Grafik gösterge ayarları", description: "Grafikte açık tutulan teknik göstergeler ve parametreleri." },
  { key: "rapot.dashboard.watchlists.v1", label: "Eski yerel izleme listeleri", description: "Sunucu listelerinden bağımsız tarayıcı listeleri." },
  { key: "rapot.dashboard.watchlist-alarms.v1", label: "Eski yerel alarmlar", description: "Yalnız tarayıcı açıkken çalışan eski kurallar." },
] as const

function inspectBrowserKeys(): LocalPreferenceItem[] {
  if (typeof window === "undefined") {
    return MANAGED_BROWSER_KEYS.map(item => ({ ...item, bytes: 0, present: false }))
  }
  return MANAGED_BROWSER_KEYS.map(item => {
    try {
      const raw = window.localStorage.getItem(item.key)
      return { ...item, bytes: raw ? raw.length : 0, present: raw !== null }
    } catch {
      return { ...item, bytes: 0, present: false }
    }
  })
}

export default function SettingsPage() {
  const session = useSession()
  const [cleanup, setCleanup] = useState<LegacySettingsCleanupResult | null>(null)
  const [items, setItems] = useState<LocalPreferenceItem[]>(() =>
    MANAGED_BROWSER_KEYS.map(item => ({ ...item, bytes: 0, present: false }))
  )
  const [resetTarget, setResetTarget] = useState<LocalPreferenceItem | null>(null)
  const [notice, setNotice] = useState("")

  useEffect(() => {
    setCleanup(cleanupLegacyBrowserSettings())
    setItems(inspectBrowserKeys())
  }, [])

  const exportLocalPreferences = () => {
    const payload: Record<string, unknown> = { exportedAt: new Date().toISOString(), preferences: {} }
    const prefs: Record<string, unknown> = {}
    for (const item of MANAGED_BROWSER_KEYS) {
      try {
        const raw = window.localStorage.getItem(item.key)
        if (raw !== null) {
          try { prefs[item.key] = JSON.parse(raw) } catch { prefs[item.key] = raw }
        }
      } catch { /* Ignore unreadable keys. */ }
    }
    payload.preferences = prefs
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "rapot-tarayici-tercihleri.json"
    link.click()
    URL.revokeObjectURL(url)
    setNotice("Tarayıcı tercihleri JSON olarak indirildi (kimlik bilgileri veya sunucu sırları içermez).")
  }

  const confirmReset = () => {
    if (!resetTarget) return
    try {
      window.localStorage.removeItem(resetTarget.key)
      setNotice(`${resetTarget.label} bu tarayıcıdan temizlendi. Sunucu verileri etkilenmedi.`)
    } catch {
      setNotice("Tarayıcı depolaması güncellenemedi.")
    }
    setResetTarget(null)
    setItems(inspectBrowserKeys())
  }

  return (
    <PageShell
      label="Ayarlar"
      title="Site ayarları ve tarayıcı tercihleri"
      description="Oturum durumu, sunucu bağlantıları ve bu tarayıcıdaki yerel tercihler."
      width="narrow"
    >
      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-foreground">Oturum durumu</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          {session
            ? `Etkin hesap: ${session.user.username} (${session.user.is_admin ? "Yönetici" : "Standart kullanıcı"}). Oturum bitişi: ${new Date(session.expiresAt).toLocaleString("tr-TR", { timeZone: "Europe/Istanbul" })} (İstanbul).`
            : "Şu anda etkin yönetici oturumu bulunmuyor."}
        </p>
        {!session ? (
          <Link href="/login?next=%2Fsettings" className="mt-2 inline-flex min-h-11 items-center text-xs text-primary underline underline-offset-4">
            Yönetici girişi yap
          </Link>
        ) : null}
      </section>

      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-foreground">Veri bağlantıları ve site AI</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Piyasa veri bağlantıları Araştırma Merkezi üzerinden yönetilir. Site AI analizi /ai ekranından kullanılabilir.
          Grafiklerde göstergeleri inceleyin; kendi sunucu ve izleme listesi alarmlarınızı koşullarınıza göre yönetin.
        </p>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Önceki sürümde bu sayfaya girilen strateji değerleri ve bildirim seçimi yalnız tarayıcıya kaydediliyordu;
          sunucu hesaplamalarını veya Telegram bildirimlerini değiştirmiyordu.
          Bu eski seçimler, gizli bağlantı alanları temizlenerek etkisiz geçmiş kayıtları olarak korunur.
        </p>
        <div className="flex flex-wrap gap-4">
          <Link href="/research" className="inline-flex min-h-11 items-center text-xs text-primary underline">Veri bağlantılarını aç</Link>
          <Link href="/ai" className="inline-flex min-h-11 items-center text-xs text-primary underline">Site AI analizini aç</Link>
        </div>
        {cleanup?.status === "blocked" ? (
          <p role="alert" className="mt-3 text-xs leading-5 text-loss">
            Eski bağlantı bilgileri için tarayıcı temizliği tamamlanamadı. Tarayıcı depolama izinlerini kontrol edip sayfayı yenileyin.
          </p>
        ) : null}
      </section>

      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-foreground">Sunucu alarmları</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Kendi sembol, gösterge ve eşik kurallarınızı alarm merkezinde yönetebilirsiniz.
          Sunucu alarm servisi çalışırken bu kurallar tarayıcı kapalı olsa da değerlendirilir.
          Telegram bildirimi varsayılan olarak kapalıdır; her alarm için kendiniz açabilirsiniz.
          Bildirim hedefi sunucu yapılandırmasından gelir; bağlantı bilgileri burada görüntülenmez.
        </p>
        <Link href="/alarms" className="mt-2 inline-flex min-h-11 items-center text-xs text-primary underline underline-offset-4">
          Sunucu alarm merkezini aç
        </Link>
      </section>

      <section className="space-y-3 border border-border bg-surface p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-semibold text-foreground">Bu tarayıcıdaki tercihler</h2>
          <Button type="button" variant="outline" size="sm" className="min-h-11 text-xs" onClick={exportLocalPreferences}>
            Tercihleri dışa aktar (JSON)
          </Button>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          Yerel izleme listeleri, çizimler, sütunlar ve filtreler ilgili ekrandan düzenlenir ve bu tarayıcıda saklanır.
          Sunucu izleme listeleri ve alarmlar ise hesabınıza bağlıdır; yerel tercihler bunları değiştirmez.
        </p>
        {notice ? <p role="status" className="border border-border bg-base p-2.5 text-xs text-foreground">{notice}</p> : null}
        <ul className="divide-y divide-border border border-border bg-base">
          {items.map(item => (
            <li key={item.key} className="flex flex-wrap items-center justify-between gap-2 p-3 text-xs">
              <div className="min-w-0">
                <p className="font-medium text-foreground">{item.label}</p>
                <p className="text-muted-foreground">{item.description}</p>
                <p className="mono-numbers mt-0.5 text-[11px] text-muted-foreground">
                  {item.present ? `Kayıtlı (${item.bytes.toLocaleString("tr-TR")} karakter)` : "Kayıt yok"}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="min-h-11 text-xs"
                disabled={!item.present}
                onClick={() => setResetTarget(item)}
              >
                Sıfırla
              </Button>
            </li>
          ))}
        </ul>
        <Link href="/scanner" className="inline-flex min-h-11 items-center text-xs text-primary underline underline-offset-4">
          Hisse ve kripto takipçisini aç
        </Link>
      </section>

      <ActionDialog
        open={Boolean(resetTarget)}
        title="Yerel tercihi sıfırla"
        description={resetTarget ? `"${resetTarget.label}" bu tarayıcıdan silinecek. Sunucu alarmları ve sunucu listeleri etkilenmez.` : undefined}
        confirmLabel="Sıfırla"
        cancelLabel="Vazgeç"
        variant="danger"
        onCancel={() => setResetTarget(null)}
        onConfirm={confirmReset}
      />
    </PageShell>
  )
}
