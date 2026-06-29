"use client"

// 보고용 차트 묶음 — recharts 기반. 위험도·품질 / 주차별 추이 / 봇 비교.
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ImageDown } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  BOT_COLOR,
  BOT_FULL_LABEL,
  CATEGORY_COLOR,
  RISK_COLOR,
  WEEK_COLOR,
} from "../constants"
import type { ReportResponse } from "../types"
import { downloadSvgAsPng } from "./export-utils"

const TOOLTIP_STYLE = {
  background: "var(--background)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--foreground)",
}
const AXIS = { fontSize: 11, fill: "var(--muted-foreground)" }
const GRID = "var(--border)"

export function ChartCard({
  title,
  description,
  children,
  className,
  exportName,
}: {
  title: string
  description?: string
  children: React.ReactNode
  className?: string
  exportName?: string
}) {
  const bodyRef = React.useRef<HTMLDivElement>(null)
  const handleExport = () => {
    const svg = bodyRef.current?.querySelector("svg")
    if (svg) downloadSvgAsPng(svg as SVGSVGElement, `${exportName}.png`)
  }
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="rt-display text-base font-bold text-[var(--rt-pine)]">{title}</CardTitle>
            {description && <CardDescription className="text-xs">{description}</CardDescription>}
          </div>
          {exportName && (
            <button
              onClick={handleExport}
              title="PNG로 저장"
              aria-label={`${title} 차트 PNG로 저장`}
              className="shrink-0 rounded-md border border-border p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground print:hidden"
            >
              <ImageDown className="size-3.5" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent ref={bodyRef}>{children}</CardContent>
    </Card>
  )
}

// 위험도 분포 도넛
export function RiskDonut({
  data,
  onSlice,
}: {
  data: ReportResponse["risk_distribution"]
  onSlice?: (level: string) => void
}) {
  const total = data.reduce((s, d) => s + d.count, 0)
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="level"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={2}
          onClick={(d: { level?: string }) => d?.level && onSlice?.(d.level)}
          className={onSlice ? "cursor-pointer" : undefined}
        >
          {data.map((d) => (
            <Cell key={d.level} fill={RISK_COLOR[d.level]} />
          ))}
          <LabelList
            dataKey="count"
            position="outside"
            style={{ fontSize: 11, fill: "var(--foreground)" }}
          />
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number, n) => [`${v}건 (${Math.round((v / total) * 100)}%)`, `위험 ${n}`]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// 봇 선호 (3주차 적절챗봇) 도넛
export function BotPreferencePie({ data }: { data: ReportResponse["bot_preference"] }) {
  const total = data.reduce((s, d) => s + d.count, 0)
  const withLabel = data.map((d) => ({ ...d, label: BOT_FULL_LABEL[d.bot] ?? d.bot }))
  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={withLabel} dataKey="count" nameKey="label" innerRadius={55} outerRadius={85} paddingAngle={2}>
          {withLabel.map((d) => (
            <Cell key={d.bot} fill={BOT_COLOR[d.bot]} />
          ))}
          <LabelList
            dataKey="count"
            position="outside"
            style={{ fontSize: 11, fill: "var(--foreground)" }}
          />
        </Pie>
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(v: number, n) => [`${v}건 (${Math.round((v / total) * 100)}%)`, n]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  )
}

// 평점 추이 (1·3주차 평균, 2주차 미측정)
export function RatingTrendLine({ data }: { data: ReportResponse["rating_trend"] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
        <XAxis dataKey="label" tick={AXIS} />
        <YAxis domain={[0, 5]} tick={AXIS} />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          formatter={(value, _name, item: { payload?: { count?: number } }) => {
            const v = value as number | null
            return v == null
              ? ["미측정", "평균 평점"]
              : [`${v} / 5 (${item?.payload?.count ?? 0}건)`, "평균 평점"]
          }}
        />
        <Line
          type="monotone"
          dataKey="avg"
          stroke="#8b5cf6"
          strokeWidth={2.5}
          connectNulls
          dot={{ r: 5, fill: "#8b5cf6" }}
        >
          <LabelList
            dataKey="avg"
            position="top"
            formatter={(v: unknown) => (v == null ? "" : String(v))}
            style={{ fontSize: 11, fill: "var(--foreground)", fontWeight: 600 }}
          />
        </Line>
      </LineChart>
    </ResponsiveContainer>
  )
}

// 평점 분포 (1주차 vs 3주차)
export function RatingByWeekBar({ data }: { data: ReportResponse["rating_by_week"] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey="rating" tick={AXIS} tickFormatter={(v) => `${v}점`} />
        <YAxis tick={AXIS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="week1" name="1주차" fill={WEEK_COLOR["1주차"]} radius={[3, 3, 0, 0]} />
        <Bar dataKey="week3" name="3주차" fill={WEEK_COLOR["3주차"]} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// 카테고리별 위험도 (가로 누적)
export function RiskByCategoryBar({ data }: { data: ReportResponse["risk_by_category"] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS} />
        <YAxis type="category" dataKey="category" tick={AXIS} width={110} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {(["없음", "하", "중", "상"] as const).map((lv) => (
          <Bar key={lv} dataKey={lv} name={lv} stackId="risk" fill={RISK_COLOR[lv]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

// 카테고리별 봇 선호 (가로 누적)
export function BotByCategoryBar({ data }: { data: ReportResponse["bot_by_category"] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS} />
        <YAxis type="category" dataKey="category" tick={AXIS} width={110} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="C" name={BOT_FULL_LABEL.C} stackId="bot" fill={BOT_COLOR.C} />
        <Bar dataKey="D" name={BOT_FULL_LABEL.D} stackId="bot" fill={BOT_COLOR.D} />
        <Bar dataKey="부적절" name="둘 다 부적절" stackId="bot" fill={BOT_COLOR.부적절} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// 카테고리 분포 (세로 막대)
export function CategoryBar({
  data,
  onBar,
}: {
  data: ReportResponse["category_distribution"]
  onBar?: (category: string) => void
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey="category" tick={{ ...AXIS, fontSize: 10 }} interval={0} angle={-12} textAnchor="end" height={50} />
        <YAxis tick={AXIS} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`${v}건`, "질문 수"]} />
        <Bar
          dataKey="count"
          radius={[3, 3, 0, 0]}
          onClick={(d: { category?: string }) => d?.category && onBar?.(d.category)}
          className={onBar ? "cursor-pointer" : undefined}
        >
          {data.map((d) => (
            <Cell key={d.category} fill={CATEGORY_COLOR[d.category] ?? "#94a3b8"} />
          ))}
          <LabelList dataKey="count" position="top" style={{ fontSize: 11, fill: "var(--foreground)" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// 위험도 × 카테고리 히트맵 — 셀 클릭 시 드릴다운
export function RiskCategoryHeatmap({
  data,
  onCell,
}: {
  data: ReportResponse["risk_by_category"]
  onCell?: (risk: string, category: string) => void
}) {
  const levels = ["상", "중", "하", "없음"] as const
  const max = Math.max(1, ...data.flatMap((row) => levels.map((lv) => row[lv])))
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-1 text-xs">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left font-medium text-muted-foreground">카테고리</th>
            {levels.map((lv) => (
              <th key={lv} className="px-2 py-1 text-center font-medium text-muted-foreground">
                {lv}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.category}>
              <td className="px-2 py-1 text-left text-muted-foreground">{row.category}</td>
              {levels.map((lv) => {
                const v = row[lv]
                const intensity = v === 0 ? 0 : 0.15 + 0.85 * (v / max)
                return (
                  <td key={lv} className="p-0">
                    <button
                      type="button"
                      disabled={v === 0 || !onCell}
                      onClick={() => onCell?.(lv, row.category)}
                      className="flex h-9 w-full items-center justify-center rounded font-semibold transition-opacity enabled:hover:opacity-80 disabled:cursor-default"
                      style={{
                        background: v === 0 ? "var(--muted)" : RISK_COLOR[lv],
                        opacity: v === 0 ? 0.4 : intensity,
                        color: v === 0 ? "var(--muted-foreground)" : "#fff",
                      }}
                    >
                      {v || "·"}
                    </button>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// 개선 추적 — 개선/정체/악화 분포 (세로 막대)
export function ImprovementBar({
  data,
}: {
  data: { name: string; value: number; color: string }[]
}) {
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 16, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey="name" tick={AXIS} />
        <YAxis tick={AXIS} allowDecimals={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v: number) => [`${v}개 질문`, ""]} />
        <Bar dataKey="value" radius={[3, 3, 0, 0]}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
          <LabelList dataKey="value" position="top" style={{ fontSize: 11, fill: "var(--foreground)" }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// 반영 현황 — 위험도별 반영/미반영/보류 (가로 누적)
export function ReflectByRiskBar({ data }: { data: ReportResponse["reflect_by_risk"] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 46)}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
        <XAxis type="number" tick={AXIS} allowDecimals={false} />
        <YAxis type="category" dataKey="risk" tick={AXIS} width={48} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="reflect" name="반영" stackId="r" fill="#1e3a34" />
        <Bar dataKey="skip" name="미반영" stackId="r" fill="#9aa39a" />
        <Bar dataKey="pending" name="보류" stackId="r" fill="#c2611f" />
      </BarChart>
    </ResponsiveContainer>
  )
}
