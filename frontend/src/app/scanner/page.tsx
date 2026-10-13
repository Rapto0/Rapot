"use client"

import Link from "next/link"
import { BorsapyScreener } from "@/components/scanner/borsapy-screener"
import { MarketDataStatus } from "@/components/market-data-status"
import { PageShell } from "@/components/ui/page-shell"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"

export default function ScannerPage() {
  const { allowed, sessionKey } = usePrivateMarket()
  return <PageShell label="Tarayıcı" title="Piyasa tarayıcı" description="Temel ve teknik koşullarla Borsapy üzerinden sembol arayın.">
    <MarketDataStatus />
    {allowed ? <BorsapyScreener key={sessionKey} /> : <Link href="/login?next=%2Fscanner" className="text-sm text-primary underline">Tarama için yönetici girişi yap</Link>}
    <p className="text-xs text-muted-foreground">Tarama sonuçları alarm oluşturmaz. Seçtiğiniz sembolleri izleme listenize ekleyip koşullarınızı Alarmlar ekranında kaydedebilirsiniz.</p>
    <Link href="/alarms?manage=watchlists#watchlists" className="text-sm text-primary underline">İzleme listelerini ve alarmları yönet</Link>
  </PageShell>
}
