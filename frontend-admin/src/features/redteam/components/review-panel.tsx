"use client"

// 리뷰 패널 — 리뷰어별(최대 3명) 옳은 답변 + 주차별 반영여부. 현재 리뷰어 탭만 편집 가능.
import * as React from "react"
import { Check, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { cn } from "@/lib/utils"
import { REFLECT_OPTIONS, REFLECT_STYLE } from "../constants"
import { useUpsertReview } from "../hooks"
import type { ReflectValue, ReviewItem } from "../types"

const WEEKS: { key: "week1_reflect" | "week2_reflect" | "week3_reflect"; label: string }[] = [
  { key: "week3_reflect", label: "3주차 반영" },
  { key: "week2_reflect", label: "2주차 반영" },
  { key: "week1_reflect", label: "1주차 반영" },
]

const EMPTY: Omit<ReviewItem, "reviewer" | "updated_at"> = {
  correct_answer: "",
  week1_reflect: "pending",
  week2_reflect: "pending",
  week3_reflect: "pending",
}

function ReflectSegment({
  value,
  onChange,
  disabled,
}: {
  value: ReflectValue
  onChange?: (v: ReflectValue) => void
  disabled?: boolean
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border">
      {REFLECT_OPTIONS.map((opt) => {
        const active = value === opt.value
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange?.(opt.value)}
            className={cn(
              "px-3 py-1 text-xs font-medium transition-colors disabled:cursor-default",
              active ? REFLECT_STYLE[opt.value] : "bg-transparent text-muted-foreground",
              !active && !disabled && "hover:bg-accent"
            )}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

function ReviewForm({
  groupId,
  existing,
  reviewerName,
}: {
  groupId: number
  existing: ReviewItem | undefined
  reviewerName: string
}) {
  const upsert = useUpsertReview(groupId)
  const [form, setForm] = React.useState(() => ({ ...EMPTY, ...existing }))

  // 그룹/리뷰어 전환 시 폼 초기화
  React.useEffect(() => {
    setForm({ ...EMPTY, ...existing })
  }, [groupId, reviewerName, existing])

  const dirty =
    form.correct_answer !== (existing?.correct_answer ?? "") ||
    form.week1_reflect !== (existing?.week1_reflect ?? "pending") ||
    form.week2_reflect !== (existing?.week2_reflect ?? "pending") ||
    form.week3_reflect !== (existing?.week3_reflect ?? "pending")

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-xs font-semibold text-muted-foreground">옳은 답변</label>
        <Textarea
          value={form.correct_answer}
          onChange={(e) => setForm((f) => ({ ...f, correct_answer: e.target.value }))}
          placeholder="이 질문에 대한 옳은 답변을 작성하세요."
          className="min-h-32 text-sm"
        />
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-xs font-semibold text-muted-foreground">
          주차별 피드백 반영 여부
        </label>
        {WEEKS.map((w) => (
          <div key={w.key} className="flex items-center justify-between gap-2">
            <span className="text-sm">{w.label}</span>
            <ReflectSegment
              value={form[w.key]}
              onChange={(v) => setForm((f) => ({ ...f, [w.key]: v }))}
            />
          </div>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Button
          onClick={() =>
            upsert.mutate({
              group_id: groupId,
              reviewer: reviewerName,
              correct_answer: form.correct_answer,
              week1_reflect: form.week1_reflect,
              week2_reflect: form.week2_reflect,
              week3_reflect: form.week3_reflect,
            })
          }
          disabled={!dirty || upsert.isPending}
        >
          {upsert.isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Check className="size-4" />
          )}
          저장
        </Button>
        {upsert.isSuccess && !dirty && (
          <span className="text-xs text-emerald-600">저장됨</span>
        )}
        {existing?.updated_at && (
          <span className="ml-auto text-xs text-muted-foreground">
            최종 수정 {new Date(existing.updated_at).toLocaleString("ko-KR")}
          </span>
        )}
      </div>
    </div>
  )
}

function ReviewReadOnly({ review }: { review: ReviewItem | undefined }) {
  if (!review || (!review.correct_answer && review.week1_reflect === "pending" && review.week2_reflect === "pending" && review.week3_reflect === "pending")) {
    return <p className="py-6 text-center text-sm text-muted-foreground">아직 작성하지 않았습니다.</p>
  }
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="mb-1 text-xs font-semibold text-muted-foreground">옳은 답변</p>
        <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm">
          {review.correct_answer || "—"}
        </p>
      </div>
      <div className="flex flex-col gap-2">
        {WEEKS.map((w) => (
          <div key={w.key} className="flex items-center justify-between">
            <span className="text-sm">{w.label}</span>
            <ReflectSegment value={review[w.key]} disabled />
          </div>
        ))}
      </div>
    </div>
  )
}

export function ReviewPanel({
  groupId,
  reviews,
  reviewerName,
  reviewerNames,
  readOnly,
}: {
  groupId: number
  reviews: ReviewItem[]
  reviewerName?: string
  reviewerNames?: string[]
  readOnly?: boolean
}) {
  const byName = React.useMemo(() => {
    const m: Record<string, ReviewItem> = {}
    for (const r of reviews) m[r.reviewer] = r
    return m
  }, [reviews])

  // 읽기전용(보고 드릴다운)에서는 실제 작성된 리뷰어만 탭으로 노출
  const names = readOnly
    ? Array.from(new Set(reviews.map((r) => r.reviewer)))
    : reviewerNames ?? []
  const activeName = reviewerName ?? names[0] ?? ""

  if (readOnly && names.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-4">
        <h3 className="mb-1 text-sm font-bold">리뷰어 피드백</h3>
        <p className="py-4 text-center text-sm text-muted-foreground">
          아직 작성된 리뷰가 없습니다.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card p-4">
      <h3 className="mb-3 text-sm font-bold">리뷰어 피드백</h3>
      <Tabs defaultValue={activeName} key={activeName}>
        <TabsList className="mb-3">
          {names.map((name) => {
            const filled =
              byName[name] &&
              (byName[name].correct_answer ||
                byName[name].week1_reflect !== "pending" ||
                byName[name].week2_reflect !== "pending" ||
                byName[name].week3_reflect !== "pending")
            return (
              <TabsTrigger key={name} value={name} className="gap-1.5">
                {!readOnly && name === activeName && (
                  <span className="text-[10px] text-primary">●</span>
                )}
                {name}
                {filled && <span className="size-1.5 rounded-full bg-emerald-500" />}
              </TabsTrigger>
            )
          })}
        </TabsList>
        {names.map((name) => (
          <TabsContent key={name} value={name}>
            {!readOnly && name === activeName ? (
              <ReviewForm groupId={groupId} existing={byName[name]} reviewerName={name} />
            ) : (
              <ReviewReadOnly review={byName[name]} />
            )}
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
