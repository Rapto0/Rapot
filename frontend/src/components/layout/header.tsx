"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Bell } from "lucide-react"
import { cn } from "@/lib/utils"
import { useApiHealth } from "@/lib/hooks/use-health"
import { SessionControls } from "@/components/auth/session-controls"

export function Header() {
  const [currentTime, setCurrentTime] = useState<Date | null>(null)
  const { apiState } = useApiHealth()

  useEffect(() => {
    const updateClock = () => setCurrentTime(new Date())
    updateClock()
    const timer = setInterval(updateClock, 1000)
    return () => clearInterval(timer)
  }, [])


  return (
    <header className="fixed left-0 right-0 top-0 z-50 hidden h-10 border-b border-border bg-surface md:left-14 md:block xl:left-44">
      <div className="flex h-full items-center justify-between px-4">
        <div className="flex items-center gap-2 text-sm">
          <Link href="/" className="font-semibold text-foreground">
            Rapot
          </Link>
          <span className="text-muted-foreground">|</span>
          <span className="hidden text-muted-foreground lg:inline">Piyasa Analizi</span>
        </div>

        <div className="flex items-center gap-4">
          <SessionControls />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                apiState === "connected" ? "bg-profit" : apiState === "error" ? "bg-loss" : "bg-neutral"
              )}
            />
            <span className="label-uppercase text-[10px] tracking-[0.06em]">
              {apiState === "connected" ? "API Bağlı" : apiState === "error" ? "API Kopuk" : apiState === "loading" ? "API Yükleniyor" : "API Bilinmiyor"}
            </span>
          </div>

          <div className="mono-numbers text-xs text-muted-foreground">
            {currentTime?.toLocaleDateString("tr-TR", {
              day: "2-digit",
              month: "short",
              year: "numeric",
            }) ?? "--"}
            <span className="mx-2 text-ghost">|</span>
            {currentTime?.toLocaleTimeString("tr-TR", {
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
            }) ?? "--"}
          </div>

          <Link href="/alarms" className="inline-flex h-8 items-center gap-2 border border-border px-2 text-xs text-muted-foreground hover:bg-raised hover:text-foreground" aria-label="Alarmlar ve bildirim geçmişi">
            <Bell className="h-4 w-4" />
            <span>Alarmlar</span>
          </Link>
        </div>
      </div>
    </header>
  )
}
