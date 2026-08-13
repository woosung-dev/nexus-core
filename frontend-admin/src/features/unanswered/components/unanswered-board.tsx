"use client"

/**
 * 못 답한 질문 — 화면 전체.
 *
 * 이 화면이 하는 일은 하나다: **무엇부터 채울지 정해 준다.** 그래서 기본 정렬이 빈도순이고,
 * 관리자는 위에서부터 「어느 트랙의 일인가」만 찍으면 된다.
 *
 * 필터는 선택이 아니다 — 신호가 다섯 종류라 필터가 없으면 목록이 금방 못 읽게 된다.
 */
import { useMemo, useState } from "react"
import { useSearchParams } from "next/navigation"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useBots } from "@/features/bots/hooks"
import { OpsFactCreateDialog } from "@/features/ops-facts/components/ops-fact-create-dialog"
import { useCreateOpsFact } from "@/features/ops-facts/hooks"

import {
  OPS_FACT_TRIAGE,
  REASON_LABEL,
  RETENTION_DAYS,
  TRIAGE_LABEL,
  TRIAGE_ORDER,
} from "../constants"
import { useSetTriage, useUnanswered } from "../hooks"
import type {
  UnansweredGroup,
  UnansweredReason,
  UnansweredTriage,
} from "../types"
import { UnansweredDetailSheet } from "./unanswered-detail-sheet"
import { UnansweredTable } from "./unanswered-table"

const PAGE_SIZE = 25
const ALL = "__all__"

const REASON_OPTIONS: UnansweredReason[] = [
  "self_refusal",
  "empty_answer",
  "lexical_empty",
  "corpus_unavailable",
]

export function UnansweredBoard() {
  // 봇 상세에서 「이 봇의 못 답한 질문」으로 넘어오면 필터가 실려 온다.
  const initialBotId = useSearchParams().get("bot_id")

  const [page, setPage] = useState(1)
  const [sort, setSort] = useState<"count" | "recent">("count")
  const [botId, setBotId] = useState<string>(initialBotId ?? ALL)
  const [reason, setReason] = useState<string>(ALL)
  const [triage, setTriage] = useState<string>(ALL)
  const [detail, setDetail] = useState<UnansweredGroup | null>(null)
  const [opsFactFor, setOpsFactFor] = useState<UnansweredGroup | null>(null)

  const params = useMemo(
    () => ({
      ...(botId !== ALL ? { bot_id: Number(botId) } : {}),
      ...(reason !== ALL ? { reason: reason as UnansweredReason } : {}),
      ...(triage !== ALL ? { triage: triage as UnansweredTriage } : {}),
      sort,
      limit: PAGE_SIZE,
      offset: (page - 1) * PAGE_SIZE,
    }),
    [botId, reason, triage, sort, page]
  )

  const { data, isLoading, isError, error } = useUnanswered(params)
  const { data: bots } = useBots()
  const setTriageMutation = useSetTriage()
  const createOpsFact = useCreateOpsFact()

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const botNames = useMemo(
    () => Object.fromEntries((bots?.bots ?? []).map((b) => [b.id, b.name])),
    [bots]
  )

  function resetPageThen(setter: (value: string) => void) {
    return (value: string) => {
      setPage(1)
      setter(value)
    }
  }

  function handleTriageChange(group: UnansweredGroup, next: UnansweredTriage) {
    setTriageMutation.mutate(
      { question_norm: group.question_norm, triage: next },
      {
        // 「문서가 틀림·낡음」에서만 운영 사실로 넘어간다. 나머지 셋은 다른 트랙의 일이다.
        onSuccess: () => {
          if (next === OPS_FACT_TRIAGE && !group.ops_fact_id) {
            setOpsFactFor({ ...group, triage: next })
          }
        },
      }
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 필터 — 스킬이 지목한 안티패턴이 "No filtering" 이다 */}
      <div className="flex flex-wrap items-center gap-2">
        <Select value={botId} onValueChange={resetPageThen(setBotId)}>
          <SelectTrigger className="h-9 w-[170px] text-sm" aria-label="봇">
            <SelectValue placeholder="전체 봇" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 봇</SelectItem>
            {(bots?.bots ?? []).map((bot) => (
              <SelectItem key={bot.id} value={String(bot.id)}>
                {bot.id}. {bot.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={reason} onValueChange={resetPageThen(setReason)}>
          <SelectTrigger className="h-9 w-[170px] text-sm" aria-label="관측된 신호">
            <SelectValue placeholder="전체 신호" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 신호</SelectItem>
            {REASON_OPTIONS.map((r) => (
              <SelectItem key={r} value={r}>
                {REASON_LABEL[r]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={triage} onValueChange={resetPageThen(setTriage)}>
          <SelectTrigger className="h-9 w-[190px] text-sm" aria-label="처리 경로">
            <SelectValue placeholder="전체 처리 경로" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 처리 경로</SelectItem>
            {TRIAGE_ORDER.map((t) => (
              <SelectItem key={t} value={t}>
                {TRIAGE_LABEL[t]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {botId !== ALL || reason !== ALL || triage !== ALL ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setPage(1)
              setBotId(ALL)
              setReason(ALL)
              setTriage(ALL)
            }}
          >
            필터 지우기
          </Button>
        ) : null}

        <Badge variant="outline" className="ml-auto text-[11px] font-normal">
          기록은 {RETENTION_DAYS}일 후 삭제됩니다
        </Badge>
      </div>

      <UnansweredTable
        items={items}
        isLoading={isLoading}
        isError={isError}
        error={error as Error | null}
        total={total}
        page={page}
        pageSize={PAGE_SIZE}
        sort={sort}
        botNames={botNames}
        pendingNorm={
          setTriageMutation.isPending
            ? setTriageMutation.variables?.question_norm ?? null
            : null
        }
        onPageChange={setPage}
        onSortChange={(next) => {
          setPage(1)
          setSort(next)
        }}
        onTriageChange={handleTriageChange}
        onOpenDetail={setDetail}
      />

      <UnansweredDetailSheet group={detail} onClose={() => setDetail(null)} />

      <OpsFactCreateDialog
        open={opsFactFor !== null}
        onOpenChange={(open) => !open && setOpsFactFor(null)}
        sourceQuestion={opsFactFor?.question_text ?? ""}
        botId={opsFactFor?.bot_id ?? null}
        isPending={createOpsFact.isPending}
        onSubmit={(request) => {
          const group = opsFactFor
          createOpsFact.mutate(request, {
            onSuccess: (fact) => {
              // 루프가 닫힌 자리를 그룹에 남긴다.
              if (group) {
                setTriageMutation.mutate({
                  question_norm: group.question_norm,
                  triage: OPS_FACT_TRIAGE,
                  ops_fact_id: fact.id,
                })
              }
              setOpsFactFor(null)
            },
          })
        }}
      />
    </div>
  )
}
