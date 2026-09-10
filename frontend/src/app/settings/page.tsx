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
      title="Bot ayarları ve tarayıcı tercihleri"
      description="Bot yapılandırması sunucuda yönetilir. Bu sayfa bot ayarlarını değiştirmez."
      width="narrow"
    >
      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold">Sunucuda yönetilen ayarlar</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Binance ve Telegram bağlantıları, sinyal eşikleri ve tarama zamanlaması sunucu yapılandırmasından gelir.
          Bağlantı anahtarları bu ekrandan girilemez veya görüntülenemez.
        </p>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Önceki sürümde bu sayfaya girilen strateji değerleri ve bildirim seçimi yalnız tarayıcıya kaydediliyordu;
          botun hesaplamalarını veya Telegram bildirimlerini değiştirmiyordu.
          Bu eski seçimler, gizli bağlantı alanları temizlenerek etkisiz geçmiş kayıtları olarak korunur.
        </p>
        {cleanup?.status === "blocked" ? (
          <p role="alert" className="mt-3 text-xs leading-5 text-loss">
            Eski bağlantı bilgileri için tarayıcı temizliği tamamlanamadı. Tarayıcı depolama izinlerini kontrol edip sayfayı yenileyin.
          </p>
        ) : null}
      </section>

      <section className="border border-border bg-surface p-4">
        <h2 className="text-sm font-semibold">Bu tarayıcıdaki tercihler</h2>
        <p className="mt-2 text-xs leading-5 text-muted-foreground">
          Tarayıcı ekranındaki izleme listeleri, sütunlar ve filtreler kendi ekranından düzenlenir ve bu tarayıcıda saklanır.
          Bu tercihler sunucunun taradığı piyasaları veya ürettiği sinyalleri değiştirmez.
        </p>
        <Link href="/scanner" className="mt-3 inline-block text-xs text-primary underline underline-offset-4">
          Piyasa tarayıcısını aç
        </Link>
      </section>
    </PageShell>
  )
}
