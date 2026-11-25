"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function AIError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="AI terminali yüklenemedi" error={error} reset={reset} />
}
