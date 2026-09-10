import type { ScanStatus as ScanStatusValue } from "@/lib/api/types"

const SCAN_STATUS = {
  success: { label: "Tamamlandı", className: "text-profit" },
  partial: { label: "Kısmen tamamlandı", className: "text-neutral" },
  failed: { label: "Başarısız", className: "text-loss" },
  cancelled: { label: "İptal edildi", className: "text-neutral" },
  unknown: { label: "Sonuç bilinmiyor", className: "text-muted-foreground" },
} as const

export function ScanStatus({ status }: { status?: ScanStatusValue | null }) {
  const result = status && Object.hasOwn(SCAN_STATUS, status) ? SCAN_STATUS[status] : SCAN_STATUS.unknown

  return <span className={result.className}>{result.label}</span>
}
