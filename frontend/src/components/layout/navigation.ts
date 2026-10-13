import { Activity, AlarmClock, BarChart3, Brain, CalendarDays, Compass, History, Home, Search, Settings } from "lucide-react"

export const navigation = [
  { name: "Ana Sayfa", shortName: "Ana", href: "/", icon: Home },
  { name: "Grafik", shortName: "Grafik", href: "/chart", icon: BarChart3 },
  { name: "Alarmlar", shortName: "Alarmlar", href: "/alarms", icon: AlarmClock },
  { name: "Tarayıcı", shortName: "Tarayıcı", href: "/scanner", icon: Search },
  { name: "Araştırma Merkezi", shortName: "Araştırma", href: "/research", icon: Compass },
  { name: "İşlemler", shortName: "İşlemler", href: "/trades", icon: History },
  { name: "Sistem Sağlığı", shortName: "Sağlık", href: "/health", icon: Activity },
  { name: "AI Analizi", shortName: "AI", href: "/ai", icon: Brain },
  { name: "Takvim", shortName: "Takvim", href: "/calendar", icon: CalendarDays },
  { name: "Ayarlar", shortName: "Ayarlar", href: "/settings", icon: Settings },
]

export function isActiveRoute(pathname: string, href: string) {
  return pathname === href || (href !== "/" && pathname.startsWith(`${href}/`))
}

export function pageName(pathname: string) {
  return navigation.find((item) => isActiveRoute(pathname, item.href))?.name
    ?? (pathname === "/login" ? "Giriş yap" : "Rapot")
}
