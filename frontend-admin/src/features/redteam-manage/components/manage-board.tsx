"use client"

// 입력관리 보드 — 필터/검색 + 마스터 리스트(좌) + 상세 편집(우) + 페이지네이션 + 요약 스트립.
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  CATEGORIES,
  DISPOSITION_OPTIONS,
  LEVEL_OPTIONS,
  RISK_LEVELS,
  STATUS_OPTIONS,
} from "../constants"
import { useManageGroups, useManageStats } from "../hooks"
import type { ManageGroupListParams } from "../types"
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
    page,
    page_size: PAGE_SIZE,
  }

  const { data, isLoading } = useManageGroups(params)
  const { data: stats } = useManageStats()
  const groups = data?.groups ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  const hasFilter = q || status || level || disposition || category || risk
  const clearFilters = () => {
    setRawQ("")
    setQ("")
    setStatus("")
    setLevel("")
    setDisposition("")
    setCategory("")
    setRisk("")
    resetPage()
  }

  return (
    <div className="mx-auto max-w-7xl px-6 py-6">
      {/* 헤더 + 요약 스트립 */}
      <div className="mb-4 flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="rt-display text-xl font-bold tracking-tight">피드백 입력관리</h1>
            <p className="text-sm text-muted-foreground">
              3주차 기준 질문을 한 건씩 분류·검증하고 상태·레벨·모범답변을 기록합니다.
            </p>
          </div>
        </div>
        {stats && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg border bg-card px-3 py-2 text-xs text-muted-foreground">
            <span>
              기준 질문 <b className="text-foreground">{stats.total_groups}</b>
            </span>
            <span className="text-border">·</span>
            <span>
              대기 <b className="text-foreground">{stats.by_status["대기"] ?? 0}</b> / 진행중{" "}
              <b className="text-foreground">{stats.by_status["진행중"] ?? 0}</b> / 검증완료{" "}
              <b className="text-emerald-600">{stats.by_status["검증완료"] ?? 0}</b>
            </span>
            <span className="text-border">·</span>
            <span>
              레벨 미분류 <b className="text-foreground">{stats.by_level["미분류"] ?? 0}</b>
            </span>
            <span className="text-border">·</span>
            <span>
              미매칭 2주 <b className="text-foreground">{stats.unmatched_week2}</b> · 1주{" "}
              <b className="text-foreground">{stats.unmatched_week1}</b>
            </span>
          </div>
        )}
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
