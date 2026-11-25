"use client"

import { RouteErrorView } from "@/components/shared/route-error"

export default function ResearchError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <RouteErrorView title="Araştırma Merkezi yüklenemedi" error={error} reset={reset} />
}
