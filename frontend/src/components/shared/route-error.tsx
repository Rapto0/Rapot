"use client"

import Link from "next/link"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

export function RouteErrorView({
  title,
  error,
  reset,
}: {
  title: string
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-[1680px] items-center justify-center px-3 py-6 md:px-4">
      <div className="w-full max-w-lg space-y-4 border border-loss/40 bg-surface p-5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-loss" aria-hidden="true" />
          <h1 className="text-sm font-semibold text-loss">{title}</h1>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          {error?.message || "Beklenmeyen bir hata oluştu. Sayfayı yeniden deneyebilir veya ana sayfaya dönebilirsiniz."}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" className="min-h-11 text-xs" onClick={reset}>
            Tekrar dene
          </Button>
          <Link href="/" className="inline-flex min-h-11 items-center rounded-sm border border-border px-3 text-xs hover:bg-raised">
            Ana sayfaya dön
          </Link>
        </div>
      </div>
    </div>
  )
}
