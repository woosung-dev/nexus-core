// 주차별 피드백 비교 페이지 (전용 셸)
import { Suspense } from "react"
import type { Metadata } from "next"
import { CompareClient } from "@/features/redteam-manage/components/compare-client"

export const metadata: Metadata = {
  title: "주차별 비교 · 중간보고 입력관리",
}

export default function RedteamManageComparePage() {
  return (
    <Suspense>
      <CompareClient />
    </Suspense>
  )
}
