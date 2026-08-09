"use client"

// 운영 사실 1건 — 검수 카드.
//
// 정답지 검수(golden-card.tsx)와 같은 3버튼 구조다. 관리자에게 백지 작문을 요구하면
// 안 온다는 것이 실증됐기 때문에(redteam_reviews.correct_answer 0행), 기본 동작을
// "쓰기"가 아니라 "판정"으로 둔다. [맞음] 을 누르면 끝이고, [고쳐야 함] 을 눌러야 입력이 열린다.
//
// 승인 전에는 챗봇이 이 사실을 전혀 모른다는 것을 화면에 명시한다 — 그래야
// "등록했는데 왜 안 바뀌지"가 생기지 않는다.
import * as React from "react"
import { AlertTriangle, Check, Loader2, Pencil, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { DOC_STYLE, KIND_EFFECT, KIND_LABEL, KIND_STYLE, RUNTIME_STATUS, STATUS_STYLE } from "../constants"
import { useUpdateOpsFact } from "../hooks"
import type { OpsFactResponse, OpsFactStatus } from "../types"

export function OpsFactCard({ fact }: { fact: OpsFactResponse }) {
  const update = useUpdateOpsFact()
  const [editing, setEditing] = React.useState(false)
  const [statement, setStatement] = React.useState(fact.statement)
  const [superseded, setSuperseded] = React.useState(fact.superseded)
  const [note, setNote] = React.useState(fact.admin_note)

  const live = RUNTIME_STATUS.includes(fact.status) && fact.is_active
  const decided = fact.status !== "초안"

  const decide = (status: OpsFactStatus, extra: Record<string, unknown> = {}) =>
    update.mutate({
      id: fact.id,
      request: { status, ...(note.trim() ? { admin_note: note.trim() } : {}), ...extra },
    })

  return (
    <Card className={cn("border-l-4", live ? "border-l-emerald-500" : "border-l-muted")}>
      <CardContent className="flex flex-col gap-3 pt-5">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn("rounded px-2 py-0.5 text-[11px] font-semibold", KIND_STYLE[fact.kind])}>
            {KIND_LABEL[fact.kind]}
          </span>
          <span className={cn("rounded px-2 py-0.5 text-[11px] font-semibold", STATUS_STYLE[fact.status])}>
            {fact.status}
          </span>
          <span className="text-sm font-semibold">{fact.title}</span>
          {fact.bot_id === null ? (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">전역</span>
          ) : (
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
              봇 {fact.bot_id}
            </span>
          )}
          {fact.source_docs.map((d) => (
            <span
              key={d}
              className={cn(
                "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                DOC_STYLE[d] ?? "bg-muted text-muted-foreground"
              )}
            >
              {d}
            </span>
          ))}
          {update.isPending && (
            <span className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">
              <Loader2 className="size-3 animate-spin" /> 저장 중
            </span>
          )}
        </div>

        {/* 쓰면 안 되는 것 → 대신 쓸 것 */}
        {editing ? (
          <div className="flex flex-col gap-2">
            {fact.kind !== "contact" && fact.kind !== "crisis" && (
              <>
                <Label className="text-[11px] text-muted-foreground">쓰면 안 되는 것</Label>
                <Input
                  value={superseded}
                  onChange={(e) => setSuperseded(e.target.value)}
                  className="h-8 text-sm"
                />
              </>
            )}
            <Label className="text-[11px] text-muted-foreground">
              {fact.kind === "term" ? "대신 쓸 표기 (이 문자열로 그대로 바뀝니다)" : "현행 사실 / 안내 문안"}
            </Label>
            <Textarea
              value={statement}
              onChange={(e) => setStatement(e.target.value)}
              className="min-h-20 text-sm leading-relaxed"
            />
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                className="h-8"
                disabled={!statement.trim() || update.isPending}
                onClick={() => {
                  decide("수정승인", { statement, superseded })
                  setEditing(false)
                }}
              >
                수정본으로 확정
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-8"
                onClick={() => {
                  setStatement(fact.statement)
                  setSuperseded(fact.superseded)
                  setEditing(false)
                }}
              >
                취소
              </Button>
            </div>
          </div>
        ) : (
          <div className="rounded-md bg-muted/40 p-3 text-sm leading-relaxed">
            {fact.superseded && (
              <p className="mb-1">
                <span className="text-muted-foreground">쓰면 안 되는 것 · </span>
                <span className="font-semibold text-red-700 line-through dark:text-red-400">
                  {fact.superseded}
                </span>
              </p>
            )}
            <p className="whitespace-pre-wrap">
              <span className="text-muted-foreground">
                {fact.kind === "term" ? "대신 쓸 표기 · " : "현행 · "}
              </span>
              {fact.statement || "(내용이 비어 있습니다)"}
            </p>
          </div>
        )}

        {fact.triggers.length > 0 && (
          <p className="text-[11px] text-muted-foreground">
            트리거 — 질문에 다음이 있을 때만 실립니다: {fact.triggers.join(" · ")}
          </p>
        )}

        {/* 승인 전에는 챗봇이 이 사실을 모른다 */}
        {!live && (
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-amber-600 dark:text-amber-400" />
            <p className="text-[11px] leading-relaxed text-foreground/90">
              아직 <b>챗봇에 반영되지 않습니다.</b> 승인하셔야 답변에 쓰입니다.
            </p>
          </div>
        )}
        {live && (
          <p className="text-[11px] text-emerald-700 dark:text-emerald-400">
            챗봇에 반영 중 — {KIND_EFFECT[fact.kind]}
          </p>
        )}

        {/* 판정 3버튼 */}
        {!editing && (
          <div className="flex flex-wrap gap-2">
            <Button
              size="sm"
              className="h-8 bg-emerald-600 hover:bg-emerald-700"
              disabled={update.isPending}
              onClick={() => decide("승인")}
            >
              <Check className="size-3.5" /> 맞음
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-8"
              disabled={update.isPending}
              onClick={() => setEditing(true)}
            >
              <Pencil className="size-3.5" /> 고쳐야 함
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-8 text-muted-foreground"
              disabled={update.isPending}
              onClick={() => decide("반려")}
            >
              <X className="size-3.5" /> 반려
            </Button>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] text-muted-foreground">검수 메모 (선택)</Label>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() =>
              note !== fact.admin_note &&
              update.mutate({ id: fact.id, request: { admin_note: note } })
            }
            placeholder="판정 이유나 남길 말"
            className="min-h-16 text-xs"
          />
        </div>

        {decided && (
          <p className="text-[11px] text-muted-foreground">
            {fact.approver ? `${fact.approver} · ` : ""}
            {fact.approved_at ? new Date(fact.approved_at).toLocaleString("ko-KR") : ""}
            {fact.draft_statement && " · 초안 원문 보존됨"}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
