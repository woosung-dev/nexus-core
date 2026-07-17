"use client"

// 비교 컬럼 — 한 기준질문의 3·2·1주차 응답을 나란히 (봇 C/D 정규화, 동일질문 표시).
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { COMPARE_BOT_LABEL, meaningfulEtc, RISK_STYLE } from "../constants"
import { useGroupCompare } from "../hooks"
import type { CompareWeekResponse, TestbotEval } from "../types"
import { citeLine, ratingBadgeCls, RECUR_STYLE } from "./testbot-section"

const WEEK_META: Record<number, { label: string; dot: string }> = {
  3: { label: "3주차 (기준)", dot: "bg-violet-500" },
  2: { label: "2주차", dot: "bg-blue-500" },
  1: { label: "1주차", dot: "bg-teal-500" },
}

function CompareCard({ r }: { r: CompareWeekResponse }) {
  const botEntries = Object.entries(r.bots).filter(([, v]) => v)
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Badge variant="outline" className="text-[10px]">
          {r.submitter ?? "익명"}
        </Badge>
        {r.same_question && r.week !== 3 && (
          <Badge variant="secondary" className="text-[10px]" title={`유사도 ${((r.match_score ?? 0) * 100).toFixed(0)}%`}>
            동일질문 {(r.match_score != null) && `${(r.match_score * 100).toFixed(0)}%`}
          </Badge>
        )}
        {r.rating != null && (
          <span className="rtm-mono text-xs text-muted-foreground">
            평점 <span className="font-semibold text-foreground">{r.rating.toFixed(0)}</span>/5
          </span>
        )}
        {r.risk && r.risk !== "없음" && (
          <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RISK_STYLE[r.risk])}>
            위험 {r.risk}
          </span>
        )}
      </div>

      {botEntries.length > 0 && (
        <div className="flex flex-col gap-2">
          {botEntries.map(([key, val]) => (
            <div key={key} className="rounded-md bg-muted/40 p-2">
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                {COMPARE_BOT_LABEL[key] ?? key}
              </p>
              <p className="whitespace-pre-wrap text-xs leading-relaxed">{val}</p>
            </div>
          ))}
        </div>
      )}
      {r.bot_note && (
        <p className="mt-1.5 text-[10px] italic text-muted-foreground">※ {r.bot_note}</p>
      )}

      {r.feedback_text && (
        <div className="mt-2 border-t pt-2">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            피드백
          </p>
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
            {r.feedback_text}
          </p>
        </div>
      )}

      {meaningfulEtc(r.etc) && (
        <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 p-2 dark:border-amber-900/40 dark:bg-amber-950/30">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300">
            기타 의견·건의
          </p>
          <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground/90">{r.etc}</p>
        </div>
      )}
    </div>
  )
}

// 테스트 봇 재검증 카드 (비교 탭용 — 좁은 칸에 맞춘 콤팩트 버전)
function CompareTestCard({ ev }: { ev: TestbotEval }) {
  const recur = ev.risk_recur ?? "판정불가"
  const indep = ev.independent_risk ?? "없음"
  return (
    <div className="rounded-lg border bg-card p-3">
      <div className="mb-2 flex flex-wrap items-center gap-1.5">
        <Badge className="bg-blue-600 text-[10px] text-white hover:bg-blue-600">{ev.bot_label}</Badge>
        <span className="rtm-mono text-[10px] text-muted-foreground">
          {ev.run_label}
          {ev.bot_model ? ` · ${ev.bot_model}` : ""}
        </span>
      </div>
      <div className="mb-2 flex flex-wrap gap-1">
        <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RECUR_STYLE[recur])}>재발: {recur}</span>
        <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-semibold", RISK_STYLE[indep] ?? "bg-muted text-muted-foreground")}>독립 {indep}</span>
        <span className={cn("rtm-mono rounded px-1.5 py-0.5 text-[10px] font-semibold", ratingBadgeCls(ev.ai_rating))}>AI {ev.ai_rating != null ? ev.ai_rating.toFixed(1) : "-"}</span>
      </div>
      <div className="whitespace-pre-wrap rounded-md bg-muted/40 p-2 text-xs leading-relaxed">{ev.answer}</div>
      <p className="mt-1.5 text-[10px] text-muted-foreground">{citeLine(ev)}</p>
      <div className="mt-2 space-y-1 border-t pt-2 text-[11px] leading-relaxed text-muted-foreground">
        {ev.risk_recur_detail && <p><b className="text-foreground/80">재발</b> {ev.risk_recur_detail}</p>}
        {ev.independent_risk_detail && <p><b className="text-foreground/80">독립위험</b> {ev.independent_risk_detail}</p>}
        {ev.ai_rating_detail && <p><b className="text-foreground/80">AI평점</b> {ev.ai_rating_detail}</p>}
      </div>
    </div>
  )
}

function TestColumn({ evals }: { evals: TestbotEval[] }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="sticky top-0 flex items-center gap-2 rounded-md border bg-background/95 px-3 py-2 text-sm font-semibold backdrop-blur">
        <span className="size-2.5 rounded-full bg-blue-600" />
        테스트 (재검증)
        <span className="text-xs font-normal text-muted-foreground">{evals.length}건</span>
      </div>
      {evals.map((ev, i) => (
        <CompareTestCard key={`${ev.bot_label}-${ev.run_label}-${i}`} ev={ev} />
      ))}
    </div>
  )
}

function WeekColumn({ week, items }: { week: number; items: CompareWeekResponse[] }) {
  const meta = WEEK_META[week]
  return (
    <div className="flex flex-col gap-3">
      <div className="sticky top-0 flex items-center gap-2 rounded-md border bg-background/95 px-3 py-2 text-sm font-semibold backdrop-blur">
        <span className={cn("size-2.5 rounded-full", meta.dot)} />
        {meta.label}
        <span className="text-xs font-normal text-muted-foreground">{items.length}건</span>
      </div>
      {items.length === 0 ? (
        <p className="rounded-md border border-dashed px-3 py-6 text-center text-xs text-muted-foreground">
          해당 주차에 동일 질문이 없습니다.
        </p>
      ) : (
        items.map((r, i) => <CompareCard key={i} r={r} />)
      )}
    </div>
  )
}

export function CompareColumns({ groupId }: { groupId: number | null }) {
  const { data: cmp, isLoading } = useGroupCompare(groupId)

  if (groupId === null) {
    return (
      <div className="flex h-full min-h-80 items-center justify-center p-8 text-center text-sm text-muted-foreground">
        왼쪽에서 질문을 선택하면 3·2·1주차 응답과 피드백을 나란히 비교합니다.
      </div>
    )
  }

  if (isLoading || !cmp) {
    return (
      <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="border-b pb-3">
        <h2 className="text-lg font-bold leading-snug">{cmp.question}</h2>
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="text-[11px]">
            {cmp.category ?? "미분류"}
          </Badge>
          {cmp.risk && cmp.risk !== "없음" && (
            <span className={cn("rounded px-2 py-0.5 text-xs font-semibold", RISK_STYLE[cmp.risk])}>
              최고 위험도 {cmp.risk}
            </span>
          )}
          <span className="text-xs text-muted-foreground">
            이전 주차 봇은 3주차 C/D 계보로 정규화해 표시합니다.
          </span>
        </div>
      </div>
      <div
        className={cn(
          "grid grid-cols-1 gap-4",
          cmp.testbot_evals.length > 0 ? "md:grid-cols-2 xl:grid-cols-4" : "md:grid-cols-3",
        )}
      >
        {cmp.testbot_evals.length > 0 && <TestColumn evals={cmp.testbot_evals} />}
        <WeekColumn week={3} items={cmp.week3} />
        <WeekColumn week={2} items={cmp.week2} />
        <WeekColumn week={1} items={cmp.week1} />
      </div>
    </div>
  )
}
