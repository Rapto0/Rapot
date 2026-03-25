"use client"

import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function HealthError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-[1700px] items-center justify-center p-3 md:p-4">
      <div className="w-full max-w-md space-y-3 border border-loss/40 bg-surface p-5 text-center">
        <div className="mx-auto flex h-9 w-9 items-center justify-center border border-loss/40 bg-loss/10 text-loss">
          <AlertTriangle className="h-4 w-4" />
        </div>
        <h1 className="text-sm font-semibold text-loss">Saglik sayfasi yuklenemedi</h1>
        <p className="text-xs text-muted-foreground">
          {error?.message || "Beklenmeyen bir hata olustu. Lütfen tekrar deneyin."}
        </p>
        <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={reset}>
          Tekrar dene
        </Button>
      </div>
    </div>
  )
}
