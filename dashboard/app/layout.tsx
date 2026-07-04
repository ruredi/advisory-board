import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";

import { Providers } from "@/components/providers";
import { AppShell } from "@/components/app-shell";
import { ApiGuard } from "@/components/shared/api-guard";
import { htmlThemeClass, isTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Advisory Board Admin",
  description: "Advisory Board memória pipeline admin dashboard",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const themeCookie = (await cookies()).get("theme")?.value;
  const themeClass = isTheme(themeCookie) ? htmlThemeClass(themeCookie) : undefined;

  return (
    <html
      lang="hu"
      suppressHydrationWarning
      className={cn(
        "h-full",
        "antialiased",
        geistSans.variable,
        geistMono.variable,
        "font-sans",
        inter.variable,
        themeClass
      )}
    >
      <body className="min-h-full">
        <Providers>
          <AppShell>
            <ApiGuard>{children}</ApiGuard>
          </AppShell>
        </Providers>
      </body>
    </html>
  );
}
