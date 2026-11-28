const exchangeClock = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Istanbul", year: "numeric", month: "2-digit", day: "2-digit",
    weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
})

// Borsa İstanbul Pay Piyasası 2026 holiday schedule. Unknown weekday calendars remain unknown.
const holidays2026 = new Set(["01-01", "03-20", "04-23", "05-01", "05-19", "05-27", "05-28", "05-29", "07-15", "10-29"])
const halfDays2026 = new Set(["03-19", "05-26", "10-28"])
const sessionStartMinutes = 9 * 60 + 40
const fullDayEndMinutes = 18 * 60 + 10
const halfDayEndMinutes = 13 * 60

export function bistSessionLabel(now: number): string {
    if (!Number.isFinite(new Date(now).getTime()) || now <= 0) return "Seans takvimi bekleniyor"
    const { year, month, day, weekday, hour, minute } = Object.fromEntries(exchangeClock.formatToParts(now).map(part => [part.type, part.value]))
    if (weekday === "Sat" || weekday === "Sun") return "Seans kapalı · Hafta sonu"
    if (year !== "2026") return "Güncel seans takvimi bekleniyor"
    const dayKey = `${month}-${day}`
    if (holidays2026.has(dayKey)) return "Seans kapalı · Resmî tatil"
    const halfDay = halfDays2026.has(dayKey)
    const minutes = Number(hour) * 60 + Number(minute)
    const end = halfDay ? halfDayEndMinutes : fullDayEndMinutes
    if (minutes < sessionStartMinutes || minutes >= end) return "Seans kapalı · Planlanan saatler dışında"
    return halfDay ? "Planlı seans · Yarım gün" : "Planlı seans saatleri"
}
