import { OpsFactsBoard } from "@/features/ops-facts/components/ops-facts-board"

/**
 * 운영 사실 관리 페이지.
 * 규정집이 답해주지 않는 것 — 폐지된 기준, 존재하지 않는 제도, 표기, 연락처, 위기 자원 —
 * 을 관리자가 판정해 챗봇 답변에 반영한다.
 */
export default function OpsFactsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">운영 사실 관리</h1>
        <p className="text-muted-foreground">
          규정집에 없거나 규정집과 다른 <b>확정 사항</b>을 관리합니다. 검색된 문서보다 우선 적용됩니다.
          <br />
          승인하신 항목만 챗봇 답변에 쓰입니다 — 등록만으로는 아무것도 바뀌지 않습니다.
        </p>
      </div>
      <OpsFactsBoard />
    </div>
  )
}
