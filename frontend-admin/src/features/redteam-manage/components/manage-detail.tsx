"use client"

// 입력관리 상세 — 질문 헤더 + 관리 편집칸 + 1·2·3주차 응답(읽기) + 리뷰어 참고.
import Link from "next/link"
import { GitCompareArrows } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { BOT_LABELS } from "../../redteam/constants"
import { RISK_STYLE } from "../constants"
import { useManageGroupDetail } from "../hooks"
import type { ResponseItem } from "../types"
import { ManageFields } from "./manage-fields"
import { ReferenceReviews } from "./reference-reviews"

function ResponseCard({ resp }: { resp: ResponseItem }) {
  const botEntries = Object.entries(resp.bot_responses ?? {}).filter(([, v]) => v)
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="text-[10px]">
          {resp.submitter ?? "익명"}
        </Badge>
        {resp.rating != null && (
          <span className="text-xs text-muted-foreground tabular-nums">
            평점 <span className="font-semibold text-foreground">{resp.rating.toFixed(0)}</span>/5
          </span>
        )}
        {resp.risk && resp.risk !== "없음" && (
          <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RISK_STYLE[resp.risk])}>
            위험 {resp.risk}
          </span>
        )}
        {resp.match_score != null && resp.match_status !== "base" && (
          <Badge variant="secondary" className="text-[10px]" title="3주차 질문과의 유사도">
            유사도 {(resp.match_score * 100).toFixed(0)}%
            {resp.match_status === "confirmed" && " · 확정"}
          </Badge>
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
  emptyHint,
}: {
  title: string
  accent: string
  responses: ResponseItem[]
  emptyHint?: string
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className={cn("size-2.5 rounded-full", accent)} />
          {title}
          <span className="text-xs font-normal text-muted-foreground">{responses.length}건</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {responses.length === 0 ? (
          <p className="text-xs text-muted-foreground">{emptyHint ?? "연결된 응답이 없습니다."}</p>
        ) : (
          responses.map((r) => <ResponseCard key={r.id} resp={r} />)
        )}
      </CardContent>
    </Card>
  )
}

export function ManageDetail({ groupId }: { groupId: number | null }) {
  const { data: detail, isLoading } = useManageGroupDetail(groupId)

  if (groupId === null) {
    return (
      <div className="flex h-full min-h-80 items-center justify-center p-8 text-center text-sm text-muted-foreground">
        왼쪽에서 질문을 선택하면 상태·레벨·분류·담당자·모범답변을 입력하고
        <br />
        1·2·3주차 응답과 리뷰어 의견을 확인할 수 있습니다.
      </div>
    )
  }

  if (isLoading || !detail) {
    return (
      <div className="flex flex-col gap-4 p-4">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  const hasPrior = detail.week2_responses.length > 0 || detail.week1_responses.length > 0

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* 헤더 */}
      <div className="flex flex-col gap-3 border-b pb-4">
        <h2 className="text-lg font-bold leading-snug">{detail.question}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="text-[11px]">
            {detail.category ?? "미분류"}
          </Badge>
          {detail.risk && detail.risk !== "없음" && (
            <span className={cn("rounded px-2 py-0.5 text-xs font-semibold", RISK_STYLE[detail.risk])}>
              최고 위험도 {detail.risk}
            </span>
          )}
          {hasPrior && (
            <Button asChild variant="outline" size="sm" className="ml-auto h-7 px-2 text-xs">
              <Link href={`/redteam-manage/compare?selectedId=${detail.id}`}>
                <GitCompareArrows className="size-3" /> 주차 비교
              </Link>
            </Button>
          )}
        </div>
      </div>

      {/* 입력관리 편집 (그룹 전환 시 remount) */}
      <ManageFields key={detail.id} detail={detail} />

      {/* 주차별 응답 (읽기) */}
      <WeekSection title="3주차 (기준)" accent="bg-violet-500" responses={detail.base_responses} />
      <WeekSection
        title="2주차"
        accent="bg-blue-500"
        responses={detail.week2_responses}
        emptyHint="2주차에 매칭된 동일 질문이 없습니다."
      />
      <WeekSection
        title="1주차"
        accent="bg-teal-500"
        responses={detail.week1_responses}
        emptyHint="1주차에 매칭된 동일 질문이 없습니다."
      />

      {/* 리뷰어 참고 */}
      <ReferenceReviews reviews={detail.reviews} />
    </div>
  )
}
