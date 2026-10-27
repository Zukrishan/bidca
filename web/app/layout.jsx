import { Public_Sans } from "next/font/google";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { IdleLogout } from "@/components/IdleLogout";
import { SITE_NAME, SITE_URL } from "@/lib/config";
import "./globals.css";

const publicSans = Public_Sans({ subsets: ["latin"], variable: "--font-public-sans", display: "swap" });

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: `${SITE_NAME} — local auctions in British Columbia`, template: `%s | ${SITE_NAME}` },
  description: "Buy and sell locally across British Columbia. Bid on auctions or buy now, and pick up nearby.",
  openGraph: { siteName: SITE_NAME, locale: "en_CA", type: "website" },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en-CA" className={publicSans.variable}>
      <body className="min-h-screen font-sans antialiased">
        <Header />
        <main className="mx-auto max-w-[1200px] px-4 py-8 sm:px-6">{children}</main>
        <Footer />
        <IdleLogout />
      </body>
    </html>
  );
}
