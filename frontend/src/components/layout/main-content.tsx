"use client"

import type { ReactNode } from "react"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"

export function MainContent({ children }: { children: ReactNode }) {
  const pathname = usePathname()
  const isChartRoute = pathname === "/chart" || pathname.startsWith("/chart/")

  return (
    <main
      className={cn(
        "pt-10 md:pl-14",
        isChartRoute
          ? "h-screen overflow-hidden pb-16 md:pb-0"
          : "min-h-screen pb-16 md:pb-4"
      )}
    >
      {children}
    </main>
  )
}
