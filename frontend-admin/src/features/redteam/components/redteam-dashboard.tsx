"use client"

// 레드팀 피드백 대시보드 — 통계 + 필터 + 마스터(기준질문) / 디테일(주차별 응답·리뷰) 조립
import * as React from "react"
import { useSearchParams } from "next/navigation"
import { ChevronLeft, ChevronRight, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useDebounce } from "@/hooks/use-debounce"
import { CATEGORIES, RISK_LEVELS } from "../constants"
import { useRedteamGroups, useRedteamStats } from "../hooks"
import { useReviewer } from "../use-reviewer"
import type { GroupListParams } from "../types"
import { GroupDetailPanel } from "./group-detail"
import { GroupList } from "./group-list"
import { ReviewerPicker } from "./reviewer-picker"
import { StatsCards } from "./stats-cards"

const ALL = "ALL"
const PAGE_SIZE = 50

export function RedteamDashboard() {
  const reviewer = useReviewer()
  const searchParams = useSearchParams()

  const [category, setCategory] = React.useState(ALL)
  const [risk, setRisk] = React.useState(ALL)
  const [weekPresent, setWeekPresent] = React.useState(ALL)
  const [matchedOnly, setMatchedOnly] = React.useState(false)
  const [search, setSearch] = React.useState("")
  const [page, setPage] = React.useState(1)
  // 보고 드릴다운에서 ?selectedId= 로 진입 시 해당 질문을 초기 선택
  const [selectedId, setSelectedId] = React.useState<number | null>(() => {
    const raw = searchParams.get("selectedId")
    return raw ? Number(raw) : null
  })

  const debouncedSearch = useDebounce(search, 300)

  // 필터 변경 시 1페이지로 리셋
  React.useEffect(() => {
    setPage(1)
  }, [category, risk, weekPresent, matchedOnly, debouncedSearch])

  const params: GroupListParams = {
    category: category === ALL ? undefined : category,
    risk: risk === ALL ? undefined : risk,
    week_present: weekPresent === ALL ? undefined : (Number(weekPresent) as 1 | 2),
    matched_only: matchedOnly || undefined,
    q: debouncedSearch || undefined,
    page,
    page_size: PAGE_SIZE,
  }

  const { data: stats, isLoading: statsLoading } = useRedteamStats()
  const { data, isLoading } = useRedteamGroups(params)

  const groups = data?.groups ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-7 px-6 py-8">
      {/* 헤더 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Review · 3주차 기준
          </p>
          <h1 className="rt-display mt-1 text-3xl font-bold tracking-tight">피드백 검토</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            1·2·3주차 피드백을 한자리에서 검토하고 옳은 답변·주차별 반영여부를 기록합니다.
          </p>
        </div>
        {reviewer.hydrated && (
          <ReviewerPicker
            names={reviewer.names}
            activeIndex={reviewer.activeIndex}
            onSelect={reviewer.selectActive}
            onRename={reviewer.updateName}
          />
        )}
      </div>

      <StatsCards stats={stats} isLoading={statsLoading} reviewerNames={reviewer.names} />

      {/* 필터 바 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 sm:max-w-xs">
          <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="질문 검색..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-8"
          />
        </div>

        <Select value={category} onValueChange={setCategory}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="카테고리" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 카테고리</SelectItem>
            {CATEGORIES.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={risk} onValueChange={setRisk}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="위험도" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 위험도</SelectItem>
            {RISK_LEVELS.map((r) => (
              <SelectItem key={r} value={r}>
                {r}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={weekPresent} onValueChange={setWeekPresent}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="주차 매칭" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>주차 무관</SelectItem>
            <SelectItem value="2">2주차 매칭만</SelectItem>
            <SelectItem value="1">1주차 매칭만</SelectItem>
          </SelectContent>
        </Select>

        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <Switch checked={matchedOnly} onCheckedChange={setMatchedOnly} />
          매칭된 질문만
        </label>
      </div>

      {/* 마스터-디테일 */}
      <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
        {/* 마스터 리스트 */}
        <div className="flex flex-col overflow-hidden rounded-lg border">
          <div className="max-h-[70vh] overflow-auto">
            <GroupList
              groups={groups}
              total={total}
              isLoading={isLoading}
              selectedId={selectedId}
              onSelect={setSelectedId}
              reviewerNames={reviewer.names}
            />
          </div>
          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t bg-muted/30 px-3 py-2 text-xs">
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="size-4" /> 이전
              </Button>
              <span className="tabular-nums text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                다음 <ChevronRight className="size-4" />
              </Button>
            </div>
          )}
        </div>

        {/* 디테일 */}
        <div className="rounded-lg border">
          <GroupDetailPanel
            groupId={selectedId}
            reviewerName={reviewer.activeName}
            reviewerNames={reviewer.names}
          />
        </div>
      </div>
    </div>
  )
}
