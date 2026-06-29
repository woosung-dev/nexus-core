// 레드팀 피드백 검토·입력 페이지 (전용 셸)
import { Suspense } from "react"
import type { Metadata } from "next"
import { RedteamDashboard } from "@/features/redteam/components/redteam-dashboard"

export const metadata: Metadata = {
  title: "레드팀 피드백 검토",
}

export default function RedteamReviewPage() {
  return (
    <Suspense>
      <RedteamDashboard />
    </Suspense>
  )
}
