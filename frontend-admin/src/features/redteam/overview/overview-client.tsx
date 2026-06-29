"use client"

// 레드팀 현황(개요) — 상태등 KPI + 오늘 처리할 일(미결정 고위험) + 심의 진행률 커맨드보드.
import * as React from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowRight, Minus, TrendingDown, TrendingUp } from "lucide-react"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"
import { useRedteamReport, useRedteamStats } from "../hooks"
import type { ReportResponse, StatsResponse } from "../types"

type Status = "ok" | "warn" | "danger"

const STATUS_DOT: Record<Status, string> = {
  ok: "bg-[var(--rt-pine)]",
  warn: "bg-[var(--rt-amber)]",
  danger: "bg-[var(--rt-garnet)]",
}
const STATUS_LABEL: Record<Status, string> = {
  ok: "정상",
  warn: "주의",
  danger: "위험",
}

function StatusCard({
  label,
  value,
  sub,
  status,
}: {
  label: string
  value: React.ReactNode
  sub: string
  status: Status
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-card p-5">
      <div className="flex items-center justify-between">
        <span className="rt-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className={cn("size-2 rounded-full", STATUS_DOT[status])} />
          <span className="rt-mono text-[10px] uppercase tracking-[0.1em] text-muted-foreground">
            {STATUS_LABEL[status]}
          </span>
        </span>
      </div>
      <div className="rt-display text-[40px] font-bold leading-none">{value}</div>
      <span className="text-[11px] leading-snug text-muted-foreground">{sub}</span>
    </div>
  )
}

function ProgressBar({ label, value, total }: { label: string; value: number; total: number }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="rt-mono tabular-nums">
          {value}/{total} · {pct}%
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-[var(--rt-pine)] transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

export function OverviewClient() {
  const { data: report, isLoading: reportLoading } = useRedteamReport()
  const { data: stats, isLoading: statsLoading } = useRedteamStats()

  if (reportLoading || statsLoading || !report || !stats) {
    return (
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-8">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    )
  }

  return <OverviewBody report={report} stats={stats} />
}

function OverviewBody({ report, stats }: { report: ReportResponse; stats: StatsResponse }) {
  const router = useRouter()
  const s = report.summary

  const pendingHigh = report.pending_high_risk.filter((g) => g.risk === "상").length
  const decided = report.reflect_by_risk.reduce((acc, r) => acc + r.reflect + r.skip, 0)
  const totalGroups = stats.total_groups
  const coverage = totalGroups > 0 ? Math.round((decided / totalGroups) * 100) : 0

  const delta =
    s.avg_rating_week1 != null && s.avg_rating_week3 != null
      ? Math.round((s.avg_rating_week3 - s.avg_rating_week1) * 100) / 100
      : null
  const DeltaIcon = delta == null ? Minus : delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-7 px-6 py-8">
      <header className="border-b-2 border-[var(--rt-ink)] pb-5">
        <p className="rt-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--rt-pine)]">
          현황 <span className="text-[var(--rt-brass)]">·</span> 커맨드 보드
        </p>
        <h1 className="rt-display mt-2 text-3xl font-bold tracking-tight">레드팀 심의 현황</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          지금 무엇을 먼저 처리해야 하는지 한눈에. 위험·반영·진행률을 상태로 표시합니다.
        </p>
      </header>

      {/* 상태등 KPI */}
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatusCard
          label="출시 차단 위험 · 상"
          value={s.high_risk}
          sub={`주의(중) ${s.mid_risk}건 · 합 ${s.high_risk + s.mid_risk}건`}
          status={s.high_risk > 0 ? "danger" : "ok"}
        />
        <StatusCard
          label="미결정 고위험"
          value={report.pending_high_risk.length}
          sub={`상 ${pendingHigh}건 미착수 · 상·중 합산`}
          status={pendingHigh > 0 ? "danger" : report.pending_high_risk.length > 0 ? "warn" : "ok"}
        />
        <StatusCard
          label="심의 진행률"
          value={`${coverage}%`}
          sub={`${decided} / ${totalGroups} 질문 반영 결정 완료`}
          status={coverage >= 80 ? "ok" : coverage >= 40 ? "warn" : "danger"}
        />
        <StatusCard
          label="평점 추이 · 1→3주차"
          value={
            <span className="inline-flex items-baseline gap-2">
              {s.avg_rating_week3 ?? "—"}
              {delta != null && (
                <span
                  className={cn(
                    "rt-mono inline-flex items-center gap-0.5 text-sm font-semibold",
                    delta > 0
                      ? "text-[var(--rt-pine)]"
                      : delta < 0
                        ? "text-[var(--rt-garnet)]"
                        : "text-muted-foreground"
                  )}
                >
                  <DeltaIcon className="size-4" />
                  {delta > 0 ? "+" : ""}
                  {delta.toFixed(2)}
                </span>
              )}
            </span>
          }
          sub={`1주차 ${s.avg_rating_week1 ?? "—"} → 3주차 ${s.avg_rating_week3 ?? "—"} · 5점`}
          status={delta == null ? "warn" : delta > 0 ? "ok" : delta < 0 ? "danger" : "warn"}
        />
      </section>

      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        {/* 오늘 처리할 일 */}
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h2 className="rt-display text-base font-bold text-[var(--rt-pine)]">
              오늘 처리할 일 · 미결정 고위험
            </h2>
            <span className="rt-mono text-xs text-muted-foreground">
              {report.pending_high_risk.length}건
            </span>
          </div>
          {report.pending_high_risk.length === 0 ? (
            <p className="px-4 py-10 text-center text-sm text-muted-foreground">
              미결정 고위험 질문이 없습니다. 모두 처리됐습니다.
            </p>
          ) : (
            <ul className="max-h-[28rem] divide-y divide-border overflow-auto">
              {report.pending_high_risk.slice(0, 30).map((g) => (
                <li key={g.group_id}>
                  <button
                    onClick={() => router.push(`/redteam?selectedId=${g.group_id}`)}
                    className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-[rgba(176,133,36,0.06)]"
                  >
                    <span
                      className={cn(
                        "rt-chip rt-mono shrink-0 text-[11px]",
                        g.risk === "상" ? "rt-chip-high" : "rt-chip-mid"
                      )}
                      style={{ width: 26, height: 26 }}
                    >
                      {g.risk}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="rt-display line-clamp-1 text-sm">{g.question}</span>
                      <span className="text-[11px] text-muted-foreground">
                        {g.category ?? "미분류"} · 리뷰어 {g.reviewer_count}명
                      </span>
                    </span>
                    <ArrowRight className="size-4 shrink-0 text-muted-foreground" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* 심의 진행률 */}
        <section className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4">
          <h2 className="rt-display text-base font-bold text-[var(--rt-pine)]">심의 진행률</h2>
          <ProgressBar label="반영 결정 완료" value={decided} total={totalGroups} />
          <div className="border-t border-border pt-3">
            <p className="mb-2 text-xs font-semibold text-muted-foreground">리뷰어별 작성</p>
            <div className="flex flex-col gap-2.5">
              {Object.keys(stats.review_progress).length === 0 ? (
                <p className="text-xs text-muted-foreground">아직 작성한 리뷰어가 없습니다.</p>
              ) : (
                Object.entries(stats.review_progress).map(([name, count]) => (
                  <ProgressBar key={name} label={name} value={count} total={totalGroups} />
                ))
              )}
            </div>
          </div>
          <div className="mt-1 flex items-center justify-between border-t border-border pt-3 text-sm">
            <span className="text-muted-foreground">판정이 갈린 질문</span>
            <span className="rt-mono font-semibold text-[var(--rt-garnet)]">
              {report.reviewer_agreement.split}건
            </span>
          </div>
          <Link
            href="/redteam/report"
            className="rt-mono mt-1 inline-flex items-center gap-1 text-xs text-[var(--rt-pine)] hover:underline"
          >
            보고에서 전체 분석 보기 <ArrowRight className="size-3" />
          </Link>
        </section>
      </div>
    </div>
  )
}
