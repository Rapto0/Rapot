import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { MobileNav, MobileHeader } from "@/components/layout/mobile-nav";
import { Providers } from "@/components/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

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
        className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}
      >
        <Providers>
          {/* Desktop Navigation */}
          <Sidebar />
          <Header />

          {/* Mobile Navigation */}
          <MobileHeader />
          <MobileNav />

          {/* Main Content - Responsive margins */}
          <main className="pt-14 pb-20 md:pb-4 md:ml-56 min-h-screen p-4">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
