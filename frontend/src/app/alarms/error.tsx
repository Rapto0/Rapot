"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function AlarmsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Alarm merkezi yüklenemedi" error={error} reset={reset} />
}
