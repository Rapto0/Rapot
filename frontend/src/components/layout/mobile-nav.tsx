"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Search,
  Bell,
  History,
  Settings,
  Home,
} from "lucide-react"

const mobileNavItems = [
  { name: "Ana", href: "/", icon: Home },
  { name: "Panel", href: "/dashboard", icon: LayoutDashboard },
  { name: "Tarayıcı", href: "/scanner", icon: Search },
  { name: "Sinyal", href: "/signals", icon: Bell },
  { name: "Ayar", href: "/settings", icon: Settings },
]

export function MobileNav() {
  const pathname = usePathname()

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-surface md:hidden">
      <div className="grid h-14 grid-cols-5">
        {mobileNavItems.map((item) => {
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href))
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center justify-center gap-1 text-[10px] tracking-[0.04em] text-muted-foreground",
                active && "bg-raised text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              <span>{item.name}</span>
            </Link>
          )
        })}
      </div>
      <div className="h-[env(safe-area-inset-bottom)]" />
    </nav>
  )
}

export function MobileHeader() {
  const pathname = usePathname()

  return (
    <header className="fixed left-0 right-0 top-0 z-50 flex h-10 items-center justify-between border-b border-border bg-surface px-3 md:hidden">
      <Link href="/" className="flex items-center gap-2">
        <span className="flex h-6 w-6 items-center justify-center border border-border bg-raised text-[10px] font-semibold tracking-[0.06em]">
          R
        </span>
        <span className="text-sm font-semibold">Rapot</span>
      </Link>

      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <History className="h-3.5 w-3.5" />
        <span className="label-uppercase">{pathname === "/" ? "Ana" : pathname.replace("/", "")}</span>
      </div>
    </header>
  )
}
