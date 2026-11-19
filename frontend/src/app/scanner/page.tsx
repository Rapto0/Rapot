"use client"

import Link from "next/link"
import { ScannerWorkspace } from "@/components/scanner/scanner-workspace"
import { MarketDataStatus } from "@/components/market-data-status"
import { PageShell } from "@/components/ui/page-shell"
import { usePrivateMarket } from "@/lib/hooks/use-private-market"

export default function ScannerPage() {
  const { allowed, sessionKey, connection } = usePrivateMarket()
  const connectionWarning = connection?.isError || (connection?.data && !connection.data.authenticated)
  return <PageShell title="Hisse ve kripto takipçisi" width="wide" actions={allowed && !connectionWarning && <Link href="/research?tab=connection" className="inline-flex min-h-10 items-center text-xs text-muted-foreground underline-offset-4 hover:underline">Veri bağlantıları</Link>}>
    {allowed && connectionWarning && <MarketDataStatus compact />}
    {allowed ? <ScannerWorkspace key={sessionKey} /> : <Link href="/login?next=%2Fscanner" className="inline-flex min-h-11 items-center self-start border border-border bg-surface px-4 text-sm">Takipçi için yönetici girişi yap</Link>}
  </PageShell>
}
