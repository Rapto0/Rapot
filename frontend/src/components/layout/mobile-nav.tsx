"use client"

import { useEffect, useRef, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Menu, X } from "lucide-react"
import { cn } from "@/lib/utils"
import { SessionControls } from "@/components/auth/session-controls"
import { isActiveRoute, navigation, pageName } from "./navigation"

const primaryItems = navigation.slice(0, 4)
const moreItems = navigation.slice(4)

export function MobileNav() {
  const pathname = usePathname()
  const dialogRef = useRef<HTMLDialogElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const [isOpen, setIsOpen] = useState(false)
  const moreActive = moreItems.some((item) => isActiveRoute(pathname, item.href))

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (isOpen && !dialog.open) dialog.showModal()
    if (!isOpen && dialog.open) dialog.close()
    if (!isOpen) return

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const desktop = window.matchMedia("(min-width: 768px)")
    const closeOnDesktop = () => { if (desktop.matches) dialog.close() }
    desktop.addEventListener("change", closeOnDesktop)
    closeOnDesktop()
    return () => {
      document.body.style.overflow = previousOverflow
      desktop.removeEventListener("change", closeOnDesktop)
    }
  }, [isOpen])

  // Back/forward navigation must not leave a modal over the new page.
  useEffect(() => { dialogRef.current?.close() }, [pathname])

  return (
    <>
      <nav aria-label="Mobil gezinme" className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] md:hidden">
        <div className="grid min-h-[64px] grid-cols-5">
          {primaryItems.map((item) => {
            const active = isActiveRoute(pathname, item.href)
            return (
              <Link key={item.href} href={item.href} aria-label={item.name} aria-current={active ? "page" : undefined}
                className={cn("flex min-w-0 flex-col items-center justify-center gap-1 text-[11px] text-muted-foreground", active && "bg-raised text-foreground")}>
                <item.icon className="h-[18px] w-[18px]" aria-hidden="true" />
                <span>{item.shortName}</span>
              </Link>
            )
          })}
          <button ref={triggerRef} type="button" aria-haspopup="dialog" aria-controls="mobile-menu" aria-expanded={isOpen}
            onClick={() => setIsOpen(true)}
            className={cn("flex min-w-0 flex-col items-center justify-center gap-1 text-[11px] text-muted-foreground", (moreActive || isOpen) && "bg-raised text-foreground")}>
            <Menu className="h-[18px] w-[18px]" aria-hidden="true" />
            <span>Diğer</span>
          </button>
        </div>
      </nav>
      <dialog ref={dialogRef} id="mobile-menu" aria-labelledby="mobile-menu-title"
        onClose={() => {
          setIsOpen(false)
          if (!window.matchMedia("(min-width: 768px)").matches) triggerRef.current?.focus()
        }}
        onClick={(event) => { if (event.target === event.currentTarget) dialogRef.current?.close() }}
        className="fixed inset-x-0 bottom-0 top-auto m-0 max-h-[85dvh] w-full max-w-none overflow-y-auto border border-border bg-overlay p-0 text-foreground backdrop:bg-black/60">
        <div className="px-4 pb-[max(16px,env(safe-area-inset-bottom))] pt-3">
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 id="mobile-menu-title" className="text-base font-semibold text-foreground">Diğer sayfalar</h2>
            <button type="button" aria-label="Menüyü kapat" onClick={() => dialogRef.current?.close()}
              className="flex h-[44px] w-[44px] items-center justify-center border border-border hover:bg-raised">
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
          <nav aria-label="Diğer sayfalar" className="grid grid-cols-2 gap-2">
            {moreItems.map((item) => (
              <Link key={item.href} href={item.href} onClick={() => dialogRef.current?.close()}
                aria-current={isActiveRoute(pathname, item.href) ? "page" : undefined}
                className={cn("flex min-h-[52px] items-center gap-3 border border-border px-3 text-sm hover:bg-raised", isActiveRoute(pathname, item.href) && "bg-raised font-semibold")}>
                <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
      </dialog>
    </>
  )
}

export function MobileHeader() {
  const pathname = usePathname()
  return (
    <header className="fixed inset-x-0 top-0 z-50 flex h-[56px] items-center justify-between gap-3 border-b border-border bg-surface px-3 md:hidden">
      <Link href="/" className="flex min-w-0 items-center gap-2" aria-label="Rapot ana sayfa">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-border bg-raised text-xs font-semibold">R</span>
        <span className="truncate text-sm font-semibold">{pageName(pathname)}</span>
      </Link>
      <div className="min-w-0 shrink-0"><SessionControls /></div>
    </header>
  )
}
