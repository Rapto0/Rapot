"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    Search,
    Bell,
    History,
    Activity,
    Settings,
    TrendingUp,
    LineChart,
    CalendarDays,
    ChevronLeft,
    ChevronRight,
    BarChart3,
} from "lucide-react"
import { useState } from "react"

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Grafik", href: "/chart", icon: BarChart3 },
    { name: "Piyasa Tarayıcı", href: "/scanner", icon: Search },
    { name: "Aktif Sinyaller", href: "/signals", icon: Bell },
    { name: "İşlem Geçmişi", href: "/trades", icon: History },
    { name: "Bot Sağlığı", href: "/health", icon: Activity },
    { name: "TradingView", href: "/tradingview", icon: LineChart },
    { name: "Ekonomik Takvim", href: "/calendar", icon: CalendarDays },
    { name: "Ayarlar", href: "/settings", icon: Settings },
]

export function Sidebar() {
    const pathname = usePathname()
    const [collapsed, setCollapsed] = useState(false)

    return (
        <aside
            className={cn(
                "fixed left-0 top-0 z-40 h-screen border-r border-sidebar-border bg-sidebar transition-all duration-300 hidden md:block",
                collapsed ? "w-16" : "w-56"
            )}
        >
            {/* Logo */}
            <div className="flex h-14 items-center border-b border-sidebar-border px-4">
                <Link href="/" className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                        <TrendingUp className="h-5 w-5 text-white" />
                    </div>
                    {!collapsed && (
                        <span className="text-lg font-bold text-foreground">Rapot</span>
                    )}
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 p-2">
                {navigation.map((item) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                                isActive
                                    ? "bg-primary/10 text-primary"
                                    : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                            )}
                        >
                            <item.icon className="h-5 w-5 shrink-0" />
                            {!collapsed && <span>{item.name}</span>}
                        </Link>
                    )
                })}
            </nav>

            {/* Collapse Button */}
            <div className="absolute bottom-4 left-0 right-0 flex justify-center px-2">
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="flex h-8 w-8 items-center justify-center rounded-lg bg-sidebar-accent text-muted-foreground hover:text-foreground transition-colors"
                >
                    {collapsed ? (
                        <ChevronRight className="h-4 w-4" />
                    ) : (
                        <ChevronLeft className="h-4 w-4" />
                    )}
                </button>
            </div>

            {/* Bot/API Status Indicator */}
            <div
                className={cn(
                    "absolute bottom-16 left-0 right-0 px-3",
                    collapsed && "px-2"
                )}
            >
                <div
                    className={cn(
                        "flex items-center gap-2 rounded-lg bg-sidebar-accent px-3 py-2",
                        collapsed && "justify-center px-2"
                    )}
                >
                    <div className="relative">
                        <div className="h-2 w-2 rounded-full bg-profit" />
                        <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-profit opacity-75" />
                    </div>
                    {!collapsed && (
                        <span className="text-xs text-muted-foreground">API Bağlı</span>
                    )}
                </div>
            </div>
        </aside>
    )
}
