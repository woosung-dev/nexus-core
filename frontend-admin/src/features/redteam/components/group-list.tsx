"use client"

// 기준 질문(3주차) 마스터 리스트 — 선택 가능한 행. 카테고리/위험도/주차매칭/리뷰어 상태 표시.
import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { RISK_STYLE } from "../constants"
import type { GroupSummary } from "../types"

function WeekDot({ active, label }: { active: boolean; label: string }) {
  return (
    <span
      className={cn(
        "inline-flex h-5 items-center rounded px-1.5 text-[10px] font-semibold",
        active
          ? "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300"
          : "bg-muted text-muted-foreground/50"
      )}
      title={active ? `${label} 매칭됨` : `${label} 매칭 없음`}
    >
      {label}
    </span>
  )
}

function ReviewDots({
  group,
  reviewerNames,
}: {
  group: GroupSummary
  reviewerNames: string[]
}) {
  return (
    <div className="flex items-center gap-1" title="리뷰어 작성 상태">
      {reviewerNames.map((name, i) => {
        const filled = group.review_status.some((r) => r.reviewer === name && r.filled)
        return (
          <span
            key={i}
            className={cn(
              "size-2.5 rounded-full",
              filled ? "bg-emerald-500" : "border border-muted-foreground/30"
            )}
          />
        )
      })}
    </div>
  )
}

export function GroupList({
  groups,
  total,
  isLoading,
  selectedId,
  onSelect,
  reviewerNames,
}: {
  groups: GroupSummary[]
  total: number
  isLoading: boolean
  selectedId: number | null
  onSelect: (id: number) => void
  reviewerNames: string[]
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 p-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full" />
        ))}
      </div>
    )
  }

  if (groups.length === 0) {
    return (
      <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
        조건에 맞는 질문이 없습니다.
      </div>
    )
  }

  return (
    <div className="flex flex-col">
      <div className="sticky top-0 z-10 border-b bg-background/95 px-3 py-2 text-xs text-muted-foreground backdrop-blur">
        총 <span className="font-semibold text-foreground">{total}</span>개 질문
      </div>
      <ul className="divide-y">
        {groups.map((g) => {
          const selected = g.id === selectedId
          return (
            <li key={g.id}>
              <button
                onClick={() => onSelect(g.id)}
                className={cn(
                  "flex w-full flex-col gap-2 px-3 py-3 text-left transition-colors",
                  selected
                    ? "bg-accent"
                    : "hover:bg-accent/50"
                )}
              >
                <p className="line-clamp-2 text-sm font-medium leading-snug">{g.question}</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  {g.category ? (
                    <Badge variant="secondary" className="text-[10px]">
                      {g.category}
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-[10px] text-muted-foreground">
                      미분류
                    </Badge>
                  )}
                  {g.risk && g.risk !== "없음" && (
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                        RISK_STYLE[g.risk]
                      )}
                    >
                      위험 {g.risk}
                    </span>
                  )}
                  <div className="ml-auto flex items-center gap-1.5">
                    <WeekDot active={g.week2_matched} label="2주" />
                    <WeekDot active={g.week1_matched} label="1주" />
                    <span className="mx-1 h-3 w-px bg-border" />
                    <ReviewDots group={g} reviewerNames={reviewerNames} />
                  </div>
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
