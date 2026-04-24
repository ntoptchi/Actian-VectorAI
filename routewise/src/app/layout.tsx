import "~/styles/globals.css";

import { type Metadata } from "next";
import { Inter_Tight, IBM_Plex_Mono } from "next/font/google";

import { TRPCReactProvider } from "~/trpc/react";

export const metadata: Metadata = {
  title: "RouteWise — Safety is the new shortest path",
  description:
    "RouteWise re-ranks driving routes by crash risk for tonight's conditions, powered by Actian VectorAI DB.",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

const interTight = Inter_Tight({
  subsets: ["latin"],
  variable: "--font-inter-tight",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
});

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${interTight.variable} ${plexMono.variable}`}
    >
      <body className="bg-paper text-ink antialiased">
        <TRPCReactProvider>{children}</TRPCReactProvider>
      </body>
    </html>
  );
}
