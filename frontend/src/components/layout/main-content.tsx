"use client"

import type { ReactNode } from "react"
import { usePathname } from "next/navigation"
import { useSessionChecked } from "@/lib/hooks/use-session"

const SESSION_PAGES = new Set(["alarms", "ai", "calendar", "health", "login", "research", "scanner", "settings", "trades"])

export function MainContent({ children }: { children: ReactNode }) {
  const page = usePathname()?.split("/")[1] ?? ""
  const sessionChecked = useSessionChecked()
  return (
    <main id="main-content" tabIndex={-1} className="min-h-dvh min-w-0 pb-[calc(80px+env(safe-area-inset-bottom))] pt-[56px] md:pb-4 md:pl-14 md:pt-10 xl:pl-44">
      {!sessionChecked && SESSION_PAGES.has(page) ? <p role="status" className="p-5 text-sm text-muted-foreground">Oturum kontrol ediliyor…</p> : children}
    </main>
  )
}
