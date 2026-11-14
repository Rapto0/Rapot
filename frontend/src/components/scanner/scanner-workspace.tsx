"use client"

import Link from "next/link"
import { useState } from "react"
import { BorsapyScreener } from "@/components/scanner/borsapy-screener"
import { RsiTracker } from "@/components/scanner/rsi-tracker"

export function ScannerWorkspace() {
  const [advanced, setAdvanced] = useState(false)
  return <div className="min-w-0 space-y-6">
    <RsiTracker />
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-xs">
      <p className="text-muted-foreground">Takipçi seçimi alarmlarınızı değiştirmez.</p>
      <Link href="/alarms?manage=watchlists#watchlists" className="inline-flex min-h-11 items-center underline underline-offset-4">İzleme listelerini ve alarmları yönet</Link>
    </div>
    <section className="border border-border bg-surface p-4" aria-label="Gelişmiş tarama">
      <button type="button" aria-expanded={advanced} aria-controls="advanced-borsapy-screener" onClick={() => setAdvanced(value => !value)} className="flex min-h-11 w-full items-center justify-between gap-4 text-left text-sm font-medium">
        <span>Gelişmiş Borsapy taraması</span><span aria-hidden="true">{advanced ? "−" : "+"}</span>
      </button>
      {advanced && <div id="advanced-borsapy-screener" className="space-y-4 border-t border-border pt-4">
        <p className="text-xs text-muted-foreground">Temel ve teknik koşullarla ayrı bir tarama çalıştırın. Sonuçlar alarm oluşturmaz.</p>
        <BorsapyScreener />
      </div>}
    </section>
  </div>
}
