"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import type { ComponentType } from "react"
import { cn } from "@/lib/utils"
import {
  Search,
  Bell,
  History,
  Activity,
  Settings,
  Brain,
  CalendarDays,
  BarChart3,
  Home,
} from "lucide-react"

type NavItem = {
  name: string
  href: string
  icon: ComponentType<{ className?: string }>
}

const navigation: NavItem[] = [
  { name: "Ana Sayfa", href: "/", icon: Home },
  { name: "Grafik", href: "/chart", icon: BarChart3 },
  { name: "Tarayıcı", href: "/scanner", icon: Search },
  { name: "Sinyaller", href: "/signals", icon: Bell },
  { name: "İşlemler", href: "/trades", icon: History },
  { name: "Bot Sağlığı", href: "/health", icon: Activity },
  { name: "AI", href: "/ai", icon: Brain },
  { name: "Takvim", href: "/calendar", icon: CalendarDays },
]

const footerNavigation: NavItem[] = [
  { name: "Ayarlar", href: "/settings", icon: Settings },
]

function isActiveRoute(pathname: string, href: string) {
  if (href === "/") {
    return pathname === "/"
  }
  return pathname === href || pathname.startsWith(`${href}/`)
}

function SidebarItem({ item, pathname }: { item: NavItem; pathname: string }) {
  const active = isActiveRoute(pathname, item.href)

  return (
    <Link
      href={item.href}
      className={cn(
        "group relative flex h-9 w-9 items-center justify-center border border-transparent text-muted-foreground transition-colors",
        "hover:bg-raised hover:text-foreground",
        active && "bg-raised text-foreground border-border"
      )}
      aria-label={item.name}
    >
      {active && <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 bg-foreground" />}
      <item.icon className="h-4 w-4" />
      <span className="pointer-events-none absolute left-[calc(100%+8px)] top-1/2 z-[70] hidden -translate-y-1/2 whitespace-nowrap border border-border bg-overlay px-2 py-1 text-[10px] font-medium tracking-[0.06em] text-foreground group-hover:block">
        {item.name}
      </span>
    </Link>
  )
}

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="fixed left-0 top-0 z-[60] hidden h-screen w-14 flex-col border-r border-sidebar-border bg-sidebar md:flex">
      <div className="flex h-10 items-center justify-center border-b border-sidebar-border">
        <Link
          href="/"
          className="flex h-7 w-7 items-center justify-center border border-border bg-raised text-xs font-semibold tracking-[0.06em] text-foreground"
          aria-label="Rapot"
        >
          R
        </Link>
      </div>

      <nav className="flex flex-1 flex-col items-center gap-2 py-3">
        {navigation.map((item) => (
          <SidebarItem key={item.href} item={item} pathname={pathname} />
        ))}
      </nav>

      <div className="border-t border-sidebar-border py-3">
        <div className="flex flex-col items-center gap-2">
          {footerNavigation.map((item) => (
            <SidebarItem key={item.href} item={item} pathname={pathname} />
          ))}
        </div>
      </div>
    </aside>
  )
}
