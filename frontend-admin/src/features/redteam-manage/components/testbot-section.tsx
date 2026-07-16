"use client"

// 입력관리 상세 — 테스트 봇 재검증 섹션. 봇 답변 + AI(codex) 3평가(① 위험 재발 ② 독립 위험도 ③ AI 평점)를
// 회차별 카드로 나열. 디자인 B안(3평가 카드): 답변 아래 색 테두리 미니카드 3개.
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import { RISK_STYLE } from "../constants"
import type { TestbotEval } from "../types"

// 재발 판정 배지/좌측 테두리 색 (해소=초록 = 좋은 결과)
export const RECUR_STYLE: Record<string, string> = {
  재발: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300",
  부분재발: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  해소: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  판정불가: "bg-muted text-muted-foreground",
}
const RECUR_BORDER: Record<string, string> = {
  재발: "border-l-red-500",
  부분재발: "border-l-amber-500",
  해소: "border-l-emerald-500",
  판정불가: "border-l-border",
}
// 독립 위험도 좌측 테두리 (RISK_STYLE 배지와 톤 일치: 상 red / 중 orange / 하 amber / 없음 muted)
const INDEP_BORDER: Record<string, string> = {
  상: "border-l-red-500",
  중: "border-l-orange-500",
  하: "border-l-amber-500",
  없음: "border-l-border",
}

export function ratingBadgeCls(v: number | null): string {
  if (v == null) return "bg-muted text-muted-foreground"
  if (v >= 4) return "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
  if (v >= 3) return "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
  return "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300"
}
function ratingBorderCls(v: number | null): string {
  if (v == null) return "border-l-border"
  if (v >= 4) return "border-l-emerald-500"
  if (v >= 3) return "border-l-amber-500"
  return "border-l-red-500"
}
export function stars(v: number | null): string {
  if (v == null) return ""
  const full = Math.min(5, Math.max(0, Math.round(v)))
  return "★".repeat(full) + "☆".repeat(5 - full)
}
export function citeLine(ev: TestbotEval): string {
  const direct = ev.citations ?? []
  const bf = ev.bf_citations ?? []
  if (direct.length) return `참고 문서: ${direct.join(" · ")}`
  if (bf.length) return `참고한 자료(근사): ${bf.join(" · ")}`
  return "인용 0 (검색·반영은 정상일 수 있음, grounding 보고 누락)"
}

function EvalCard({ ev, humanRatings }: { ev: TestbotEval; humanRatings: number[] }) {
  const humanAvg = humanRatings.length
    ? humanRatings.reduce((a, b) => a + b, 0) / humanRatings.length
    : null
  const recur = ev.risk_recur ?? "판정불가"
  const indep = ev.independent_risk ?? "없음"
  return (
    <div className="rounded-lg border bg-card p-3">
      {/* 헤더 */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Badge className="bg-blue-600 text-[10px] text-white hover:bg-blue-600">{ev.bot_label}</Badge>
        <span className="rtm-mono text-[11px] text-muted-foreground">
          {ev.run_label}
          {ev.bot_model ? ` · ${ev.bot_model}` : ""}
          {humanAvg != null && ` · 사람 ${humanAvg.toFixed(1)}/5`}
        </span>
      </div>

      {/* 봇 답변 */}
      <div className="whitespace-pre-wrap rounded-md border bg-muted/40 p-2.5 text-xs leading-relaxed">
        {ev.answer}
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">{citeLine(ev)}</p>

      {/* AI 3평가 카드 */}
      <div className="mt-3 flex flex-col gap-2">
        {/* ① 위험 재발 */}
        <div className={cn("rounded-md border border-l-[3px] bg-background p-2.5", RECUR_BORDER[recur])}>
          <div className="mb-1 flex items-center gap-1.5">
            <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RECUR_STYLE[recur])}>
              ① 위험 재발
            </span>
            <b className="text-xs">{recur}</b>
          </div>
          <p className="text-xs leading-relaxed text-foreground/80">{ev.risk_recur_detail || "—"}</p>
        </div>

        {/* ② 독립 위험도 */}
        <div className={cn("rounded-md border border-l-[3px] bg-background p-2.5", INDEP_BORDER[indep] ?? "border-l-border")}>
          <div className="mb-1 flex items-center gap-1.5">
            <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RISK_STYLE[indep] ?? "bg-muted text-muted-foreground")}>
              ② 독립 위험도
            </span>
            <b className="text-xs">{indep}</b>
          </div>
          <p className="text-xs leading-relaxed text-foreground/80">{ev.independent_risk_detail || "—"}</p>
        </div>

        {/* ③ AI 평점 */}
        <div className={cn("rounded-md border border-l-[3px] bg-background p-2.5", ratingBorderCls(ev.ai_rating))}>
          <div className="mb-1 flex items-center gap-1.5">
            <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", ratingBadgeCls(ev.ai_rating))}>
              ③ AI 평점
            </span>
            <b className="rtm-mono text-xs">{ev.ai_rating != null ? `${ev.ai_rating.toFixed(1)}/5` : "-"}</b>
            <span className="text-xs text-amber-500">{stars(ev.ai_rating)}</span>
          </div>
          <p className="text-xs leading-relaxed text-foreground/80">{ev.ai_rating_detail || "—"}</p>
        </div>
      </div>
    </div>
  )
}

/** 테스트 봇 재검증 섹션 — 회차(모델)별로 답변+3평가 카드를 나열. evals 가 있을 때만 렌더. */
export function TestbotSection({
  evals,
  humanRatings,
}: {
  evals: TestbotEval[]
  humanRatings: number[]
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <span className="text-base">🤖</span> 테스트 봇 검증
          <span className="text-xs font-normal text-muted-foreground">{evals.length}건</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {evals.map((ev, i) => (
          <EvalCard key={`${ev.bot_label}-${ev.run_label}-${i}`} ev={ev} humanRatings={humanRatings} />
        ))}
      </CardContent>
    </Card>
  )
}
