import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import Providers from "@/components/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// 운영 도메인 — Vercel/사용자 운영 환경에서 NEXT_PUBLIC_SITE_URL 로 주입.
// 미설정 시 localhost fallback. OG/Twitter 카드의 absolute URL 빌드 기준점.
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
const SITE_NAME = "Nexus";
const SITE_DESCRIPTION =
  "다양한 AI 챗봇과 대화하며 궁금했던 부분을 해결해 보세요.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} — AI 챗봇 포털`,
    template: `%s | ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: ["Nexus", "AI 챗봇", "AI 상담", "챗봇 포털", "AI assistant"],
  openGraph: {
    type: "website",
    locale: "ko_KR",
    siteName: SITE_NAME,
    url: "/",
    title: `${SITE_NAME} — AI 챗봇 포털`,
    description: SITE_DESCRIPTION,
    // /opengraph-image (app/opengraph-image.tsx) 가 1200x630 PNG 동적 생성.
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: `${SITE_NAME} — AI 챗봇 포털`,
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: `${SITE_NAME} — AI 챗봇 포털`,
    description: SITE_DESCRIPTION,
    images: ["/opengraph-image"],
  },
  // 기본은 인덱싱 허용. 페이지별로 noindex 오버라이드.
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider signInUrl="/login" signUpUrl="/signup">
      <html lang="ko" className="dark" suppressHydrationWarning>
        <body
          className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        >
          <Providers>{children}</Providers>
        </body>
      </html>
    </ClerkProvider>
  );
}
