import type { Metadata } from "next";
import { Nav } from "@/components/nav/Nav";
import "./globals.css";

export const metadata: Metadata = {
  title: "GridBridge: transmission coordination leads",
  description:
    "Where Dominion Energy South Carolina and Georgia Power plan transmission work within 25 miles of each other, traced to public filings.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Nav />
        {children}
      </body>
    </html>
  );
}
