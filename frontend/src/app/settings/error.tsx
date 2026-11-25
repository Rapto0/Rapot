"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function SettingsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Ayarlar sayfası yüklenemedi" error={error} reset={reset} />
}
