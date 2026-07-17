"use client"

// 입력관리 보드 — 필터/검색 + 마스터 리스트(좌) + 상세 편집(우) + 페이지네이션 + 요약 스트립.
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { ChevronLeft, ChevronRight, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AI_AUTO_TAG,
  ASSIGNEES,
  CATEGORIES,
  DISPOSITION_OPTIONS,
  LEVEL_OPTIONS,
  RATING_OPTIONS,
  RISK_LEVELS,
  STATUS_COLOR,
  STATUS_OPTIONS,
} from "../constants"
import { useManageGroups, useManageStats } from "../hooks"
import type { ManageGroupListParams, ManageStatsResponse } from "../types"

function FlowMeter({ stats }: { stats: ManageStatsResponse }) {
  const wait = stats.by_status["대기"] ?? 0
  const prog = stats.by_status["진행중"] ?? 0
  const done = stats.by_status["검증완료"] ?? 0
  const total = Math.max(1, wait + prog + done)
  const seg = [
    { label: "대기", n: wait, c: STATUS_COLOR["대기"] },
    { label: "진행중", n: prog, c: STATUS_COLOR["진행중"] },
    { label: "검증완료", n: done, c: STATUS_COLOR["검증완료"] },
  ]
  return (
    <div className="rounded-lg border bg-card px-4 py-3">
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
        <span className="text-muted-foreground">
          기준 질문 <b className="rtm-mono text-sm text-foreground">{stats.total_groups}</b>
        </span>
        <span className="h-3.5 w-px bg-border" />
        {seg.map((s, i) => (
          <span key={s.label} className="flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: s.c }} />
            <span className="text-muted-foreground">{s.label}</span>
            <b className="rtm-mono text-foreground">{s.n}</b>
            {i < 2 && <span className="text-muted-foreground/40">▸</span>}
          </span>
        ))}
        <span className="ml-auto text-muted-foreground">
          3주차 기준 <b className="rtm-mono text-foreground">{stats.week3_groups}</b> · 1·2주차 전용{" "}
          <b className="rtm-mono text-foreground">{stats.prior_only_groups}</b> · 레벨 미분류{" "}
          <b className="rtm-mono text-foreground">{stats.by_level["미분류"] ?? 0}</b>
        </span>
      </div>
      <div className="flex h-2 overflow-hidden rounded-full bg-muted">
        {seg.map((s) => (
          <div
            key={s.label}
            style={{ width: `${(s.n / total) * 100}%`, background: s.c }}
            title={`${s.label} ${s.n}`}
          />
        ))}
      </div>
    </div>
  )
}
import { ManageDetail } from "./manage-detail"
import { ManageGroupList } from "./manage-group-list"

const ALL = "__all__"
const PAGE_SIZE = 50

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  options: { value: string; label: string }[]
}) {
  return (
    <Select value={value || ALL} onValueChange={(v) => onChange(v === ALL ? "" : v)}>
      <SelectTrigger className="h-8 w-auto min-w-28 text-xs">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ALL}>{placeholder}</SelectItem>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

export function ManageBoard() {
  const searchParams = useSearchParams()
  const initialId = searchParams.get("selectedId")
  const [selectedId, setSelectedId] = React.useState<number | null>(
    initialId ? Number(initialId) : null
  )

  const [rawQ, setRawQ] = React.useState("")
  const [q, setQ] = React.useState("")
  const [status, setStatus] = React.useState("")
  const [level, setLevel] = React.useState("")
  const [disposition, setDisposition] = React.useState("")
  const [category, setCategory] = React.useState("")
  const [risk, setRisk] = React.useState("")
  const [rating, setRating] = React.useState("") // "5"~"1" | "없음" | ""
  const [assignee, setAssignee] = React.useState("")
  const [origin, setOrigin] = React.useState("") // "week1"|"week2"|"week3"|"prior"|"multiweek"|""
  const [aiOnly, setAiOnly] = React.useState(false) // AI 자동분류 항목만
  const [page, setPage] = React.useState(1)

  // 검색 디바운스
  React.useEffect(() => {
    const t = setTimeout(() => {
      setQ(rawQ)
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [rawQ])

  const resetPage = () => setPage(1)
  const onFilter = (setter: (v: string) => void) => (v: string) => {
    setter(v)
    resetPage()
  }

  const params: ManageGroupListParams = {
    q: q || undefined,
    status: status || undefined,
    level: level ? Number(level) : undefined,
    disposition: disposition || undefined,
    category: category || undefined,
    risk: risk || undefined,
    rating: rating || undefined,
    assignee: assignee || undefined,
    tag: aiOnly ? AI_AUTO_TAG : undefined,
    ...(origin === "multiweek"
      ? { multiweek: true }
      : origin === "prior"
        ? { origin: "prior" as const }
        : origin === "week1"
          ? { week_present: 1 as const }
          : origin === "week2"
            ? { week_present: 2 as const }
            : origin === "week3"
              ? { week_present: 3 as const }
              : {}),
    page,
    page_size: PAGE_SIZE,
  }

  const { data, isLoading } = useManageGroups(params)
  const { data: stats } = useManageStats()
  const groups = data?.groups ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const hasFilter =
    q ||
    status ||
    level ||
    disposition ||
    category ||
    risk ||
    rating ||
    assignee ||
    origin ||
    aiOnly
  const clearFilters = () => {
    setRawQ("")
    setQ("")
    setStatus("")
    setLevel("")
    setDisposition("")
    setCategory("")
    setRisk("")
    setRating("")
    setAssignee("")
    setOrigin("")
    setAiOnly(false)
    resetPage()
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      {/* 헤더 + 요약 스트립 */}
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="rtm-display text-xl tracking-tight">피드백 입력관리</h1>
            <p className="text-sm text-muted-foreground">
              전 주차 고유질문을 한 건씩 분류·검증합니다. 3주차 기준 + 1·2주차 전용 질문 전건. 주차
              배지로 어느 주차에 나온 질문인지 표시됩니다.
            </p>
          </div>
        </div>
        {stats && <FlowMeter stats={stats} />}
      </div>

      {/* 필터 바 */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          value={rawQ}
          onChange={(e) => setRawQ(e.target.value)}
          placeholder="질문 검색..."
          className="h-8 w-52 text-xs"
        />
        <FilterSelect
          value={status}
          onChange={onFilter(setStatus)}
          placeholder="상태"
          options={STATUS_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
        />
        <FilterSelect
          value={level}
          onChange={onFilter(setLevel)}
          placeholder="레벨"
          options={LEVEL_OPTIONS.map((o) => ({ value: String(o.value), label: o.label }))}
        />
        <FilterSelect
          value={disposition}
          onChange={onFilter(setDisposition)}
          placeholder="분류"
          options={DISPOSITION_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
        />
        <FilterSelect
          value={category}
          onChange={onFilter(setCategory)}
          placeholder="카테고리"
          options={CATEGORIES.map((c) => ({ value: c, label: c }))}
        />
        <FilterSelect
          value={risk}
          onChange={onFilter(setRisk)}
          placeholder="위험도"
          options={RISK_LEVELS.map((r) => ({ value: r, label: r }))}
        />
        <FilterSelect
          value={rating}
          onChange={onFilter(setRating)}
          placeholder="평점"
          options={RATING_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
        />
        <FilterSelect
          value={assignee}
          onChange={onFilter(setAssignee)}
          placeholder="담당자"
          options={ASSIGNEES.map((a) => ({ value: a, label: a }))}
        />
        <FilterSelect
          value={origin}
          onChange={onFilter(setOrigin)}
          placeholder="주차"
          options={[
            { value: "week1", label: "1주차" },
            { value: "week2", label: "2주차" },
            { value: "week3", label: "3주차 기준" },
            { value: "prior", label: "1·2주차 전용" },
            { value: "multiweek", label: "다주차 중복" },
          ]}
        />
        <span className="mx-0.5 h-5 w-px self-center bg-border" aria-hidden />
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-pressed={aiOnly}
          title="AI가 자동분류한 항목만 보기"
          onClick={() => {
            setAiOnly((v) => !v)
            resetPage()
          }}
          className={cn(
            "h-8 gap-1 px-2.5 text-xs",
            aiOnly
              ? "border-violet-600 bg-violet-600 text-white hover:bg-violet-700 hover:text-white"
              : "text-violet-700 hover:text-violet-800 dark:text-violet-300"
          )}
        >
          <Sparkles className="size-3" aria-hidden />
          AI 자동분류
        </Button>
        {hasFilter && (
          <Button variant="ghost" size="sm" className="h-8 px-2 text-xs" onClick={clearFilters}>
            필터 초기화
          </Button>
        )}
      </div>

      {/* 본문 그리드 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
        <div className="flex flex-col overflow-hidden rounded-lg border">
          <div className="max-h-[72vh] overflow-y-auto">
            <ManageGroupList
              groups={groups}
              total={total}
              isLoading={isLoading}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
          </div>
          <div className="flex items-center justify-between border-t bg-background px-3 py-2 text-xs">
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              <ChevronLeft className="size-3" /> 이전
            </Button>
            <span className="tabular-nums text-muted-foreground">
              {page} / {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              다음 <ChevronRight className="size-3" />
            </Button>
          </div>
        </div>

        <div className="rounded-lg border">
          <ManageDetail groupId={selectedId} />
        </div>
      </div>
    </div>
  )
}
