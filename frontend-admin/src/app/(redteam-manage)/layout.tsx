// 중간보고 입력관리 전용 라우트 그룹 레이아웃 — "운영 콘솔" 폰트(IBM Plex Sans KR + JetBrains Mono).
import { IBM_Plex_Sans_KR, JetBrains_Mono } from "next/font/google"
import { RedteamManageShell } from "@/features/redteam-manage/shell/redteam-manage-shell"

const plexSansKr = IBM_Plex_Sans_KR({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-plex-sans-kr",
  display: "swap",
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-jetbrains",
  display: "swap",
})

export default function RedteamManageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${plexSansKr.variable} ${jetbrainsMono.variable}`}>
      <RedteamManageShell>{children}</RedteamManageShell>
    </div>
  )
}
