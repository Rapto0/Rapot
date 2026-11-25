"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function RootError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Sayfa yüklenemedi" error={error} reset={reset} />
}
