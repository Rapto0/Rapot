"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { isActiveRoute, navigation } from "./navigation"

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-[60] hidden h-dvh w-14 flex-col border-r border-sidebar-border bg-sidebar md:flex xl:w-44">
      <div className="flex h-10 shrink-0 items-center justify-center border-b border-sidebar-border xl:justify-start xl:px-3">
        <Link href="/" className="flex items-center gap-2 font-semibold" aria-label="Rapot ana sayfa">
          <span className="flex h-7 w-7 items-center justify-center border border-border bg-raised text-xs">R</span>
          <span className="hidden xl:inline">Rapot</span>
        </Link>
      </div>
      <nav aria-label="Ana gezinme" className="min-h-0 flex-1 space-y-1 overflow-y-auto px-0.5 py-3 xl:px-2">
        {navigation.map((item) => {
          const active = isActiveRoute(pathname, item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              title={item.name}
              aria-label={item.name}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex min-h-[44px] items-center justify-center gap-3 border border-transparent text-muted-foreground transition-colors hover:bg-raised hover:text-foreground xl:justify-start xl:px-3",
                active && "border-border bg-raised text-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span className="hidden text-xs xl:inline">{item.name}</span>
            </Link>
          )
        })}
      </nav>
    </aside>
  )
}
