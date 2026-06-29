// 레드팀 전용 라우트 그룹 레이아웃 — admin 셸과 분리. "심의·봉인" 폰트:
// 세리프(말) Noto Serif KR · 본문 Noto Sans KR · 판정/데이터 모노 IBM Plex Mono
import { IBM_Plex_Mono, Noto_Sans_KR, Noto_Serif_KR } from "next/font/google"
import { RedteamShell } from "@/features/redteam/shell/redteam-shell"

const notoSans = Noto_Sans_KR({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-noto-sans",
  display: "swap",
})

const notoSerif = Noto_Serif_KR({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-noto-serif",
  display: "swap",
})

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["500", "600"],
  variable: "--font-plex-mono",
  display: "swap",
})

export default function RedteamLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${notoSans.variable} ${notoSerif.variable} ${plexMono.variable}`}>
      <RedteamShell>{children}</RedteamShell>
    </div>
  )
}
