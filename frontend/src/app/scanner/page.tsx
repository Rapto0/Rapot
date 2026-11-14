"use client"

import Link from "next/link"
import { ScannerWorkspace } from "@/components/scanner/scanner-workspace"
import { MarketDataStatus } from "@/components/market-data-status"
import { PageShell } from "@/components/ui/page-shell"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"

export default function ScannerPage() {
  const { allowed, sessionKey } = usePrivateMarket()
  return <PageShell label="Takipçi" title="Hisse ve kripto takipçisi" description="Piyasayı seçin, sembolleri bulun ve takip edeceğiniz RSI periyotlarını düzenleyin.">
    <MarketDataStatus compact />
    {allowed ? <ScannerWorkspace key={sessionKey} /> : <Link href="/login?next=%2Fscanner" className="text-sm text-primary underline">Takipçi için yönetici girişi yap</Link>}
  </PageShell>
}
