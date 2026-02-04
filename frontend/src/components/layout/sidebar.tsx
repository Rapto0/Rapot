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
    BarChart3,
    Pin,
    PinOff,
    Home,
} from "lucide-react"
import { useSidebar } from "./sidebar-context"

const navigation = [
    { name: "Ana Sayfa", href: "/", icon: Home },
    { name: "Gösterge Paneli", href: "/dashboard", icon: LayoutDashboard },
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
    const { isPinned, setIsPinned, isHovered, setIsHovered, isExpanded } = useSidebar()

    return (
        <aside
            onMouseEnter={() => !isPinned && setIsHovered(true)}
            onMouseLeave={() => !isPinned && setIsHovered(false)}
            className={cn(
                "fixed left-0 top-0 z-[60] h-screen border-r border-sidebar-border bg-sidebar/95 backdrop-blur-xl hidden md:flex flex-col",
                "transition-all duration-300 ease-out",
                isExpanded ? "w-56" : "w-16"
            )}
        >
            {/* Logo Area */}
            <div className="flex h-14 items-center border-b border-sidebar-border px-3">
                <Link href="/" className="flex items-center gap-3 flex-1 min-w-0">
                    <div className={cn(
                        "flex items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-red-600 transition-all duration-300 shadow-lg",
                        isExpanded ? "h-9 w-9" : "h-10 w-10"
                    )}>
                        <TrendingUp className={cn(
                            "text-white transition-all duration-300",
                            isExpanded ? "h-5 w-5" : "h-6 w-6"
                        )} />
                    </div>
                    <span className={cn(
                        "text-lg font-bold text-foreground whitespace-nowrap transition-all duration-300",
                        isExpanded ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 w-0"
                    )}>
                        Rapot
                    </span>
                </Link>

                {/* Pin/Unpin Button - Only visible when expanded */}
                <button
                    onClick={() => setIsPinned(!isPinned)}
                    className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-300",
                        "text-muted-foreground hover:text-foreground hover:bg-sidebar-accent",
                        isExpanded ? "opacity-100 scale-100" : "opacity-0 scale-75 pointer-events-none w-0"
                    )}
                    title={isPinned ? "Otomatik gizle" : "Sabitle"}
                >
                    {isPinned ? (
                        <Pin className="h-4 w-4 text-primary" />
                    ) : (
                        <PinOff className="h-4 w-4" />
                    )}
                </button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 p-2 overflow-y-auto overflow-x-hidden">
                {navigation.map((item, index) => {
                    const isActive = pathname === item.href
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                                "hover:scale-[1.02] active:scale-[0.98]",
                                isActive
                                    ? "bg-primary/10 text-primary shadow-sm"
                                    : "text-muted-foreground hover:bg-sidebar-accent hover:text-foreground"
                            )}
                            style={{
                                transitionDelay: isExpanded ? `${index * 20}ms` : "0ms"
                            }}
                        >
                            <div className={cn(
                                "flex h-8 w-8 items-center justify-center rounded-lg shrink-0 transition-colors",
                                isActive ? "bg-primary/10" : "bg-transparent"
                            )}>
                                <item.icon className={cn(
                                    "h-5 w-5 transition-transform duration-200",
                                    !isExpanded && "scale-110"
                                )} />
                            </div>
                            <span className={cn(
                                "whitespace-nowrap transition-all duration-300",
                                isExpanded ? "opacity-100 translate-x-0" : "opacity-0 -translate-x-4 w-0 overflow-hidden"
                            )}>
                                {item.name}
                            </span>

                            {/* Active indicator dot */}
                            {isActive && !isExpanded && (
                                <span className="absolute left-1 w-1 h-6 rounded-full bg-primary" />
                            )}
                        </Link>
                    )
                })}
            </nav>

            {/* Bot/API Status Indicator */}
            <div className="p-3 border-t border-sidebar-border">
                <div className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2 bg-sidebar-accent/50 transition-all duration-300",
                    !isExpanded && "justify-center px-2"
                )}>
                    <div className="relative shrink-0">
                        <div className="h-2.5 w-2.5 rounded-full bg-profit" />
                        <div className="absolute inset-0 h-2.5 w-2.5 animate-ping rounded-full bg-profit opacity-75" />
                    </div>
                    <span className={cn(
                        "text-xs text-muted-foreground whitespace-nowrap transition-all duration-300",
                        isExpanded ? "opacity-100" : "opacity-0 w-0 overflow-hidden"
                    )}>
                        API Bağlı
                    </span>
                </div>

                {/* Hover hint when collapsed and not pinned */}
                {!isExpanded && !isPinned && (
                    <div className="mt-2 text-[10px] text-muted-foreground/50 text-center animate-pulse">
                        ← Hover
                    </div>
                )}
            </div>
        </aside>
    )
}
