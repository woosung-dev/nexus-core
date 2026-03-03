"use client"

import * as React from "react"
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table"
import { Loader2, Plus } from "lucide-react"

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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useBots } from "@/features/bots/hooks"
import {
  useCreateFaq,
  useDeleteFaq,
  useFaqs,
  useUpdateFaq,
} from "@/features/faqs/hooks"
import type { FaqResponse } from "@/features/faqs/types"
import { createFaqColumns } from "./columns"
import { FaqFormDialog } from "./faq-form-dialog"

// ─── FAQ DataTable 컴포넌트 ───────────────────────────────────
export function FaqDataTable() {
  // 봇 목록 (봇 선택 Select용)
  const { data: botsData, isLoading: isBotsLoading } = useBots()
  const bots = botsData?.bots ?? []

  // 선택된 봇 ID
  const [selectedBotId, setSelectedBotId] = React.useState<number | null>(null)

  // 봇 목록 로드 완료 시 첫 번째 봇 자동 선택
  const firstBotId = bots[0]?.id ?? null
  React.useEffect(() => {
    if (firstBotId !== null && selectedBotId === null) {
      setSelectedBotId(firstBotId)
    }
  }, [firstBotId, selectedBotId])

  // FAQ 목록 조회 (선택된 봇 기준)
  const { data: faqsData, isLoading: isFaqsLoading, isError, error } =
    useFaqs(selectedBotId)
  const faqs = faqsData?.faqs ?? []

  // Mutation 훅 — selectedBotId가 null이면 0으로 대체 (실제 호출 시 이미 선택됨)
  const { mutate: createFaq, isPending: isCreating } = useCreateFaq()
  const { mutate: updateFaqMutate, isPending: isUpdating } = useUpdateFaq(
    selectedBotId ?? 0
  )
  const { mutate: deleteFaqMutate, isPending: isDeleting } = useDeleteFaq(
    selectedBotId ?? 0
  )

  // 다이얼로그 상태
  const [dialogOpen, setDialogOpen] = React.useState(false)
  const [editingFaq, setEditingFaq] = React.useState<FaqResponse | null>(null)

  // 테이블 상태
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] =
    React.useState<ColumnFiltersState>([])

  // --- 이벤트 핸들러 ---
  function handleOpenCreate() {
    setEditingFaq(null)
    setDialogOpen(true)
  }

  function handleOpenEdit(faq: FaqResponse) {
    setEditingFaq(faq)
    setDialogOpen(true)
  }

  function handleDelete(id: number) {
    deleteFaqMutate(id)
  }

  function handleFormSubmit(values: {
    question: string
    answer: string
    threshold: number
  }) {
    if (editingFaq) {
      // 수정 모드
      updateFaqMutate(
        { id: editingFaq.id, request: values },
        { onSuccess: () => setDialogOpen(false) }
      )
    } else {
      // 등록 모드
      if (!selectedBotId) return
      createFaq(
        { bot_id: selectedBotId, ...values },
        { onSuccess: () => setDialogOpen(false) }
      )
    }
  }

  // --- 컬럼 생성 (콜백 주입) ---
  const columns: ColumnDef<FaqResponse>[] = React.useMemo(
    () =>
      createFaqColumns({
        onEdit: handleOpenEdit,
        onDelete: handleDelete,
        isDeleting,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [isDeleting]
  )

  // --- 테이블 인스턴스 ---
  const table = useReactTable({
    data: faqs,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: { sorting, columnFilters },
  })

  return (
    <div className="space-y-4">
      {/* 상단: 봇 선택 + 검색 + 추가 버튼 */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          {/* 봇 선택 Select */}
          <Select
            value={selectedBotId ? String(selectedBotId) : ""}
            onValueChange={(val) => setSelectedBotId(Number(val))}
            disabled={isBotsLoading}
          >
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="봇을 선택하세요" />
            </SelectTrigger>
            <SelectContent>
              {bots.map((bot) => (
                <SelectItem key={bot.id} value={String(bot.id)}>
                  {bot.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* 질문 검색 */}
          <Input
            placeholder="질문으로 검색..."
            value={
              (table.getColumn("question")?.getFilterValue() as string) ?? ""
            }
            onChange={(event) =>
              table.getColumn("question")?.setFilterValue(event.target.value)
            }
            className="max-w-sm"
          />
        </div>

        <Button onClick={handleOpenCreate} disabled={!selectedBotId}>
          <Plus className="mr-2 h-4 w-4" />새 FAQ 추가
        </Button>
      </div>

      {/* 봇 미선택 안내 */}
      {!selectedBotId && !isBotsLoading && (
        <div className="flex h-32 items-center justify-center rounded-md border border-dashed text-muted-foreground">
          봇을 먼저 선택해 주세요.
        </div>
      )}

      {/* 테이블 */}
      {selectedBotId && (
        <>
          <div className="overflow-hidden rounded-md border">
            <Table>
              <TableHeader>
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => (
                      <TableHead key={header.id}>
                        {header.isPlaceholder
                          ? null
                          : flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                      </TableHead>
                    ))}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody>
                {/* 로딩 상태 */}
                {isFaqsLoading ? (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center"
                    >
                      <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                    </TableCell>
                  </TableRow>
                ) : isError ? (
                  /* 에러 상태 */
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center text-destructive"
                    >
                      데이터를 불러오는 데 실패했습니다.{" "}
                      {error instanceof Error ? `(${error.message})` : ""}
                    </TableCell>
                  </TableRow>
                ) : table.getRowModel().rows?.length ? (
                  table.getRowModel().rows.map((row) => (
                    <TableRow
                      key={row.id}
                      data-state={row.getIsSelected() && "selected"}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <TableCell key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center"
                    >
                      등록된 FAQ가 없습니다.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* 페이지네이션 */}
          <div className="flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              이전
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              다음
            </Button>
          </div>
        </>
      )}

      {/* FAQ 등록/수정 다이얼로그 */}
      <FaqFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initialData={editingFaq}
        onSubmit={handleFormSubmit}
        isPending={isCreating || isUpdating}
      />
    </div>
  )
}
