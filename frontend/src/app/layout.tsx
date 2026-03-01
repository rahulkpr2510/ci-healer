// frontend/src/app/layout.tsx

import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AuthGuard from "@/components/auth/AuthGuard";
import WarmupPinger from "@/components/WarmupPinger";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

const APP_URL = process.env.NEXT_PUBLIC_APP_URL ?? "https://cihealer.dev";

export const metadata: Metadata = {
  metadataBase: new URL(APP_URL),
  title: {
    default: "CI Healer — AI-Powered CI/CD Auto-Fixer",
    template: "%s | CI Healer",
  },
  description:
    "Connect your GitHub repository and let our AI agent automatically diagnose failing tests, generate fixes, and open a pull request. Powered by Gemini 2.5 Flash.",
  keywords: [
    "CI/CD",
    "AI devops",
    "auto fix",
    "GitHub Actions",
    "test automation",
    "LangGraph",
    "Gemini",
  ],
  authors: [{ name: "CI Healer" }],
  creator: "CI Healer",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: APP_URL,
    siteName: "CI Healer",
    title: "CI Healer — AI-Powered CI/CD Auto-Fixer",
    description:
      "Automatically diagnose and fix failing CI pipelines using an AI agent powered by Gemini 2.5 Flash and LangGraph.",
    images: [{ url: "/og.png", width: 1200, height: 630, alt: "CI Healer" }],
  },
  twitter: {
    card: "summary_large_image",
    title: "CI Healer — AI-Powered CI/CD Auto-Fixer",
    description: "Automatically fix failing CI pipelines with AI.",
    images: ["/og.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true },
  },
};

export const viewport: Viewport = {
  themeColor: "#09090b",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="font-[var(--font-inter)] antialiased">
        <AuthGuard>
          <WarmupPinger />
          {children}
        </AuthGuard>
      </body>
    </html>
  );
}
