// 미분류 큐 페이지 (전용 셸)
import { Suspense } from "react"
import type { Metadata } from "next"
import { UnmatchedClient } from "@/features/redteam-manage/components/unmatched-client"

export const metadata: Metadata = {
  title: "미분류 큐 · 중간보고 입력관리",
}

export default function RedteamManageUnmatchedPage() {
  return (
    <Suspense>
      <UnmatchedClient />
    </Suspense>
  )
}
