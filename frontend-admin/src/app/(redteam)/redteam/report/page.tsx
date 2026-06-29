// 레드팀 피드백 종합 보고 페이지 (전용 셸)
import type { Metadata } from "next"
import { ReportClient } from "@/features/redteam/report/report-client"

export const metadata: Metadata = {
  title: "레드팀 피드백 종합 보고",
}

export default function RedteamReportPage() {
  return <ReportClient />
}
