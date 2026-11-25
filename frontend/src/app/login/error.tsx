"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function LoginError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Giriş ekranı yüklenemedi" error={error} reset={reset} />
}
