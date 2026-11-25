import Link from "next/link"
import { PageShell } from "@/components/ui/page-shell"

export default function NotFound() {
  return (
    <PageShell
      label="404"
      title="Sayfa bulunamadı"
      description="Aradığınız adres mevcut değil veya taşınmış olabilir."
      width="narrow"
    >
      <section className="space-y-4 border border-border bg-surface p-5">
        <p className="text-sm text-muted-foreground">
          Aşağıdaki bağlantılardan ana ekranlara geçebilirsiniz.
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-xs hover:bg-raised">
            Ana sayfa
          </Link>
          <Link href="/scanner" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-xs hover:bg-raised">
            RSI takipçisi
          </Link>
          <Link href="/alarms" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-xs hover:bg-raised">
            Alarm merkezi
          </Link>
          <Link href="/chart" className="inline-flex min-h-11 items-center rounded-sm border border-border px-4 text-xs hover:bg-raised">
            Gelişmiş grafik
          </Link>
        </div>
      </section>
    </PageShell>
  )
}
