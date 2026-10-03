import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GhostNet | Marine Debris Intelligence Platform",
  description:
    "Decision-support prototype for marine debris / ghost-gear detection, drift forecasting, and ecological risk assessment. DEMO data - not an operational system.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-ocean-950 text-slate-100 antialiased">{children}</body>
    </html>
  );
}
