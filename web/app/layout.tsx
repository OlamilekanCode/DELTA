import type { Metadata } from "next";
import type React from "react";
import { Space_Grotesk, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/nav/Navigation";
import Footer from "@/components/shared/Footer";
import MouseGlow from "@/components/shared/MouseGlow";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
  preload: true,
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
  preload: false,
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400"],
  display: "swap",
  preload: false,
});

export const metadata: Metadata = {
  title: "DELTA — Map the Market",
  description:
    "DELTA maps how stocks and crypto move together using historical market data. Discover which crypto assets have historically tracked any stock ticker.",
  keywords: ["stock crypto correlation", "exposure score", "stock crypto", "market analytics"],
  icons: { icon: "/favicon.svg", apple: "/favicon.svg" },
  openGraph: {
    title: "DELTA — Map the Market",
    description:
      "See how any stock and crypto move together. Explore Exposure Scores and interactive market graphs.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${inter.variable} ${ibmPlexMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-bg text-text font-body">
        <MouseGlow />
        <Navigation />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
