import type { Metadata, Viewport } from "next";
import { Figtree, Instrument_Serif, Kalam, Noto_Sans_Devanagari, Tiro_Devanagari_Hindi } from "next/font/google";
import "./globals.css";
import { AppProviders } from "@/providers/app-providers";
import { InkCursor } from "@/components/layout/ink-cursor";
import { PageLoader } from "@/components/brand/page-loader";

const display = Instrument_Serif({ subsets: ["latin"], weight: "400", style: ["normal", "italic"], variable: "--font-display-latin" });
const displayDeva = Tiro_Devanagari_Hindi({ subsets: ["devanagari"], weight: "400", variable: "--font-display-deva" });
const ui = Figtree({ subsets: ["latin"], variable: "--font-ui-latin" });
const uiDeva = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-ui-deva" });
const hand = Kalam({ subsets: ["latin", "devanagari"], weight: ["300", "400", "700"], variable: "--font-kalam" });

export const metadata: Metadata = {
  title: { default: "Shikshak — the teacher who notices", template: "%s · Shikshak" },
  description:
    "An AI teacher that teaches on video, pauses to check you understood, and explains it again — differently — when you didn't. English & हिन्दी.",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: "#fbfaf6",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${displayDeva.variable} ${ui.variable} ${uiDeva.variable} ${hand.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-paper font-sans text-ink antialiased">
        <AppProviders>
          <PageLoader />
          <InkCursor />
          {children}
        </AppProviders>
      </body>
    </html>
  );
}
