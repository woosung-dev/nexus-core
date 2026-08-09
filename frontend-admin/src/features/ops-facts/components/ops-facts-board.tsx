"use client"

// 운영 사실 검수 보드 — 종류별로 묶어 보여준다.
//
// 상단 스트립이 "지금 챗봇에 몇 건이 반영 중인가"를 먼저 보여준다.
// 등록만으로는 아무것도 안 바뀌므로(승인분만 런타임이 읽는다) 그 숫자가 화면의 핵심이다.
import { Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { KIND_EFFECT, KIND_LABEL, KIND_ORDER, KIND_STYLE, RUNTIME_STATUS } from "../constants"
import { useOpsFacts } from "../hooks"
import type { OpsFactResponse } from "../types"
import { OpsFactCard } from "./ops-fact-card"

function ProgressStrip({ facts }: { facts: OpsFactResponse[] }) {
  const live = facts.filter((f) => RUNTIME_STATUS.includes(f.status) && f.is_active).length
  const draft = facts.filter((f) => f.status === "초안").length
  const rejected = facts.filter((f) => f.status === "반려").length

  return (
    <div className="flex flex-wrap items-center gap-6 rounded-lg border bg-card p-4">
      <div>
        <p className="text-2xl font-bold tabular-nums text-emerald-600 dark:text-emerald-400">
          {live}
        </p>
        <p className="text-xs text-muted-foreground">챗봇에 반영 중</p>
      </div>
      <div>
        <p className="text-2xl font-bold tabular-nums">{draft}</p>
        <p className="text-xs text-muted-foreground">검수 대기</p>
      </div>
      <div>
        <p className="text-2xl font-bold tabular-nums text-muted-foreground">{rejected}</p>
        <p className="text-xs text-muted-foreground">반려</p>
      </div>
      {live === 0 && (
        <p className="text-xs leading-relaxed text-amber-700 dark:text-amber-400">
          승인된 항목이 없어 챗봇 동작은 지금과 완전히 같습니다.
          <br />
          검수 대기 항목을 승인하시면 그때부터 답변에 반영됩니다.
        </p>
      )}
    </div>
  )
}

export function OpsFactsBoard() {
  const { data, isLoading, isError, error } = useOpsFacts()

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
        목록을 불러오지 못했습니다: {(error as Error)?.message}
      </p>
    )
  }

  const facts = data?.items ?? []
  if (facts.length === 0) {
    return (
      <p className="rounded-md border p-8 text-center text-sm text-muted-foreground">
        등록된 운영 사실이 없습니다.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <ProgressStrip facts={facts} />
      {KIND_ORDER.map((kind) => {
        const rows = facts.filter((f) => f.kind === kind)
        if (rows.length === 0) return null
        return (
          <section key={kind} className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className={cn("rounded px-2 py-0.5 text-xs font-semibold", KIND_STYLE[kind])}>
                {KIND_LABEL[kind]}
              </span>
              <span className="text-xs text-muted-foreground">{KIND_EFFECT[kind]}</span>
              <span className="text-xs tabular-nums text-muted-foreground">{rows.length}건</span>
            </div>
            {rows.map((f) => (
              <OpsFactCard key={f.id} fact={f} />
            ))}
          </section>
        )
      })}
    </div>
  )
}
