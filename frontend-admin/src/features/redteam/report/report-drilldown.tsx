"use client"

// 보고 드릴다운 — 차트/표 클릭 시 우측 Sheet로 질문 리스트→상세(읽기전용)를 연다.
import * as React from "react"
import { useRouter } from "next/navigation"
import { ChevronLeft, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { useRedteamGroups } from "../hooks"
import { GroupDetailPanel } from "../components/group-detail"
import { GroupList } from "../components/group-list"

export type DrillFilter = {
  label: string
  risk?: string
  category?: string
  groupId?: number
}

export function ReportDrilldown({
  filter,
  onClose,
}: {
  filter: DrillFilter | null
  onClose: () => void
}) {
  const router = useRouter()
  const [detailId, setDetailId] = React.useState<number | null>(null)

  // 필터 변경 시 단계 초기화 (group_id 직접 진입이면 바로 상세)
  React.useEffect(() => {
    setDetailId(filter?.groupId ?? null)
  }, [filter])

  const listEnabled = !!filter && filter.groupId == null
  const { data, isLoading } = useRedteamGroups({
    risk: filter?.risk,
    category: filter?.category,
    page: 1,
    page_size: 100,
  })

  const directDetail = filter?.groupId != null

  return (
    <Sheet open={!!filter} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="border-b px-4 py-3">
          <SheetTitle className="flex items-center gap-2 text-sm">
            {detailId !== null && !directDetail && (
              <button
                onClick={() => setDetailId(null)}
                className="inline-flex items-center gap-1 text-muted-foreground hover:text-foreground"
              >
                <ChevronLeft className="size-4" /> 목록
              </button>
            )}
            <span className="truncate">{filter?.label ?? ""}</span>
          </SheetTitle>
        </SheetHeader>

        <div className="min-h-0 flex-1 overflow-auto">
          {detailId !== null ? (
            <>
              <div className="flex justify-end border-b bg-muted/30 px-4 py-2">
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs"
                  onClick={() => router.push(`/redteam?selectedId=${detailId}`)}
                >
                  <ExternalLink className="size-3" /> 이 질문 검토하기
                </Button>
              </div>
              <GroupDetailPanel groupId={detailId} readOnly />
            </>
          ) : listEnabled ? (
            <GroupList
              groups={data?.groups ?? []}
              total={data?.total ?? 0}
              isLoading={isLoading}
              selectedId={null}
              onSelect={setDetailId}
              reviewerNames={[]}
            />
          ) : null}
        </div>
      </SheetContent>
    </Sheet>
  )
}
