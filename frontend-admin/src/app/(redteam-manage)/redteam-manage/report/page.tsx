// 보고서 탭 — 1~3주차 발전·위험·분류 분석 (문서형)
import type { Metadata } from "next"
import { ReportClient } from "@/features/redteam-manage/components/report-client"

export const metadata: Metadata = {
  title: "레드팀 결과 보고서 · 입력관리",
}

export default function RedteamManageReportPage() {
  return <ReportClient />
}
