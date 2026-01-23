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
    MoreHorizontal,
} from "lucide-react"
import { useState } from "react"

// Main mobile navigation items (max 5 for bottom bar)
const mobileNavItems = [
    { name: "Ana Sayfa", href: "/", icon: LayoutDashboard },
    { name: "Tarayıcı", href: "/scanner", icon: Search },
    { name: "Sinyaller", href: "/signals", icon: Bell },
    { name: "İşlemler", href: "/trades", icon: History },
    { name: "Daha", href: "#more", icon: MoreHorizontal },
]

// Secondary items for "More" menu
const moreMenuItems = [
    { name: "Bot Sağlığı", href: "/health", icon: Activity },
    { name: "Ayarlar", href: "/settings", icon: LayoutDashboard },
]

export function MobileNav() {
    const pathname = usePathname()
    const [showMore, setShowMore] = useState(false)

    return (
        <>
            {/* Bottom Navigation Bar - Only visible on mobile */}
            <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-sidebar md:hidden">
                <div className="flex items-center justify-around h-16">
                    {mobileNavItems.map((item) => {
                        const isActive = item.href === "#more"
                            ? showMore
                            : pathname === item.href

                        const isMore = item.href === "#more"

                        return (
                            <button
                                key={item.name}
                                onClick={() => {
                                    if (isMore) {
                                        setShowMore(!showMore)
                                    } else {
                                        setShowMore(false)
                                    }
                                }}
                                className={cn(
                                    "flex flex-col items-center justify-center flex-1 h-full gap-1 transition-colors",
                                    isActive
                                        ? "text-primary"
                                        : "text-muted-foreground"
                                )}
                            >
                                {!isMore ? (
                                    <Link href={item.href} className="flex flex-col items-center gap-1">
                                        <item.icon className="h-5 w-5" />
                                        <span className="text-[10px] font-medium">{item.name}</span>
                                    </Link>
                                ) : (
                                    <>
                                        <item.icon className="h-5 w-5" />
                                        <span className="text-[10px] font-medium">{item.name}</span>
                                    </>
                                )}
                            </button>
                        )
                    })}
                </div>

                {/* Safe area padding for iOS */}
                <div className="h-[env(safe-area-inset-bottom)]" />
            </nav>

            {/* More Menu Overlay */}
            {showMore && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-40 bg-black/50 md:hidden"
                        onClick={() => setShowMore(false)}
                    />

                    {/* Menu */}
                    <div className="fixed bottom-20 left-4 right-4 z-50 rounded-lg bg-card border border-border p-2 md:hidden">
                        {moreMenuItems.map((item) => {
                            const isActive = pathname === item.href
                            return (
                                <Link
                                    key={item.name}
                                    href={item.href}
                                    onClick={() => setShowMore(false)}
                                    className={cn(
                                        "flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-medium transition-colors",
                                        isActive
                                            ? "bg-primary/10 text-primary"
                                            : "text-foreground hover:bg-muted"
                                    )}
                                >
                                    <item.icon className="h-5 w-5" />
                                    <span>{item.name}</span>
                                </Link>
                            )
                        })}
                    </div>
                </>
            )}
        </>
    )
}

// Mobile Header with hamburger menu
export function MobileHeader() {
    const [showMenu, setShowMenu] = useState(false)

    return (
        <>
            {/* Mobile Header - Only visible on mobile */}
            <header className="fixed top-0 left-0 right-0 z-50 h-14 border-b border-border bg-sidebar flex items-center justify-between px-4 md:hidden">
                {/* Logo */}
                <Link href="/" className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                        <Search className="h-4 w-4 text-white" />
                    </div>
                    <span className="text-lg font-bold">Rapot</span>
                </Link>

                {/* Bot Status */}
                <div className="flex items-center gap-2">
                    <div className="relative">
                        <div className="h-2 w-2 rounded-full bg-profit" />
                        <div className="absolute inset-0 h-2 w-2 animate-ping rounded-full bg-profit opacity-75" />
                    </div>
                    <span className="text-xs text-muted-foreground">Bot Aktif</span>
                </div>
            </header>
        </>
    )
}
