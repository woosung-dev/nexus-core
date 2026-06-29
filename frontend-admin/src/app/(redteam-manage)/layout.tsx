// 중간보고 입력관리 전용 라우트 그룹 레이아웃 — admin/redteam 셸과 분리. "심의·봉인" 폰트 재사용.
import { IBM_Plex_Mono, Noto_Sans_KR, Noto_Serif_KR } from "next/font/google"
import { RedteamManageShell } from "@/features/redteam-manage/shell/redteam-manage-shell"

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

export default function RedteamManageLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className={`${notoSans.variable} ${notoSerif.variable} ${plexMono.variable}`}>
      <RedteamManageShell>{children}</RedteamManageShell>
    </div>
  )
}
