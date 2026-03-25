"use client"

import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function ScannerError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="mx-auto flex min-h-[calc(100vh-40px)] w-full max-w-[1900px] items-center justify-center px-3 py-3 md:px-4">
      <div className="w-full max-w-lg space-y-3 border border-loss/40 bg-surface p-5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-loss" />
          <h1 className="text-sm font-semibold text-loss">Scanner sayfasi yuklenemedi</h1>
        </div>
        <p className="text-xs text-muted-foreground">
          {error?.message || "Beklenmeyen bir hata olustu. Sayfayi tekrar deneyin."}
        </p>
        <Button type="button" variant="outline" size="sm" className="h-8 text-xs" onClick={reset}>
          Tekrar dene
        </Button>
      </div>
    </div>
  )
}
