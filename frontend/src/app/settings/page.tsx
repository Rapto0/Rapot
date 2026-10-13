"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { PageShell } from "@/components/ui/page-shell"
import { cleanupLegacyBrowserSettings, type LegacySettingsCleanupResult } from "@/lib/browser-preferences"

export default function SettingsPage() {
  const [cleanup, setCleanup] = useState<LegacySettingsCleanupResult | null>(null)

  useEffect(() => {
    setCleanup(cleanupLegacyBrowserSettings())
  }, [])

  return (
    <PageShell
      label="Ayarlar"
      title="Site ayarları ve tarayıcı tercihleri"
      description="Veri bağlantıları, kendi alarmlarınız ve bu tarayıcıdaki tercihler."
      width="narrow"
    >
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

      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold text-foreground">Bu tarayıcıdaki tercihler</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Yerel izleme listeleri, çizimler, sütunlar ve filtreler ilgili ekrandan düzenlenir ve bu tarayıcıda saklanır.
          Sunucu izleme listeleri ve alarmlar ise hesabınıza bağlıdır; yerel tercihler bunları değiştirmez.
        </p>
        <Link href="/scanner" className="mt-3 inline-block text-xs text-primary underline underline-offset-4">
          Piyasa tarayıcısını aç
        </Link>
      </section>
    </PageShell>
  )
}
