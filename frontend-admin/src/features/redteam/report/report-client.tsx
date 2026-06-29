"use client"

// 윗선 보고용 독립 대시보드 — "심의·봉인". 읽기전용, 차트 중심, PDF·인쇄 지원.
import * as React from "react"
import {
  ArrowDown,
  ArrowUp,
  ChevronsUpDown,
  Download,
  Minus,
  Printer,
  TrendingDown,
  TrendingUp,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { useRedteamReport } from "../hooks"
import type { ReportResponse, TopRiskQuestion } from "../types"
import { downloadCsv } from "./export-utils"
import {
  BotByCategoryBar,
  BotPreferencePie,
  CategoryBar,
  ChartCard,
  ImprovementBar,
  RatingByWeekBar,
  RatingTrendLine,
  ReflectByRiskBar,
  RiskCategoryHeatmap,
  RiskDonut,
} from "./report-charts"
import { ReportDrilldown, type DrillFilter } from "./report-drilldown"

// 가넷 봉인 — 헤드라인 위험 판정
function VerdictSeal({ high, mid }: { high: number; mid: number }) {
  return (
    <div className="flex shrink-0 flex-col items-center gap-2">
      <div className="rt-seal" style={{ width: 124, height: 124 }}>
        <div className="relative z-[2] text-center leading-none">
          <div className="rt-mono text-[8px] uppercase tracking-[0.34em] opacity-85">위험 판정</div>
          <div
            className="rt-display mt-1 text-[40px] font-bold leading-[0.92]"
            style={{ textShadow: "0 1px 1px rgba(80,15,8,.6), 0 -1px 0 rgba(255,255,255,.25)" }}
          >
            {high + mid}
          </div>
          <div className="rt-mono mt-1 inline-block border-t border-[rgba(252,239,230,.4)] pt-1 text-[9px] font-semibold tracking-[0.12em]">
            상 {high} · 중 {mid}
          </div>
        </div>
      </div>
      <div className="rt-mono text-[9px] uppercase tracking-[0.18em] text-muted-foreground">
        심의필 · 출시 전 차단 {high}
      </div>
    </div>
  )
}

function RatingDelta({ summary }: { summary: ReportResponse["summary"] }) {
  const w1 = summary.avg_rating_week1
  const w3 = summary.avg_rating_week3
  if (w1 == null || w3 == null) return <span>—</span>
  const delta = Math.round((w3 - w1) * 100) / 100
  const Icon = delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus
  const color =
    delta > 0
      ? "text-[var(--rt-pine)]"
      : delta < 0
        ? "text-[var(--rt-garnet)]"
        : "text-muted-foreground"
  return (
    <span className="inline-flex items-baseline gap-2">
      <span className="rt-mono">{w3.toFixed(2)}</span>
      <span className={cn("rt-mono inline-flex items-center gap-0.5 text-sm font-semibold", color)}>
        <Icon className="size-4" />
        {delta > 0 ? "+" : ""}
        {delta.toFixed(2)}
      </span>
    </span>
  )
}

function KpiCell({
  label,
  value,
  sub,
  pine,
  valueClass,
}: {
  label: string
  value: React.ReactNode
  sub: string
  pine?: boolean
  valueClass?: string
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-1.5 px-5 py-5 [&:not(:first-child)]:border-l [&:not(:first-child)]:border-border",
        pine && "rt-pine"
      )}
    >
      <span
        className={cn(
          "rt-mono text-[10px] font-semibold uppercase tracking-[0.14em]",
          pine ? "text-[var(--rt-brass)]" : "text-muted-foreground"
        )}
      >
        {label}
      </span>
      <div className={cn("rt-display text-[40px] font-bold leading-none", valueClass)}>{value}</div>
      <span className={cn("text-[11px] leading-snug", pine ? "text-[rgba(241,237,226,.78)]" : "text-muted-foreground")}>
        {sub}
      </span>
    </div>
  )
}

function SecHead({ no, title, desc }: { no: string; title: string; desc?: string }) {
  return (
    <div className="mb-4 flex items-baseline gap-3 border-b border-border pb-2.5">
      <span className="rt-secno">{no}</span>
      <h2 className="rt-display text-xl font-bold">{title}</h2>
      {desc && <span className="ml-auto hidden text-xs text-muted-foreground sm:block">{desc}</span>}
    </div>
  )
}

const RISK_CHIP: Record<string, string> = {
  없음: "rt-chip-none",
  하: "rt-chip-low",
  중: "rt-chip-mid",
  상: "rt-chip-high",
}

// 드릴다운 가능한 질문 행 (개선/악화/보류/갈림 리스트 공용)
function QuestionRow({
  question,
  meta,
  right,
  onClick,
}: {
  question: string
  meta?: string
  right: React.ReactNode
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 border-b border-border px-3 py-2.5 text-left last:border-0 hover:bg-[rgba(176,133,36,0.06)]"
    >
      <div className="min-w-0 flex-1">
        <p className="rt-display line-clamp-1 text-sm">{question}</p>
        {meta && <p className="text-[11px] text-muted-foreground">{meta}</p>}
      </div>
      <div className="shrink-0">{right}</div>
    </button>
  )
}

function ListCard({
  title,
  empty,
  children,
}: {
  title: string
  empty: boolean
  children: React.ReactNode
}) {
  return (
    <div className="rounded-md border border-border bg-card">
      <div className="border-b border-border px-3 py-2 text-xs font-semibold text-[var(--rt-pine)]">
        {title}
      </div>
      {empty ? (
        <p className="px-3 py-6 text-center text-xs text-muted-foreground">해당 항목이 없습니다.</p>
      ) : (
        <div className="max-h-72 overflow-auto">{children}</div>
      )}
    </div>
  )
}

function AgreementStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-md border border-border bg-card px-3 py-4">
      <span className={cn("rt-display text-3xl font-bold leading-none", tone)}>{value}</span>
      <span className="text-center text-[11px] text-muted-foreground">{label}</span>
    </div>
  )
}

const RISK_RANK: Record<string, number> = { 없음: 0, 하: 1, 중: 2, 상: 3 }

type SortKey = "question" | "category" | "risk" | "rating"
type SortDir = "asc" | "desc"

// 우선 조치 질문 — 정렬(aria-sort) + CSV 내보내기 + 행 클릭 드릴다운
function PriorityTable({
  rows,
  onRow,
}: {
  rows: TopRiskQuestion[]
  onRow: (group_id: number, question: string) => void
}) {
  const [sort, setSort] = React.useState<{ key: SortKey; dir: SortDir }>({
    key: "risk",
    dir: "desc",
  })

  const sorted = React.useMemo(() => {
    const arr = [...rows]
    const { key, dir } = sort
    const mul = dir === "asc" ? 1 : -1
    arr.sort((a, b) => {
      let av: number | string
      let bv: number | string
      if (key === "risk") {
        av = RISK_RANK[a.risk ?? "없음"]
        bv = RISK_RANK[b.risk ?? "없음"]
      } else if (key === "rating") {
        av = a.rating_avg ?? -1
        bv = b.rating_avg ?? -1
      } else {
        av = (key === "question" ? a.question : a.category ?? "")
        bv = (key === "question" ? b.question : b.category ?? "")
      }
      if (av < bv) return -1 * mul
      if (av > bv) return 1 * mul
      return 0
    })
    return arr
  }, [rows, sort])

  const toggle = (key: SortKey) =>
    setSort((s) =>
      s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "desc" }
    )

  const exportCsv = () =>
    downloadCsv(
      "레드팀_우선조치질문.csv",
      sorted.map((q) => ({
        질문: q.question,
        카테고리: q.category ?? "미분류",
        위험도: q.risk ?? "없음",
        "3주차 평점": q.rating_avg ?? "",
      })),
      [
        { key: "질문", label: "질문" },
        { key: "카테고리", label: "카테고리" },
        { key: "위험도", label: "위험도" },
        { key: "3주차 평점", label: "3주차 평점" },
      ]
    )

  const Th = ({
    label,
    sortKey,
    align,
  }: {
    label: string
    sortKey: SortKey
    align?: "center" | "right"
  }) => {
    const active = sort.key === sortKey
    const Icon = !active ? ChevronsUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown
    return (
      <th
        aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
        className={cn(
          "rt-mono px-4 py-2.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-muted-foreground",
          align === "center" && "text-center",
          align === "right" && "text-right"
        )}
      >
        <button
          onClick={() => toggle(sortKey)}
          className={cn(
            "inline-flex items-center gap-1 hover:text-foreground",
            align === "center" && "mx-auto",
            align === "right" && "ml-auto",
            active && "text-foreground"
          )}
        >
          {label}
          <Icon className="size-3" />
        </button>
      </th>
    )
  }

  return (
    <>
      <div className="mb-2 flex justify-end print:hidden">
        <Button variant="outline" size="sm" className="h-8 text-xs" onClick={exportCsv}>
          <Download className="size-3.5" /> CSV 내보내기
        </Button>
      </div>
      <div className="overflow-x-auto rounded-md border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--rt-ink)] text-left">
              <Th label="질문" sortKey="question" />
              <Th label="카테고리" sortKey="category" />
              <Th label="위험" sortKey="risk" align="center" />
              <Th label="3주차 평점" sortKey="rating" align="right" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((q) => (
              <tr
                key={q.group_id}
                onClick={() => onRow(q.group_id, q.question)}
                className="cursor-pointer border-b border-border align-middle last:border-0 hover:bg-[rgba(176,133,36,0.06)] print:cursor-auto"
              >
                <td className="rt-display max-w-[520px] px-4 py-3 leading-relaxed">
                  <span className="rt-display mr-1.5 font-bold text-[var(--rt-brass)]">›</span>
                  {q.question}
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground">{q.category ?? "미분류"}</td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={cn("rt-chip rt-mono mx-auto text-[11px]", RISK_CHIP[q.risk ?? "없음"])}
                    style={{ width: 28, height: 28 }}
                  >
                    {q.risk}
                  </span>
                </td>
                <td className="rt-mono px-4 py-3 text-right font-semibold">
                  {q.rating_avg != null ? q.rating_avg.toFixed(1) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export function ReportClient() {
  const { data: report, isLoading } = useRedteamReport()
  const [printedAt, setPrintedAt] = React.useState("")
  const [drill, setDrill] = React.useState<DrillFilter | null>(null)

  React.useEffect(() => {
    setPrintedAt(new Date().toLocaleString("ko-KR", { dateStyle: "long", timeStyle: "short" }))
  }, [])

  return (
    <div className="mx-auto max-w-7xl px-6 py-8 print:px-0 print:py-2">
      {/* 마스트헤드 */}
      <header className="mb-7 flex flex-col gap-6 border-b-2 border-[var(--rt-ink)] pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="rt-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--rt-pine)]">
            심의 <span className="text-[var(--rt-brass)]">·</span> 1·2·3주차 종합
          </p>
          <h1 className="rt-display mt-2 text-4xl font-bold leading-tight tracking-tight">
            레드팀 피드백 종합 보고
          </h1>
          <p className="rt-display mt-3 max-w-xl text-[15px] leading-relaxed text-[var(--rt-pine)]">
            세 차례 레드팀 심의 대상 답변의 위험도·품질·페르소나를 판정한 종합 보고. 축복·가정관리 AI 챗봇.
          </p>
          <p className="rt-mono mt-2 text-[10.5px] uppercase tracking-[0.1em] text-muted-foreground">
            작성 {printedAt}
          </p>
        </div>
        <div className="flex items-start gap-6">
          {report && <VerdictSeal high={report.summary.high_risk} mid={report.summary.mid_risk} />}
          <Button onClick={() => window.print()} className="print:hidden">
            <Printer className="size-4" /> 인쇄 · PDF
          </Button>
        </div>
      </header>

      {isLoading || !report ? (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-72 w-full" />
        </div>
      ) : (
        <ReportBody report={report} onDrill={setDrill} />
      )}

      <ReportDrilldown filter={drill} onClose={() => setDrill(null)} />
    </div>
  )
}

function ReportBody({
  report,
  onDrill,
}: {
  report: ReportResponse
  onDrill: (f: DrillFilter) => void
}) {
  const s = report.summary
  const imp = report.bot_improvement
  const agree = report.reviewer_agreement
  const drillGroup = (group_id: number, question: string) =>
    onDrill({ label: question, groupId: group_id })
  return (
    <div className="flex flex-col gap-8">
      {/* KPI 마스트헤드 스트립 */}
      <section className="grid grid-cols-2 border-y border-border lg:grid-cols-4 print:grid-cols-4">
        <KpiCell
          label="기준 질문 · 3주차"
          value={<span className="rt-mono">{s.total_groups}</span>}
          sub={`전체 응답 ${s.total_responses.toLocaleString()}건 · ${s.responses_by_week["1"]} / ${s.responses_by_week["2"]} / ${s.responses_by_week["3"]}`}
        />
        <KpiCell
          label="위험 질문 · 상·중"
          value={<span className="rt-mono">{s.high_risk + s.mid_risk}</span>}
          valueClass="text-[var(--rt-garnet)]"
          sub={`출시 차단(상) ${s.high_risk}건 · 주의(중) ${s.mid_risk}건`}
        />
        <KpiCell
          label="평균 평점 추이 · 1→3주차"
          value={<RatingDelta summary={s} />}
          sub={`1주차 ${s.avg_rating_week1 ?? "—"} → 3주차 ${s.avg_rating_week3 ?? "—"} · 5점 만점`}
        />
        <KpiCell
          pine
          label="3주차 선호 챗봇"
          value={
            <span className="inline-flex items-baseline gap-2">
              {s.bot_d >= s.bot_c ? "D" : "C"}
              <span className="rt-display text-base font-medium opacity-80">
                {s.bot_d >= s.bot_c ? "여정 동반자" : "실무안내자"}
              </span>
            </span>
          }
          sub={`C ${s.bot_c} · D ${s.bot_d} · 부적절 ${s.bot_none}`}
        />
      </section>

      {/* 01. 위험 지도 */}
      <section className="break-inside-avoid">
        <SecHead no="01" title="위험 지도" desc="조각·셀을 클릭하면 해당 질문으로 드릴다운" />
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="위험도 분포"
            description="3주차 기준 질문의 최고 위험도 · 조각 클릭 시 해당 질문"
            exportName="위험도분포"
          >
            <RiskDonut
              data={report.risk_distribution}
              onSlice={(level) => onDrill({ label: `위험도 ${level}`, risk: level })}
            />
          </ChartCard>
          <ChartCard title="위험도 × 카테고리" description="셀 = 카테고리·위험도별 질문 수 · 클릭 시 드릴다운">
            <RiskCategoryHeatmap
              data={report.risk_by_category}
              onCell={(risk, category) =>
                onDrill({ label: `${category} · 위험도 ${risk}`, risk, category })
              }
            />
          </ChartCard>
        </div>
      </section>

      {/* 02. 개선 추적 */}
      <section className="break-inside-avoid">
        <SecHead no="02" title="개선 추적" desc={`1주차→3주차 평점 변화 · 비교 가능 ${imp.compared}개 질문`} />
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="개선 / 정체 / 악화"
            description="같은 질문의 1주차 대비 3주차 평점 (±0.25 기준)"
            exportName="개선추적"
          >
            <ImprovementBar
              data={[
                { name: "개선", value: imp.improved, color: "#1e3a34" },
                { name: "정체", value: imp.same, color: "#9aa39a" },
                { name: "악화", value: imp.declined, color: "#b5321e" },
              ]}
            />
          </ChartCard>
          <ChartCard
            title="평균 평점 추이"
            description="적절성·유용성 평균 (2주차는 평점 미측정)"
            exportName="평점추이"
          >
            <RatingTrendLine data={report.rating_trend} />
          </ChartCard>
        </div>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <ListCard title="가장 개선된 질문" empty={imp.top_improved.length === 0}>
            {imp.top_improved.map((r) => (
              <QuestionRow
                key={r.group_id}
                question={r.question}
                meta={`${r.category ?? "미분류"} · ${r.week1_avg} → ${r.week3_avg}`}
                right={
                  <span className="rt-mono text-sm font-semibold text-[var(--rt-pine)]">
                    +{r.delta.toFixed(2)}
                  </span>
                }
                onClick={() => drillGroup(r.group_id, r.question)}
              />
            ))}
          </ListCard>
          <ListCard title="악화된 질문" empty={imp.top_declined.length === 0}>
            {imp.top_declined.map((r) => (
              <QuestionRow
                key={r.group_id}
                question={r.question}
                meta={`${r.category ?? "미분류"} · ${r.week1_avg} → ${r.week3_avg}`}
                right={
                  <span className="rt-mono text-sm font-semibold text-[var(--rt-garnet)]">
                    {r.delta.toFixed(2)}
                  </span>
                }
                onClick={() => drillGroup(r.group_id, r.question)}
              />
            ))}
          </ListCard>
        </div>
        <div className="mt-4">
          <ChartCard
            title="평점 분포 (1주차 vs 3주차)"
            description="점수대별 응답 수 비교 — 고득점 이동 여부"
            exportName="평점분포"
          >
            <RatingByWeekBar data={report.rating_by_week} />
          </ChartCard>
        </div>
      </section>

      {/* 03. 챗봇 비교 */}
      <section className="break-inside-avoid">
        <SecHead no="03" title="챗봇 비교 · 3주차" desc="적절했던 페르소나" />
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="적절 챗봇 선호"
            description="응답이 적절했던 챗봇 (C 실무안내자 / D 여정 동반자 / 둘 다 부적절)"
            exportName="챗봇선호"
          >
            <BotPreferencePie data={report.bot_preference} />
          </ChartCard>
          <ChartCard
            title="카테고리별 선호 챗봇"
            description="주제별로 어떤 페르소나가 더 적합했는지"
            exportName="카테고리별챗봇"
          >
            <BotByCategoryBar data={report.bot_by_category} />
          </ChartCard>
        </div>
      </section>

      {/* 04. 카테고리 분포 */}
      <section className="break-inside-avoid">
        <SecHead no="04" title="질문 카테고리 분포" desc="막대 클릭 시 해당 카테고리 질문" />
        <ChartCard title="카테고리별 질문 수" exportName="카테고리분포">
          <CategoryBar
            data={report.category_distribution}
            onBar={(category) => onDrill({ label: `카테고리 ${category}`, category })}
          />
        </ChartCard>
      </section>

      {/* 05. 반영 현황 · 합의도 */}
      <section className="break-inside-avoid">
        <SecHead no="05" title="반영 현황 · 합의도" desc="3주차 반영 결정 기준" />
        <div className="grid gap-4 lg:grid-cols-2">
          <ChartCard
            title="위험도별 반영 현황"
            description="고위험인데 보류(주황)면 우선 처리 대상"
            exportName="반영현황"
          >
            <ReflectByRiskBar data={report.reflect_by_risk} />
          </ChartCard>
          <div className="flex flex-col gap-3">
            <div className="grid grid-cols-3 gap-2">
              <AgreementStat label="만장일치 반영" value={agree.unanimous_reflect} tone="text-[var(--rt-pine)]" />
              <AgreementStat label="만장일치 미반영" value={agree.unanimous_skip} tone="text-muted-foreground" />
              <AgreementStat label="판정 갈림" value={agree.split} tone="text-[var(--rt-garnet)]" />
            </div>
            <ListCard title="판정이 갈린 질문 (재검토 후보)" empty={report.split_groups.length === 0}>
              {report.split_groups.map((g) => (
                <QuestionRow
                  key={g.group_id}
                  question={g.question}
                  meta={`${g.category ?? "미분류"} · 위험 ${g.risk ?? "없음"}`}
                  right={<span className="rt-mono text-xs">반영 {g.reflect} · 미 {g.skip}</span>}
                  onClick={() => drillGroup(g.group_id, g.question)}
                />
              ))}
            </ListCard>
          </div>
        </div>
        <div className="mt-4">
          <ListCard
            title={`아직 미결정 고위험 질문 (상·중 · ${report.pending_high_risk.length}건)`}
            empty={report.pending_high_risk.length === 0}
          >
            {report.pending_high_risk.map((g) => (
              <QuestionRow
                key={g.group_id}
                question={g.question}
                meta={`${g.category ?? "미분류"} · 리뷰어 ${g.reviewer_count}명`}
                right={
                  <span
                    className={cn("rt-chip rt-mono text-[11px]", RISK_CHIP[g.risk ?? "없음"])}
                    style={{ width: 28, height: 28 }}
                  >
                    {g.risk}
                  </span>
                }
                onClick={() => drillGroup(g.group_id, g.question)}
              />
            ))}
          </ListCard>
        </div>
      </section>

      {/* 06. 우선 조치 필요 질문 */}
      <section className="break-inside-avoid">
        <SecHead no="06" title="우선 조치 필요 질문" desc="상·중 위험 · 열 정렬·CSV·행 클릭 상세" />
        <PriorityTable rows={report.top_risk_questions} onRow={drillGroup} />
      </section>

      <footer className="rt-mono mt-2 border-t border-border pt-4 text-center text-[10px] uppercase tracking-[0.15em] text-muted-foreground print:mt-6">
        Nexus Core · 레드팀 피드백 종합 보고 · 데이터 출처 1·2·3주차 레드팀 응답 시트
      </footer>
    </div>
  )
}
