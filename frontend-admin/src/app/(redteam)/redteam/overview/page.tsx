// 레드팀 현황(개요) 페이지 — 상태등 KPI + 처리할 일 커맨드보드
import type { Metadata } from "next"
import { OverviewClient } from "@/features/redteam/overview/overview-client"

export const metadata: Metadata = {
  title: "레드팀 현황",
}

export default function RedteamOverviewPage() {
  return <OverviewClient />
}
