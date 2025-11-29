import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { ConfigProvider } from "./app-providers";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Neumann Search UI",
  description: "Hybrid search frontend for the Neumann pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-background text-foreground`}>
        <ConfigProvider>
          <div className="min-h-screen">
            {children}
          </div>
        </ConfigProvider>
      </body>
    </html>
  );
}
