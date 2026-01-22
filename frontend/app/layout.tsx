import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "OtonomTradingbot Dashboard",
  description: "TradingView kalitesinde admin panel"
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr" className="dark">
      <body>{children}</body>
    </html>
  );
}
