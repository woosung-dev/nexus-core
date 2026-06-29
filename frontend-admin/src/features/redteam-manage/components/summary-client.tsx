"use client"

// 중간보고 요약 — 상태/레벨/분류/태그/담당자 분포 + 진행 KPI (입력관리 현황 보고용).
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DISPOSITION_COLOR,
  LEVEL_COLOR,
  STATUS_COLOR,
} from "../constants"
import { useManageStats } from "../hooks"

function Bars({
  data,
  colorOf,
}: {
  data: { label: string; value: number }[]
  colorOf?: (label: string) => string
}) {
  const max = Math.max(1, ...data.map((d) => d.value))
  if (data.length === 0) {
    return <p className="text-xs text-muted-foreground">데이터 없음</p>
  }
  return (
    <div className="flex flex-col gap-2">
      {data.map((d) => (
        <div key={d.label} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate text-muted-foreground" title={d.label}>
            {d.label}
          </span>
          <div className="h-4 flex-1 overflow-hidden rounded bg-muted">
            <div
              className="h-full rounded"
              style={{
                width: `${(d.value / max) * 100}%`,
                backgroundColor: colorOf?.(d.label) ?? "#1e3a34",
                minWidth: d.value > 0 ? 4 : 0,
              }}
            />
          </div>
          <span className="w-10 shrink-0 text-right font-semibold tabular-nums">{d.value}</span>
        </div>
      ))}
    </div>
  )
}

function ordered(
  rec: Record<string, number>,
  keys: string[]
): { label: string; value: number }[] {
  return keys.map((k) => ({ label: k, value: rec[k] ?? 0 }))
}

function topN(rec: Record<string, number>, n: number): { label: string; value: number }[] {
  return Object.entries(rec)
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([label, value]) => ({ label, value }))
}

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className="rt-mono text-2xl font-bold tabular-nums">{value}</p>
      {sub && <p className="text-[11px] text-muted-foreground">{sub}</p>}
    </div>
  )
}

export function SummaryClient() {
  const { data: stats, isLoading } = useManageStats()

  if (isLoading || !stats) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-6">
        <Skeleton className="h-24 w-full" />
        <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      </div>
    )
  }

  const done = stats.by_status["검증완료"] ?? 0
  const donePct = stats.total_groups ? Math.round((done / stats.total_groups) * 100) : 0
  const levelClassified =
    stats.total_groups - (stats.by_level["미분류"] ?? 0)
  const levelPct = stats.total_groups
    ? Math.round((levelClassified / stats.total_groups) * 100)
    : 0

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-4">
        <h1 className="rt-display text-xl font-bold tracking-tight">중간보고 요약</h1>
        <p className="text-sm text-muted-foreground">
          입력관리 진행 현황 — 검증 상태·보완 레벨·학습/FAQ 분류·담당자 분포.
        </p>
      </div>

      {/* KPI */}
      <div className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi label="기준 질문" value={String(stats.total_groups)} sub="3주차 고유질문" />
        <Kpi label="검증완료" value={`${donePct}%`} sub={`${done} / ${stats.total_groups}`} />
        <Kpi label="레벨 분류율" value={`${levelPct}%`} sub={`미분류 ${stats.by_level["미분류"] ?? 0}건`} />
        <Kpi
          label="미매칭 응답"
          value={String(stats.unmatched_week2 + stats.unmatched_week1)}
          sub={`2주 ${stats.unmatched_week2} · 1주 ${stats.unmatched_week1}`}
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">검증 상태</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars
              data={ordered(stats.by_status, ["대기", "진행중", "검증완료"])}
              colorOf={(l) => STATUS_COLOR[l] ?? "#1e3a34"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">보완 레벨</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars
              data={ordered(stats.by_level, ["미분류", "0", "1", "2", "3"])}
              colorOf={(l) => LEVEL_COLOR[l] ?? "#9aa39a"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">처리 분류 (학습/FAQ)</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars
              data={ordered(stats.by_disposition, ["학습", "FAQ", "미정"])}
              colorOf={(l) => DISPOSITION_COLOR[l] ?? "#9aa39a"}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">담당자별 배정</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars data={topN(stats.assignee_load, 8)} colorOf={() => "#b08524"} />
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">피드백 유형 태그 (상위 12)</CardTitle>
          </CardHeader>
          <CardContent>
            <Bars data={topN(stats.by_tag, 12)} colorOf={() => "#5e8d80"} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
