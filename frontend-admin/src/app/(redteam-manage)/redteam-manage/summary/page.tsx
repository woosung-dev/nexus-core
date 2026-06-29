// 중간보고 요약 페이지 (전용 셸)
import type { Metadata } from "next"
import { SummaryClient } from "@/features/redteam-manage/components/summary-client"

export const metadata: Metadata = {
  title: "중간보고 요약 · 입력관리",
}

export default function RedteamManageSummaryPage() {
  return <SummaryClient />
}
