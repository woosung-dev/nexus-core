"use client"

// 입력관리 마스터 리스트 — 상태·레벨·분류·담당자 배지 표시, 선택 가능.
import * as React from "react"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { DISPOSITION_STYLE, LEVEL_STYLE, RISK_STYLE, STATUS_SPINE, STATUS_STYLE } from "../constants"
import type { ManageGroupSummary } from "../types"

function WeekDot({ active, label }: { active: boolean; label: string }) {
  return (
    <span
      className={cn(
        "rtm-mono inline-flex h-5 items-center rounded px-1.5 text-[10px] font-semibold",
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

export function ManageGroupList({
  groups,
  total,
  isLoading,
  selectedId,
  onSelect,
}: {
  groups: ManageGroupSummary[]
  total: number
  isLoading: boolean
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2 p-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full" />
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
                style={{ ["--rtm-spine-color" as string]: STATUS_SPINE[g.status] ?? "transparent" }}
                className={cn(
                  "rtm-spine flex w-full flex-col gap-2 py-2.5 pl-4 pr-3 text-left transition-colors",
                  selected ? "bg-accent" : "hover:bg-accent/50"
                )}
              >
                <p className="line-clamp-2 text-sm font-medium leading-snug">{g.question}</p>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={cn(
                      "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                      STATUS_STYLE[g.status] ?? "bg-muted text-muted-foreground"
                    )}
                  >
                    {g.status}
                  </span>
                  {g.level != null && (
                    <span
                      className={cn(
                        "rtm-mono rounded px-1.5 py-0.5 text-[10px] font-semibold",
                        LEVEL_STYLE[g.level]
                      )}
                      title="보완 레벨"
                    >
                      Lv{g.level}
                    </span>
                  )}
                  {g.disposition !== "미정" && (
                    <span
                      className={cn(
                        "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                        DISPOSITION_STYLE[g.disposition]
                      )}
                    >
                      {g.disposition}
                    </span>
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
                </div>
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
                  {g.assignee && (
                    <Badge variant="outline" className="text-[10px]">
                      담당 {g.assignee}
                    </Badge>
                  )}
                  {g.tags.slice(0, 2).map((t) => (
                    <Badge key={t} variant="outline" className="text-[10px] text-muted-foreground">
                      #{t}
                    </Badge>
                  ))}
                  <div className="ml-auto flex items-center gap-1.5">
                    <WeekDot active={g.week2_matched} label="2주" />
                    <WeekDot active={g.week1_matched} label="1주" />
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
