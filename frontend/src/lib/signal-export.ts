import type { Signal } from "@/lib/hooks/use-signals"

export const SIGNAL_EXPORT_LIMIT = 300

const SPECIAL_TAG_LABELS = {
  BELES: "BELEŞ",
  COK_UCUZ: "ÇOK UCUZ",
  PAHALI: "PAHALI",
  FAHIS_FIYAT: "FAHİŞ FİYAT",
} as const

function textCell(value: unknown): string {
  let text = typeof value === "string" ? value : ""
  // Quotes protect CSV boundaries; the apostrophe also prevents spreadsheet formulas.
  if (/^[\s\u0000-\u001f]*[=+\-@]/u.test(text)) text = `'${text}`
  return `"${text.replaceAll('"', '""')}"`
}

function numberCell(value: unknown): string {
  // Keep actual numbers numeric in a Turkish semicolon-delimited CSV.
  return typeof value === "number" && Number.isFinite(value)
    ? String(value).replace(".", ",")
    : ""
}

function utcDate(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) return ""
  const date = new Date(value)
  return Number.isFinite(date.getTime()) ? date.toISOString() : ""
}

/** Serialize the supplied visible rows in their current order; never fetch or invent rows. */
export function buildSignalCsv(rows: readonly Signal[]): string {
  const header = [
    "Sembol", "Piyasa", "Strateji", "Özel", "Yön", "Zaman Dilimi", "Skor", "Fiyat", "Tarih (UTC)",
  ].map(textCell).join(";")
  const records = rows.map((row) => [
    textCell(row.symbol),
    textCell(row.marketType),
    textCell(row.strategy),
    textCell(row.specialTag ? SPECIAL_TAG_LABELS[row.specialTag] : ""),
    textCell(row.signalType),
    textCell(row.timeframe),
    textCell(row.score),
    numberCell(row.price),
    textCell(utcDate(row.createdAt)),
  ].join(";"))
  return `\uFEFF${[header, ...records].join("\r\n")}\r\n`
}
