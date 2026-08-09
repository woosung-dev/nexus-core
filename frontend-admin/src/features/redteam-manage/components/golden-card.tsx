"use client"

// 입력관리 상세 — 정답지(golden) 검수 섹션.
//
// 왜 3버튼인가 —
//   기존 "모범답변" 칸은 자유 텍스트박스 하나였고, 실제로는 46건 전부 리뷰어 메모로 채워졌다
//   (정답지로 쓸 수 없다). `redteam_reviews.correct_answer` 는 아예 0행이다.
//   백지 작문을 요구하면 안 온다는 게 실증됐으므로, 기본 동작을 "쓰기"가 아니라 "판정"으로 둔다.
//   [맞음] 을 누르면 끝이고, [고쳐야 함] 을 눌러야 텍스트 영역이 열린다.
//
// 근거는 접힌 패널로 옆에 붙인다. quote 는 코퍼스 원문 그대로라(생성 시 대조 검증됨)
// 관리자가 원문을 따로 찾지 않고 그 자리에서 대조할 수 있다.
import * as React from "react"
import { Check, ChevronDown, HelpCircle, Loader2, Pencil, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { useUpdateGolden } from "../hooks"
import type { GoldenItem, GoldenStatus } from "../types"

const STATUS_STYLE: Record<GoldenStatus, string> = {
  초안: "bg-muted text-muted-foreground",
  승인: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  수정승인: "bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
  근거없음: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  반려: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
}

const COVERAGE_STYLE: Record<string, string> = {
  충분: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  부분: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  근거없음: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
}

const DOC_STYLE: Record<string, string> = {
  규정집v20: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  공문: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  // 대사전은 전 항목이 "내부 참고용·확정 문구 아님"이라 사용 승인이 미결이다 → 눈에 띄게 둔다
  대사전v4: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
}

function EvidencePanel({ golden }: { golden: GoldenItem }) {
  const [open, setOpen] = React.useState(false)
  if (!golden.evidence.length) return null
  return (
    <div className="rounded-md border bg-muted/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-semibold"
      >
        <ChevronDown className={cn("size-3.5 transition-transform", open && "rotate-180")} />
        근거 원문 {golden.evidence.length}건
        <span className="font-normal text-muted-foreground">
          (문서에서 그대로 옮긴 대목입니다)
        </span>
      </button>
      {open && (
        <div className="flex flex-col gap-2 border-t px-3 py-2">
          {golden.evidence.map((e, i) => (
            <div key={i} className="rounded bg-background p-2">
              <div className="mb-1 flex flex-wrap items-center gap-1.5">
                <span
                  className={cn(
                    "rounded px-1.5 py-0.5 text-[10px] font-semibold",
                    DOC_STYLE[e.doc] ?? "bg-muted text-muted-foreground"
                  )}
                >
                  {e.doc}
                </span>
                <span className="rtm-mono text-[10px] text-muted-foreground">{e.locator}</span>
              </div>
              <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">
                “{e.quote}”
              </p>
            </div>
          ))}
          <p className="text-[10px] leading-relaxed text-muted-foreground">
            규정집은 승인 전 개정초안이고 “초안 조문번호의 대외 인용 금지”가 활용 원칙입니다.
            위 조문 번호는 <b>검수용</b>이며, 챗봇 답변에는 조문 번호를 싣지 않습니다.
          </p>
        </div>
      )}
    </div>
  )
}

export function GoldenCard({ golden, groupId }: { golden: GoldenItem; groupId: number }) {
  const update = useUpdateGolden(groupId)
  const [editing, setEditing] = React.useState(false)
  const [draft, setDraft] = React.useState(golden.golden)
  const [note, setNote] = React.useState(golden.admin_note)

  // 그룹 전환 시 부모가 key로 remount 하므로 동기화 이펙트는 두지 않는다.
  const decided = golden.status !== "초안"

  const decide = (status: GoldenStatus, extra: Record<string, unknown> = {}) =>
    update.mutate({ status, ...(note.trim() ? { admin_note: note.trim() } : {}), ...extra })

  return (
    <Card className="border-l-4 border-l-violet-500">
      <CardHeader className="pb-3">
        <CardTitle className="flex flex-wrap items-center gap-2 text-sm">
          정답지 검수
          <span
            className={cn("rounded px-2 py-0.5 text-[11px] font-semibold", STATUS_STYLE[golden.status])}
          >
            {golden.status}
          </span>
          {golden.coverage && (
            <span
              className={cn(
                "rounded px-2 py-0.5 text-[11px] font-semibold",
                COVERAGE_STYLE[golden.coverage] ?? "bg-muted"
              )}
              title="문서만으로 답이 확정되는가"
            >
              문서근거 {golden.coverage}
            </span>
          )}
          {golden.source_docs.map((d) => (
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
        </CardTitle>
      </CardHeader>

      <CardContent className="flex flex-col gap-3">
        {/* 정답지 본문 */}
        {editing ? (
          <div className="flex flex-col gap-2">
            <Label className="text-[11px] text-muted-foreground">
              고칠 내용을 반영해 주세요 (초안은 따로 보존됩니다)
            </Label>
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="min-h-32 text-sm leading-relaxed"
            />
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                className="h-8"
                disabled={!draft.trim() || update.isPending}
                onClick={() => {
                  decide("수정승인", { golden: draft })
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
                  setDraft(golden.golden)
                  setEditing(false)
                }}
              >
                취소
              </Button>
            </div>
          </div>
        ) : (
          <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm leading-relaxed">
            {golden.golden || "(정답지 본문이 비어 있습니다)"}
          </p>
        )}

        <EvidencePanel golden={golden} />

        {golden.open_question && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
              가정행복국 확인이 필요한 것
            </p>
            <p className="text-xs leading-relaxed text-foreground/90">{golden.open_question}</p>
          </div>
        )}

        {/* 판정 3버튼 */}
        {!editing && (
          <div className="flex flex-col gap-2">
            <Label className="text-[11px] text-muted-foreground">판정</Label>
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
                variant="outline"
                className="h-8 border-amber-400 text-amber-700 hover:bg-amber-50 dark:text-amber-300"
                disabled={update.isPending}
                onClick={() => decide("근거없음")}
              >
                <HelpCircle className="size-3.5" /> 근거 없음 — 결정 필요
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
          </div>
        )}

        {/* 메모 */}
        <div className="flex flex-col gap-1.5">
          <Label className="text-[11px] text-muted-foreground">검수 메모 (선택)</Label>
          <Textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note !== golden.admin_note && update.mutate({ admin_note: note })}
            placeholder="판정 이유나 남길 말"
            className="min-h-16 text-xs"
          />
        </div>

        {decided && (
          <p className="text-[11px] text-muted-foreground">
            {golden.approver ? `${golden.approver} · ` : ""}
            {golden.approved_at ? new Date(golden.approved_at).toLocaleString("ko-KR") : ""}
            {golden.draft_golden && " · 초안 원문 보존됨"}
          </p>
        )}

        <p className="text-[10px] text-muted-foreground">
          기준 문서 {golden.corpus_version || "(미기록)"} · 초안 생성 {golden.draft_engine}
        </p>
      </CardContent>
    </Card>
  )
}
