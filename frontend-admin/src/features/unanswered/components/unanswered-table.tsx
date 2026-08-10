"use client"

/**
 * 못 답한 질문 — 빈도순 목록.
 *
 * **빈도순이 핵심이다.** 「무엇부터 채울지」를 이 순서가 정해 준다. 그래서 횟수 컬럼이
 * 질문 바로 옆에 있고 기본 정렬이 count 다.
 *
 * 서버 페이지네이션이다(`ChatHistoryList` 와 같은 규약) — 그룹 수가 늘어도 목록이
 * 한 번에 다 오지 않는다.
 */
import { ChevronLeft, ChevronRight, Inbox, Loader2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

import { REASON_LABEL, REASON_STYLE, TRIAGE_RING } from "../constants"
import type { UnansweredGroup, UnansweredTriage } from "../types"
import { TriageSelect } from "./triage-select"

/** 「2시간 전」. 이 레포엔 날짜 라이브러리가 없어 최소한만 직접 만든다. */
function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diffMs / 60_000)
  if (min < 1) return "방금"
  if (min < 60) return `${min}분 전`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour}시간 전`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day}일 전`
  return new Date(iso).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}

type Props = {
  items: UnansweredGroup[]
  isLoading: boolean
  isError: boolean
  error?: Error | null
  total: number
  page: number
  pageSize: number
  sort: "count" | "recent"
  /** 봇 id → 이름. 표에 숫자만 뜨면 무슨 봇인지 알 수 없다. */
  botNames: Record<number, string>
  pendingNorm: string | null
  onPageChange: (page: number) => void
  onSortChange: (sort: "count" | "recent") => void
  onTriageChange: (group: UnansweredGroup, next: UnansweredTriage) => void
  onOpenDetail: (group: UnansweredGroup) => void
}

export function UnansweredTable({
  items,
  isLoading,
  isError,
  error,
  total,
  page,
  pageSize,
  sort,
  botNames,
  pendingNorm,
  onPageChange,
  onSortChange,
  onTriageChange,
  onOpenDetail,
}: Props) {
  const totalPages = Math.ceil(total / pageSize) || 1

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-8 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> 불러오는 중
      </div>
    )
  }

  if (isError) {
    return (
      <p className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-950/30 dark:text-red-300">
        목록을 불러오지 못했습니다: {error?.message}
      </p>
    )
  }

  if (items.length === 0) {
    return (
      <div className="rounded-md border p-10 text-center text-sm text-muted-foreground">
        <Inbox className="mx-auto mb-3 size-8 opacity-40" aria-hidden />
        <p className="font-medium text-foreground">못 답한 질문이 없습니다.</p>
        <p className="mt-1">
          챗봇이 답하지 못한 질문이 생기면 여기에 빈도순으로 쌓입니다. 필터를 넓혀 보세요.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {/* 표가 넓어져도 페이지 자체가 가로로 밀리면 안 된다 */}
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader className="bg-muted/40">
            <TableRow>
              <TableHead className="min-w-[280px]">질문</TableHead>
              <TableHead
                className="w-[90px] text-right"
                aria-sort={sort === "count" ? "descending" : "none"}
              >
                <button
                  type="button"
                  onClick={() => onSortChange("count")}
                  className="cursor-pointer hover:text-foreground data-[active=true]:font-semibold data-[active=true]:text-foreground"
                  data-active={sort === "count"}
                >
                  횟수
                </button>
              </TableHead>
              <TableHead
                className="w-[110px]"
                aria-sort={sort === "recent" ? "descending" : "none"}
              >
                <button
                  type="button"
                  onClick={() => onSortChange("recent")}
                  className="cursor-pointer hover:text-foreground data-[active=true]:font-semibold data-[active=true]:text-foreground"
                  data-active={sort === "recent"}
                >
                  최근
                </button>
              </TableHead>
              <TableHead className="w-[70px]">봇</TableHead>
              <TableHead className="w-[180px]">관측된 신호</TableHead>
              <TableHead className="w-[210px]">처리 경로</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((group) => (
              <TableRow key={group.question_norm} className="hover:bg-muted/40">
                <TableCell className="py-2.5">
                  <button
                    type="button"
                    onClick={() => onOpenDetail(group)}
                    className="cursor-pointer text-left text-sm leading-snug hover:underline"
                  >
                    {group.question_text}
                  </button>
                  {group.admin_note ? (
                    <p className="mt-1 text-xs text-muted-foreground">{group.admin_note}</p>
                  ) : null}
                </TableCell>
                {/* 정렬해도 폭이 흔들리지 않게 tabular figures */}
                <TableCell className="text-right text-sm font-semibold tabular-nums">
                  {group.count}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {relativeTime(group.last_seen)}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {group.bot_id ? botNames[group.bot_id] ?? `#${group.bot_id}` : "-"}
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {group.reasons.map((reason) => (
                      <Badge
                        key={reason}
                        variant="secondary"
                        className={`text-[11px] ${REASON_STYLE[reason]}`}
                      >
                        {REASON_LABEL[reason]}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  {/* 선택 상자가 곧 현재 상태 표시다 — 옆에 배지를 또 두면 같은 말을 두 번 한다.
                      색은 상자 테두리로만 거들고, 뜻은 아이콘 + 라벨이 진다. */}
                  <div className="flex items-center gap-2">
                    <div className={`rounded-md ${TRIAGE_RING[group.triage]}`}>
                      <TriageSelect
                        value={group.triage}
                        onChange={(next) => onTriageChange(group, next)}
                        disabled={pendingNorm === group.question_norm}
                      />
                    </div>
                    {pendingNorm === group.question_norm ? (
                      <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                    ) : null}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          총 <span className="font-medium text-foreground tabular-nums">{total}</span>개 질문
          중 {(page - 1) * pageSize + (total > 0 ? 1 : 0)}–{Math.min(page * pageSize, total)}
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="mr-1 size-4" />
            이전
          </Button>
          <span className="px-2 text-sm text-muted-foreground tabular-nums">
            {page} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
          >
            다음
            <ChevronRight className="ml-1 size-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}
