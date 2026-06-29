"use client"

// 레드팀 대시보드 상단 KPI 카드 — 총 질문/카테고리·위험도 분포/매칭 커버리지/리뷰 진행률
import * as React from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { RISK_LEVELS } from "../constants"
import type { StatsResponse } from "../types"

function DistBar({
  items,
  total,
}: {
  items: { label: string; value: number; className?: string }[]
  total: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {items.map((it) => (
        <div key={it.label} className="flex items-center gap-2 text-xs">
          <span className="w-24 shrink-0 truncate text-muted-foreground" title={it.label}>
            {it.label}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
            <div
              className={it.className ?? "bg-primary"}
              style={{ width: total ? `${Math.round((it.value / total) * 100)}%` : "0%", height: "100%" }}
            />
          </div>
          <span className="w-8 shrink-0 text-right tabular-nums font-medium">{it.value}</span>
        </div>
      ))}
    </div>
  )
}

export function StatsCards({
  stats,
  isLoading,
  reviewerNames,
}: {
  stats?: StatsResponse
  isLoading: boolean
  reviewerNames: string[]
}) {
  if (isLoading || !stats) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-16 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const riskColors: Record<string, string> = {
    없음: "bg-[var(--rt-sage)]",
    하: "bg-[var(--rt-brass)]",
    중: "bg-[var(--rt-amber)]",
    상: "bg-[var(--rt-garnet)]",
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {/* 총 질문 / 응답 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            기준 질문 (3주차)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold tabular-nums">{stats.total_groups}</div>
          <p className="mt-1 text-xs text-muted-foreground">
            전체 응답 {stats.total_responses.toLocaleString()}건
          </p>
        </CardContent>
      </Card>

      {/* 카테고리 분포 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            카테고리 분포
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DistBar
            total={stats.total_groups}
            items={Object.entries(stats.by_category)
              .sort((a, b) => b[1] - a[1])
              .map(([label, value]) => ({ label, value }))}
          />
        </CardContent>
      </Card>

      {/* 위험도 분포 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            위험도 분포
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DistBar
            total={stats.total_groups}
            items={RISK_LEVELS.map((label) => ({
              label,
              value: stats.by_risk[label] ?? 0,
              className: riskColors[label],
            }))}
          />
        </CardContent>
      </Card>

      {/* 매칭 + 리뷰 진행률 */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            매칭 · 리뷰 진행
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">2주차 매칭</span>
            <span className="font-semibold tabular-nums">
              {stats.matched_week2} / {stats.total_groups}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">1주차 매칭</span>
            <span className="font-semibold tabular-nums">
              {stats.matched_week1} / {stats.total_groups}
            </span>
          </div>
          <div className="mt-1 border-t pt-2">
            {reviewerNames.map((name) => (
              <div key={name} className="flex justify-between text-xs">
                <span className="truncate text-muted-foreground" title={name}>
                  {name}
                </span>
                <span className="font-medium tabular-nums">
                  {stats.review_progress[name] ?? 0} 작성
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
