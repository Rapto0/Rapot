import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { MobileNav, MobileHeader } from "@/components/layout/mobile-nav";
import { MainContent } from "@/components/layout/main-content";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "Rapot Dashboard | Finansal Analiz Platformu",
  description: "Profesyonel BIST ve Kripto piyasa tarama, sinyal ve trade takip platformu",
  keywords: ["BIST", "Kripto", "Trading", "Sinyal", "Analiz", "Dashboard"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" className="dark">
      <body
        className="antialiased bg-background text-foreground font-sans"
      >
        <Providers>
          {/* Desktop Navigation */}
          <Sidebar />
          <Header />

          {/* Mobile Navigation */}
          <MobileHeader />
          <MobileNav />

          {/* Main Content - Responsive margins */}
          <MainContent>
            {children}
          </MainContent>
        </Providers>
      </body>
    </html>
  );
}
