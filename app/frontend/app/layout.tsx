import type { Metadata } from "next";

import { APP_NAME } from "@/lib/site";

import "./globals.css";

export const metadata: Metadata = {
  title: APP_NAME,
  description: `${APP_NAME}: built with App Creator`,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr">
      <head>
        {/* Police Jost (Google Fonts) ; hors ligne, repli sur Calibri / police système */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link href="https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body>{children}</body>
    </html>
  );
}
