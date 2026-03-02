"use client"

/**
 * 사용자 관리 페이지.
 * 검색 Input + 플랜 필터 Select → UserTable 조립.
 * 비즈니스 로직은 useUsers 훅과 각 컴포넌트에 위임하고 이 페이지는 상태 조립만 담당.
 */
import * as React from "react"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useUsers } from "@/features/users/hooks"
import { UserTable } from "@/features/users/components/user-table"
import { useDebounce } from "@/hooks/use-debounce"

const PLAN_FILTER_OPTIONS = [
  { label: "전체", value: "ALL" },
  { label: "FREE", value: "FREE" },
  { label: "PRO", value: "PRO" },
] as const

export default function UsersPage() {
  const [searchEmail, setSearchEmail] = React.useState("")
  const [planFilter, setPlanFilter] = React.useState<"ALL" | "FREE" | "PRO">("ALL")

  // 검색어 디바운스 (300ms) — 입력할 때마다 API를 호출하지 않도록
  const debouncedEmail = useDebounce(searchEmail, 300)

  const { data, isLoading } = useUsers({
    email: debouncedEmail || undefined,
    plan_type: planFilter === "ALL" ? undefined : planFilter,
  })

  const users = data?.users ?? []
  const total = data?.total ?? 0

  return (
    <div className="flex flex-col gap-6">
      {/* 페이지 헤더 */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">사용자 관리</h1>
        <p className="text-muted-foreground">
          전체 사용자 수:{" "}
          <span className="font-semibold text-foreground">{total}명</span>
        </p>
      </div>

      {/* 검색 & 필터 */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Input
          placeholder="이메일로 검색..."
          value={searchEmail}
          onChange={(e) => setSearchEmail(e.target.value)}
          className="sm:max-w-xs"
        />
        <Select
          value={planFilter}
          onValueChange={(val) => setPlanFilter(val as typeof planFilter)}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="플랜 필터" />
          </SelectTrigger>
          <SelectContent>
            {PLAN_FILTER_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* 사용자 목록 테이블 */}
      <UserTable users={users} isLoading={isLoading} />
    </div>
  )
}
