"use client"

// 레드팀 결과 보고서(문서형) — 평균 대신 만족도 분포 이동·적절응답률·위험으로 '개선'을 보여줌.
import { Printer } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { RISK_COLOR } from "../constants"
import { useManageReport } from "../hooks"
import type { ManageReportResponse } from "../types"

function Section({
  no,
  title,
  children,
}: {
  no: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="border-t border-border pt-6">
      <h2 className="mb-3 flex items-center gap-2 text-base font-bold">
        <span className="rtm-mono text-xs font-semibold text-primary">{no}</span>
        {title}
      </h2>
      {children}
    </section>
  )
}

// 만족도 분포 스택 바 (저=red, 중=slate, 고=green)
function SatBar({ label, high, low }: { label: string; high: number | null; low: number | null }) {
  if (high == null || low == null) {
    return (
      <div className="flex items-center gap-3 text-xs">
        <span className="w-16 shrink-0 text-muted-foreground">{label}</span>
        <span className="text-muted-foreground">평점 미수집</span>
      </div>
    )
  }
  const mid = Math.max(0, 100 - high - low)
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-16 shrink-0 text-muted-foreground">{label}</span>
      <div className="flex h-5 flex-1 overflow-hidden rounded">
        <div style={{ width: `${low}%`, background: "#dc2626" }} title={`불만족 ${low}%`} />
        <div style={{ width: `${mid}%`, background: "#cbd5e1" }} title={`보통 ${mid.toFixed(1)}%`} />
        <div style={{ width: `${high}%`, background: "#059669" }} title={`만족 ${high}%`} />
      </div>
      <span className="rtm-mono w-28 shrink-0 text-right text-[11px]">
        만족 <b className="text-emerald-700">{high}%</b> · 불만 <b className="text-red-600">{low}%</b>
      </span>
    </div>
  )
}

function Bars({ data, max }: { data: { label: string; value: number }[]; max: number }) {
  return (
    <div className="flex flex-col gap-1.5">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate text-muted-foreground">{d.label}</span>
          <div className="h-3.5 flex-1 overflow-hidden rounded bg-muted">
            <div
              className="h-full rounded bg-primary/80"
              style={{ width: `${(d.value / Math.max(1, max)) * 100}%` }}
            />
          </div>
          <span className="rtm-mono w-9 shrink-0 text-right">{d.value}</span>
        </div>
      ))}
    </div>
  )
}

function ExecStat({ value, label, tone }: { value: string; label: string; tone?: string }) {
  return (
    <div className="rounded-lg border bg-muted/30 px-3 py-2.5">
      <p className={cn("rtm-mono text-xl font-bold tabular-nums", tone)}>{value}</p>
      <p className="text-[11px] text-muted-foreground">{label}</p>
    </div>
  )
}

function ReportBody({ d }: { d: ManageReportResponse }) {
  const r1 = d.rating.find((r) => r.week === 1)
  const r3 = d.rating.find((r) => r.week === 3)
  const highShift =
    r1?.high_pct != null && r3?.high_pct != null ? +(r3.high_pct - r1.high_pct).toFixed(1) : null
  const lowRelDrop =
    r1?.low_pct && r3?.low_pct != null && r1.low_pct > 0
      ? Math.round(((r1.low_pct - r3.low_pct) / r1.low_pct) * 100)
      : null
  const catMax = Math.max(...d.category_dist.map((c) => c.count), 1)
  const appr = d.appropriate

  return (
    <div className="flex flex-col gap-6">
      {/* 1. 요약 */}
      <Section no="01" title="요약">
        <div className="mb-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <ExecStat
            value={highShift != null ? `+${highShift}%p` : "—"}
            label="만족(4·5점) 비율 상승"
            tone="text-emerald-700"
          />
          <ExecStat
            value={lowRelDrop != null ? `−${lowRelDrop}%` : "—"}
            label="불만족(1·2점) 감소(상대)"
            tone="text-red-600"
          />
          <ExecStat
            value={appr.rate != null ? `${appr.rate}%` : "—"}
            label="3주차 적절 응답률"
          />
          <ExecStat value={String(d.high_risk)} label="고위험(상·중) 질문" tone="text-orange-600" />
        </div>
        <p className="text-sm leading-relaxed text-foreground/90">
          3주차부터 <b>위험도 평가가 더해져 채점이 더 엄격해진 조건</b>에서도, 만족(4·5점) 응답
          비율은 <b className="text-emerald-700">{r1?.high_pct}% → {r3?.high_pct}%</b>로 올랐고
          불만족(1·2점) 응답은 <b className="text-red-600">{r1?.low_pct}% → {r3?.low_pct}%</b>로{" "}
          {lowRelDrop != null && <>약 {lowRelDrop}% </>}줄었습니다. 순긍정(만족−불만족)은{" "}
          <b>+{r1?.net}%p → +{r3?.net}%p</b>로 거의 두 배가 되었습니다. 사용자는 3주차 두 봇 중{" "}
          <b>{appr.rate}%</b>에서 최소 하나를 적절하다고 평가했습니다. 전체 {d.total_groups}개
          질문(3주차 기준 {d.week3_groups} · 1·2주차 전용 {d.prior_only_groups}) 중 고위험{" "}
          {d.high_risk}건이 우선 검토 대상입니다.
        </p>
      </Section>

      {/* 2. 봇 발전 */}
      <Section no="02" title="봇 발전 — 만족도 분포 이동">
        <div className="flex flex-col gap-2 rounded-lg border bg-card p-4">
          <SatBar label="1주차" high={r1?.high_pct ?? null} low={r1?.low_pct ?? null} />
          <SatBar label="2주차" high={null} low={null} />
          <SatBar label="3주차" high={r3?.high_pct ?? null} low={r3?.low_pct ?? null} />
          <p className="mt-1 text-[11px] text-muted-foreground">
            <span className="mr-2 inline-block size-2 rounded-full align-middle" style={{ background: "#059669" }} />
            만족(4·5)
            <span className="mx-2 inline-block size-2 rounded-full align-middle" style={{ background: "#cbd5e1" }} />
            보통(3)
            <span className="mx-2 inline-block size-2 rounded-full align-middle" style={{ background: "#dc2626" }} />
            불만족(1·2) · 평균 평점은 {r1?.avg} → {r3?.avg}(보조 지표)
          </p>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          3주차 선호 봇: <b className="text-foreground">D(여정 동반자) {d.bot_pref.D}</b> · C(실무안내자){" "}
          {d.bot_pref.C} · 둘 다 부적절 {d.bot_pref.none}
        </p>
      </Section>

      {/* 3. 위험 분석 */}
      <Section no="03" title="위험 분석">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-lg border bg-card p-4">
            <p className="mb-2 text-xs font-semibold">3주차 답변 위험도</p>
            <div className="flex h-5 overflow-hidden rounded">
              {d.risk_dist.map((r) => (
                <div
                  key={r.level}
                  style={{ width: `${r.pct}%`, background: RISK_COLOR[r.level] }}
                  title={`${r.level} ${r.pct}%`}
                />
              ))}
            </div>
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
              {d.risk_dist.map((r) => (
                <span key={r.level}>
                  <span className="mr-1 inline-block size-2 rounded-full align-middle" style={{ background: RISK_COLOR[r.level] }} />
                  {r.level} <b className="rtm-mono text-foreground">{r.pct}%</b>
                </span>
              ))}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="mb-2 text-xs font-semibold">카테고리별 고위험 (상·중)</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-muted-foreground">
                  <th className="py-1 text-left font-medium">카테고리</th>
                  <th className="w-10 py-1 text-right font-medium">상</th>
                  <th className="w-10 py-1 text-right font-medium">중</th>
                </tr>
              </thead>
              <tbody>
                {d.risk_by_category.slice(0, 6).map((c) => (
                  <tr key={c.category} className="border-t">
                    <td className="py-1">{c.category}</td>
                    <td className="rtm-mono py-1 text-right text-red-600">{c["상"]}</td>
                    <td className="rtm-mono py-1 text-right text-orange-600">{c["중"]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-1.5 text-[11px] text-muted-foreground">미분류 카테고리에 고위험이 집중 → 분류 우선.</p>
          </div>
        </div>
      </Section>

      {/* 4. 카테고리 구성 */}
      <Section no="04" title="카테고리 구성">
        <div className="rounded-lg border bg-card p-4">
          <Bars data={d.category_dist.map((c) => ({ label: c.category, value: c.count }))} max={catMax} />
        </div>
      </Section>

      {/* 5. 다음 단계 */}
      <Section no="05" title="분류 진척 · 다음 단계">
        <ul className="flex list-disc flex-col gap-1.5 pl-5 text-sm text-foreground/90">
          <li>미분류 카테고리 질문 우선 분류 (학습 / FAQ 구분)</li>
          <li>고위험(상·중) {d.high_risk}건 검증·모범답변 확정</li>
          <li>다주차 중복 {d.multiweek_groups}건(주로 2↔3주차)은 주차별 평가 변화 비교</li>
          <li>
            1↔3주차 동일 질문은 0건이라 질문 단위 직접 비교는 불가 — 집단 평균·분포 추이로 평가
          </li>
        </ul>
      </Section>

      {/* 6. 우선 조치 질문 */}
      <Section no="06" title="우선 조치 질문 (고위험 상)">
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-xs">
            <thead className="bg-muted/50 text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left font-medium">질문</th>
                <th className="w-32 px-3 py-2 text-left font-medium">카테고리</th>
                <th className="w-16 px-3 py-2 text-right font-medium">평점</th>
              </tr>
            </thead>
            <tbody>
              {d.top_risk_questions.slice(0, 10).map((q) => (
                <tr key={q.group_id} className="border-t">
                  <td className="px-3 py-2">{q.question}</td>
                  <td className="px-3 py-2 text-muted-foreground">{q.category ?? "미분류"}</td>
                  <td className="rtm-mono px-3 py-2 text-right">
                    {q.rating_avg != null ? q.rating_avg.toFixed(1) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}

export function ReportClient() {
  const { data, isLoading } = useManageReport()

  return (
    <div className="mx-auto max-w-[880px] px-6 py-8">
      <div className="rounded-xl border bg-card p-8 shadow-sm print:border-0 print:p-0 print:shadow-none">
        <div className="mb-6 flex items-start justify-between gap-4 border-b border-border pb-5">
          <div>
            <h1 className="rtm-display text-2xl tracking-tight">축복챗 레드팀 결과 보고서</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              1~3주차 발전·위험·분류 분석 · 입력관리
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-8 shrink-0 print:hidden"
            onClick={() => window.print()}
          >
            <Printer className="size-3.5" /> 인쇄 / PDF
          </Button>
        </div>

        {isLoading || !data ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-40 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        ) : (
          <ReportBody d={data} />
        )}
      </div>
    </div>
  )
}
