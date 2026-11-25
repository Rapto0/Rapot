"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function CalendarError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Ekonomik takvim yüklenemedi" error={error} reset={reset} />
}
