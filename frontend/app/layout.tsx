import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "GroundTruth · grounded customer assistant",
    template: "%s · GroundTruth",
  },
  description: "GroundTruth: Multi-tenant AI assistant grounded in documentation with RAG citations, an embeddable widget, and per-tenant cost reporting.",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
  openGraph: {
    title: "GroundTruth · grounded customer assistant",
    description: "GroundTruth: Multi-tenant AI assistant grounded in your docs.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
