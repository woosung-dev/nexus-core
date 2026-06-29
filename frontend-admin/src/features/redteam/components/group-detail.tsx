"use client"

// 기준 질문 상세 — 카테고리 편집 + 3/2/1주차 응답 + 동일질문 수동매칭 + 리뷰 패널
import * as React from "react"
import { ChevronDown, Link2, Loader2, Unlink } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { BOT_LABELS, CATEGORIES, RISK_STYLE } from "../constants"
import {
  useLinkCandidate,
  useRedteamCandidates,
  useRedteamGroupDetail,
  useUpdateCategory,
} from "../hooks"
import type { GroupDetail, ResponseItem } from "../types"
import { ReviewPanel } from "./review-panel"

const NO_CATEGORY = "__none__"

function RatingStars({ rating }: { rating: number | null }) {
  if (rating == null) return null
  return (
    <span className="text-xs text-muted-foreground tabular-nums" title="적절성/유용성 평가">
      평점 <span className="font-semibold text-foreground">{rating.toFixed(0)}</span>/5
    </span>
  )
}

function ResponseCard({
  resp,
  onUnlink,
  unlinking,
}: {
  resp: ResponseItem
  onUnlink?: () => void
  unlinking?: boolean
}) {
  const botEntries = Object.entries(resp.bot_responses ?? {}).filter(([, v]) => v)
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {resp.submitter ?? "익명"}
        </Badge>
        <RatingStars rating={resp.rating} />
        {resp.risk && resp.risk !== "없음" && (
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-semibold",
              RISK_STYLE[resp.risk]
            )}
          >
            위험 {resp.risk}
          </span>
        )}
        {resp.match_score != null && resp.match_status !== "base" && (
          <Badge
            variant="secondary"
            className="text-[10px]"
            title="3주차 질문과의 유사도"
          >
            유사도 {(resp.match_score * 100).toFixed(0)}%
            {resp.match_status === "confirmed" && " · 확정"}
          </Badge>
        )}
        {onUnlink && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto h-6 px-2 text-xs text-muted-foreground"
            onClick={onUnlink}
            disabled={unlinking}
          >
            {unlinking ? <Loader2 className="size-3 animate-spin" /> : <Unlink className="size-3" />}
            매칭 해제
          </Button>
        )}
      </div>

      {botEntries.length > 0 && (
        <div className="flex flex-col gap-2">
          {botEntries.map(([key, val]) => (
            <div key={key} className="rounded-md bg-muted/40 p-2">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {BOT_LABELS[key] ?? key}
              </p>
              <p className="whitespace-pre-wrap text-xs leading-relaxed">{val}</p>
            </div>
          ))}
        </div>
      )}

      {resp.feedback_text && (
        <div className="mt-2 border-t pt-2">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            피드백
          </p>
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
            {resp.feedback_text}
          </p>
        </div>
      )}
    </div>
  )
}

function WeekSection({
  title,
  accent,
  responses,
  groupId,
  emptyHint,
  readOnly,
}: {
  title: string
  accent: string
  responses: ResponseItem[]
  groupId: number
  emptyHint?: string
  readOnly?: boolean
}) {
  const link = useLinkCandidate(groupId)
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className={cn("size-2.5 rounded-full", accent)} />
          {title}
          <span className="text-xs font-normal text-muted-foreground">
            {responses.length}건
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {responses.length === 0 ? (
          <p className="text-xs text-muted-foreground">{emptyHint ?? "연결된 응답이 없습니다."}</p>
        ) : (
          responses.map((r) => (
            <ResponseCard
              key={r.id}
              resp={r}
              onUnlink={
                readOnly || r.match_status === "base"
                  ? undefined
                  : () => link.mutate({ responseId: r.id, action: "reject" })
              }
              unlinking={link.isPending && link.variables?.responseId === r.id}
            />
          ))
        )}
      </CardContent>
    </Card>
  )
}

function ManualMatchSection({ groupId }: { groupId: number }) {
  const [open, setOpen] = React.useState(false)
  const { data: candidates, isLoading } = useRedteamCandidates(groupId, open)
  const link = useLinkCandidate(groupId)

  return (
    <Card>
      <CardHeader className="pb-2">
        <button
          className="flex w-full items-center gap-2 text-sm font-semibold"
          onClick={() => setOpen((o) => !o)}
        >
          <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          동일 질문 수동 매칭
          <span className="text-xs font-normal text-muted-foreground">
            (1·2주차 미연결 응답 후보)
          </span>
        </button>
      </CardHeader>
      {open && (
        <CardContent className="flex flex-col gap-2">
          {isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : candidates && candidates.length > 0 ? (
            candidates.map((c) => (
              <div
                key={c.id}
                className="flex items-center gap-2 rounded-md border p-2 text-xs"
              >
                <Badge variant="outline" className="shrink-0 text-[10px]">
                  {c.week}주차
                </Badge>
                <span className="shrink-0 tabular-nums text-muted-foreground">
                  {((c.match_score ?? 0) * 100).toFixed(0)}%
                </span>
                <span className="line-clamp-1 flex-1" title={c.question}>
                  {c.question}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 shrink-0 px-2"
                  onClick={() => link.mutate({ responseId: c.id, action: "confirm" })}
                  disabled={link.isPending && link.variables?.responseId === c.id}
                >
                  {link.isPending && link.variables?.responseId === c.id ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    <Link2 className="size-3" />
                  )}
                  연결
                </Button>
              </div>
            ))
          ) : (
            <p className="text-xs text-muted-foreground">유사한 후보가 없습니다.</p>
          )}
        </CardContent>
      )}
    </Card>
  )
}

function CategoryEditor({ detail }: { detail: GroupDetail }) {
  const update = useUpdateCategory(detail.id)
  return (
    <div className="flex items-center gap-2">
      <Select
        value={detail.category ?? NO_CATEGORY}
        onValueChange={(v) => update.mutate(v === NO_CATEGORY ? null : v)}
      >
        <SelectTrigger className="h-8 w-44 text-xs">
          <SelectValue placeholder="카테고리" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={NO_CATEGORY}>미분류</SelectItem>
          {CATEGORIES.map((c) => (
            <SelectItem key={c} value={c}>
              {c}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {detail.category_source === "manual" ? (
        <Badge variant="outline" className="text-[10px] text-muted-foreground">
          수동
        </Badge>
      ) : (
        <Badge variant="secondary" className="text-[10px]">
          자동
        </Badge>
      )}
      {update.isPending && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
    </div>
  )
}

export function GroupDetailPanel({
  groupId,
  reviewerName,
  reviewerNames,
  readOnly,
}: {
  groupId: number | null
  reviewerName?: string
  reviewerNames?: string[]
  readOnly?: boolean
}) {
  const { data: detail, isLoading } = useRedteamGroupDetail(groupId)

  if (groupId === null) {
    return (
      <div className="flex h-full min-h-80 items-center justify-center p-8 text-center text-sm text-muted-foreground">
        왼쪽에서 질문을 선택하면 1·2·3주차 응답과 리뷰 입력 칸이 표시됩니다.
      </div>
    )
  }

  if (isLoading || !detail) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* 헤더 */}
      <div className="flex flex-col gap-3 border-b pb-4">
        <h2 className="text-lg font-bold leading-snug">{detail.question}</h2>
        <div className="flex flex-wrap items-center gap-3">
          {readOnly ? (
            <Badge variant="secondary" className="text-[11px]">
              {detail.category ?? "미분류"}
            </Badge>
          ) : (
            <CategoryEditor detail={detail} />
          )}
          {detail.risk && detail.risk !== "없음" && (
            <span
              className={cn(
                "rounded px-2 py-0.5 text-xs font-semibold",
                RISK_STYLE[detail.risk]
              )}
            >
              최고 위험도 {detail.risk}
            </span>
          )}
        </div>
      </div>

      {/* 주차별 응답 */}
      <WeekSection
        title="3주차 (기준)"
        accent="bg-violet-500"
        responses={detail.base_responses}
        groupId={detail.id}
        readOnly={readOnly}
      />
      <WeekSection
        title="2주차"
        accent="bg-blue-500"
        responses={detail.week2_responses}
        groupId={detail.id}
        emptyHint="2주차에 매칭된 동일 질문이 없습니다."
        readOnly={readOnly}
      />
      <WeekSection
        title="1주차"
        accent="bg-teal-500"
        responses={detail.week1_responses}
        groupId={detail.id}
        emptyHint="1주차에 매칭된 동일 질문이 없습니다."
        readOnly={readOnly}
      />

      {!readOnly && <ManualMatchSection groupId={detail.id} />}

      {/* 리뷰 패널 */}
      <ReviewPanel
        groupId={detail.id}
        reviews={detail.reviews}
        reviewerName={reviewerName}
        reviewerNames={reviewerNames}
        readOnly={readOnly}
      />
    </div>
  )
}
