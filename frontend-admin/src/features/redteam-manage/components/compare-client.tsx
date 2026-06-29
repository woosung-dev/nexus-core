"use client"

// 비교 탭 — 1·2주차가 매칭된 기준질문을 골라 주차별 피드백/평점 차이를 비교.
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useManageGroups } from "../hooks"
import { CompareColumns } from "./compare-columns"
import { ManageGroupList } from "./manage-group-list"

const PAGE_SIZE = 50

export function CompareClient() {
  const searchParams = useSearchParams()
  const initialId = searchParams.get("selectedId")
  const [selectedId, setSelectedId] = React.useState<number | null>(
    initialId ? Number(initialId) : null
  )
  const [rawQ, setRawQ] = React.useState("")
  const [q, setQ] = React.useState("")
  const [page, setPage] = React.useState(1)

  React.useEffect(() => {
    const t = setTimeout(() => {
      setQ(rawQ)
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [rawQ])

  const { data, isLoading } = useManageGroups({
    matched_only: true, // 1·2주차 매칭이 있는 그룹만 (비교 의미 있음)
    q: q || undefined,
    page,
    page_size: PAGE_SIZE,
  })
  const groups = data?.groups ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      <div className="mb-4">
        <h1 className="rtm-display text-xl tracking-tight">주차별 피드백 비교</h1>
        <p className="text-sm text-muted-foreground">
          3주차 질문과 동일한 1·2주차 질문을 찾아, 발전된 봇에 대한 평가가 어떻게 달라졌는지 비교합니다.
        </p>
      </div>

      <div className="mb-4">
        <Input
          value={rawQ}
          onChange={(e) => setRawQ(e.target.value)}
          placeholder="질문 검색... (1·2주차 매칭된 질문만 표시)"
          className="h-8 w-72 text-xs"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[340px_1fr]">
        <div className="flex flex-col overflow-hidden rounded-lg border">
          <div className="max-h-[72vh] overflow-y-auto">
            <ManageGroupList
              groups={groups}
              total={total}
              isLoading={isLoading}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
          <div className="flex items-center justify-between border-t bg-background px-3 py-2 text-xs">
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="size-3" /> 이전
            </Button>
            <span className="tabular-nums text-muted-foreground">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              다음 <ChevronRight className="size-3" />
            </Button>
          </div>
        </div>

        <div className="rounded-lg border">
          <CompareColumns groupId={selectedId} />
        </div>
      </div>
    </div>
  )
}
