// 중간보고 입력관리 보드 페이지 (전용 셸)
import { Suspense } from "react"
import type { Metadata } from "next"
import { ManageBoard } from "@/features/redteam-manage/components/manage-board"

export const metadata: Metadata = {
  title: "중간보고 입력관리",
}

export default function RedteamManagePage() {
  return (
    <Suspense>
      <ManageBoard />
    </Suspense>
  )
}
