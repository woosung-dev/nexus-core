"use client"

// 미분류 큐 — 어떤 3주차 기준질문에도 연결되지 않은 1·2주차 응답. 검색해서 그룹에 연결한다.
import * as React from "react"
import { Link2, Loader2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import { useLinkUnmatched, useManageGroups, useUnmatched } from "../hooks"
import type { UnmatchedItem } from "../types"

const ALL = "__all__"
const PAGE_SIZE = 50

function LinkDialog({
  target,
  onClose,
}: {
  target: UnmatchedItem | null
  onClose: () => void
}) {
  const [rawQ, setRawQ] = React.useState("")
  const [q, setQ] = React.useState("")
  const link = useLinkUnmatched()

  React.useEffect(() => {
    const t = setTimeout(() => setQ(rawQ), 300)
    return () => clearTimeout(t)
  }, [rawQ])

  // 다이얼로그 열릴 때 검색어를 응답 질문으로 시드
  React.useEffect(() => {
    if (target) {
      setRawQ(target.question.slice(0, 16))
      setQ(target.question.slice(0, 16))
    }
  }, [target])

  const { data, isLoading } = useManageGroups({ q: q || undefined, page_size: 20 })
  const groups = data?.groups ?? []

  return (
    <Dialog open={target !== null} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-base">기준 질문에 연결</DialogTitle>
        </DialogHeader>
        {target && (
          <div className="rounded-md border bg-muted/30 p-2 text-xs">
            <Badge variant="outline" className="mr-1.5 text-[10px]">
              {target.week}주차
            </Badge>
            {target.question}
          </div>
        )}
        <Input
          value={rawQ}
          onChange={(e) => setRawQ(e.target.value)}
          placeholder="연결할 3주차 기준 질문 검색..."
          className="h-8 text-xs"
        />
        <div className="max-h-72 overflow-y-auto">
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : groups.length === 0 ? (
            <p className="py-6 text-center text-xs text-muted-foreground">검색 결과가 없습니다.</p>
          ) : (
            <ul className="flex flex-col gap-1.5">
              {groups.map((g) => (
                <li
                  key={g.id}
                  className="flex items-center gap-2 rounded-md border p-2 text-xs"
                >
                  <span className="line-clamp-2 flex-1">{g.question}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-7 shrink-0 px-2"
                    disabled={link.isPending}
                    onClick={() =>
                      target &&
                      link.mutate(
                        { groupId: g.id, responseId: target.id, action: "confirm" },
                        { onSuccess: onClose }
                      )
                    }
                  >
                    {link.isPending ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      <Link2 className="size-3" />
                    )}
                    연결
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function UnmatchedClient() {
  const [week, setWeek] = React.useState("")
  const [rawQ, setRawQ] = React.useState("")
  const [q, setQ] = React.useState("")
  const [page, setPage] = React.useState(1)
  const [target, setTarget] = React.useState<UnmatchedItem | null>(null)

  React.useEffect(() => {
    const t = setTimeout(() => {
      setQ(rawQ)
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [rawQ])

  const { data: rows, isLoading } = useUnmatched({
    week: week ? Number(week) : undefined,
    q: q || undefined,
    page,
    page_size: PAGE_SIZE,
  })
  const items = rows ?? []
  const fullPage = items.length === PAGE_SIZE

  return (
    <div className="mx-auto max-w-5xl px-6 py-6">
      <div className="mb-4">
        <h1 className="rt-display text-xl font-bold tracking-tight">미분류 큐</h1>
        <p className="text-sm text-muted-foreground">
          3주차 기준 질문에 매칭되지 않은 1·2주차 응답입니다. 동일 질문이면 기준 질문에 연결합니다.
        </p>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Input
          value={rawQ}
          onChange={(e) => setRawQ(e.target.value)}
          placeholder="질문 검색..."
          className="h-8 w-60 text-xs"
        />
        <Select
          value={week || ALL}
          onValueChange={(v) => {
            setWeek(v === ALL ? "" : v)
            setPage(1)
          }}
        >
          <SelectTrigger className="h-8 w-28 text-xs">
            <SelectValue placeholder="주차" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>전체 주차</SelectItem>
            <SelectItem value="2">2주차</SelectItem>
            <SelectItem value="1">1주차</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">주차</TableHead>
              <TableHead>질문</TableHead>
              <TableHead className="w-24">제출자</TableHead>
              <TableHead className="w-36">카테고리</TableHead>
              <TableHead className="w-24 text-right">연결</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Skeleton className="h-24 w-full" />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="py-10 text-center text-sm text-muted-foreground">
                  미분류 응답이 없습니다.
                </TableCell>
              </TableRow>
            ) : (
              items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    <Badge variant="outline" className="text-[10px]">
                      {r.week}주차
                    </Badge>
                  </TableCell>
                  <TableCell className="text-sm">{r.question}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.submitter ?? "익명"}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {r.category ?? "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 px-2 text-xs"
                      onClick={() => setTarget(r)}
                    >
                      <Link2 className="size-3" /> 연결
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">페이지 {page}</span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            이전
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2"
            disabled={!fullPage}
            onClick={() => setPage((p) => p + 1)}
          >
            다음
          </Button>
        </div>
      </div>

      <LinkDialog target={target} onClose={() => setTarget(null)} />
    </div>
  )
}
