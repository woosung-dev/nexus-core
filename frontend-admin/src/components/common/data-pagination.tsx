// 목록 하단 페이지 이동. 다섯 벌이 복붙돼 있었고 서로 달랐다 — 어떤 곳은 총 건수를
// 안 보여 주고, 어떤 곳은 현재 쪽 표기가 없고, 색도 zinc 하드코딩이었다.
//
// TanStack Table 을 쓰는 화면은 table.getState().pagination 값을 그대로 넘기면 된다.
import { ChevronLeft, ChevronRight } from "lucide-react"

import { Button } from "@/components/ui/button"

export function DataPagination({
  page,
  pageSize,
  total,
  onPageChange,
  /** 「기록」·「문서」처럼 세는 대상 이름 */
  unit = "건",
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  unit?: string
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-1">
      <p className="text-xs tabular-nums text-muted-foreground">
        총 {total.toLocaleString()}
        {unit} 중 {first.toLocaleString()} – {last.toLocaleString()}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="size-4" aria-hidden />
          이전
        </Button>
        <span className="px-2 text-xs tabular-nums text-muted-foreground">
          {page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
        >
          다음
          <ChevronRight className="size-4" aria-hidden />
        </Button>
      </div>
    </div>
  )
}
