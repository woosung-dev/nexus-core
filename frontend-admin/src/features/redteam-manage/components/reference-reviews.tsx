"use client"

// 리뷰어 입력 참고 (읽기 전용) — 검토 대시보드의 3인 '옳은 답변'을 모범답변 작성 참고용으로 표시.
import { Badge } from "@/components/ui/badge"
import type { ReviewItem } from "../types"

const REFLECT_LABEL: Record<string, string> = {
  reflect: "반영",
  skip: "미반영",
  pending: "보류",
}

export function ReferenceReviews({ reviews }: { reviews: ReviewItem[] }) {
  const filled = reviews.filter((r) => r.correct_answer.trim())

  return (
    <div className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-4">
      <h3 className="text-sm font-semibold">리뷰어 옳은 답변 · 반영여부 (참고)</h3>
      {filled.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          검토 대시보드에서 입력된 리뷰어 옳은 답변이 아직 없습니다.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {filled.map((r) => (
            <li key={r.reviewer} className="rounded-md border bg-card p-3">
              <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary" className="text-[10px]">
                  {r.reviewer}
                </Badge>
                <span className="text-[10px] text-muted-foreground">
                  3주 {REFLECT_LABEL[r.week3_reflect]} · 2주 {REFLECT_LABEL[r.week2_reflect]} · 1주{" "}
                  {REFLECT_LABEL[r.week1_reflect]}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                {r.correct_answer}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
