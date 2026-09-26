import type { Metadata, Viewport } from "next";
import { Big_Shoulders, Martian_Mono, Public_Sans } from "next/font/google";
import { Nav } from "@/components/nav/Nav";
import "./globals.css";

// Signage and instrument type (F21 decision 2): condensed display for headings and figures, the U.S. government's
// USWDS face for reading, mono for every number and id.
const display = Big_Shoulders({ subsets: ["latin"], axes: ["opsz"], variable: "--gb-display", display: "swap" });
const sans = Public_Sans({ subsets: ["latin"], variable: "--gb-sans", display: "swap" });
const mono = Martian_Mono({ subsets: ["latin"], variable: "--gb-mono", display: "swap" });

export const viewport: Viewport = { themeColor: "#06080d", colorScheme: "dark" };

export const metadata: Metadata = {
  title: "GridBridge: transmission coordination leads",
  description:
    "Where Dominion Energy South Carolina and Georgia Power plan transmission work within 25 miles of each other, traced to public filings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable} ${mono.variable}`}>
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
