// 선택된 범위의 용어집을 검색하고 관리하는 데이터 테이블입니다.
"use client"

import * as React from "react"
import {
  type ColumnDef,
  type ColumnFiltersState,
  type SortingState,
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
  useCreateGlossary,
  useDeleteGlossary,
  useGlossary,
  useUpdateGlossary,
} from "@/features/glossary/hooks"
import { type GlossaryFormValues } from "@/features/glossary/schemas"
import type { Glossary } from "@/features/glossary/types"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { createGlossaryColumns } from "./columns"
import { GlossaryFormDialog } from "./glossary-form-dialog"

interface GlossaryDataTableProps {
  botId: number | null
}

export function GlossaryDataTable({ botId }: GlossaryDataTableProps) {
  const { data, isLoading, isError, error } = useGlossary(botId)
  const terms = React.useMemo(() => data?.terms ?? [], [data?.terms])
  const { mutate: createGlossary, isPending: isCreating, error: createError } =
    useCreateGlossary()
  const { mutate: updateGlossary, isPending: isUpdating, error: updateError } =
    useUpdateGlossary()
  const { mutate: deleteGlossary, isPending: isDeleting, error: deleteError } =
    useDeleteGlossary()
  const [dialogOpen, setDialogOpen] = React.useState(false)
  const [editingGlossary, setEditingGlossary] = React.useState<Glossary | null>(null)
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])

  const handleOpenCreate = React.useCallback(() => {
    setEditingGlossary(null)
    setDialogOpen(true)
  }, [])

  const handleOpenEdit = React.useCallback((glossary: Glossary) => {
    setEditingGlossary(glossary)
    setDialogOpen(true)
  }, [])

  const handleDelete = React.useCallback(
    (id: number) => deleteGlossary(id),
    [deleteGlossary]
  )

  const handleFormSubmit = React.useCallback(
    (values: GlossaryFormValues) => {
      const request = {
        term: values.term,
        aliases: values.aliases,
        definition: values.definition,
        priority: values.priority,
        threshold: values.threshold,
      }

      if (editingGlossary) {
        updateGlossary(
          { id: editingGlossary.id, request },
          { onSuccess: () => setDialogOpen(false) }
        )
      } else {
        createGlossary(
          {
            ...request,
            ...(values.scope === "bot" ? { bot_id: botId! } : {}),
          },
          { onSuccess: () => setDialogOpen(false) }
        )
      }
    },
    [botId, createGlossary, editingGlossary, updateGlossary]
  )

  const columns: ColumnDef<Glossary>[] = React.useMemo(
    () =>
      createGlossaryColumns({
        onEdit: handleOpenEdit,
        onDelete: handleDelete,
        isDeleting,
      }),
    [handleDelete, handleOpenEdit, isDeleting]
  )

  const table = useReactTable({
    data: terms,
    columns,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: { sorting, columnFilters },
  })
  const mutationError = createError ?? updateError ?? deleteError

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Input
          placeholder="용어로 검색..."
          value={(table.getColumn("term")?.getFilterValue() as string) ?? ""}
          onChange={(event) =>
            table.getColumn("term")?.setFilterValue(event.target.value)
          }
          className="max-w-sm"
        />
        <Button onClick={handleOpenCreate}>
          <Plus className="mr-2 h-4 w-4" />새 용어
        </Button>
      </div>

      {mutationError instanceof Error && (
        <p className="text-sm text-destructive">저장에 실패했습니다. {mutationError.message}</p>
      )}

      <div className="overflow-hidden rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  <Loader2 className="mx-auto h-6 w-6 animate-spin text-muted-foreground" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-destructive">
                  데이터를 불러오는 데 실패했습니다. {error instanceof Error ? `(${error.message})` : ""}
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  등록된 용어가 없습니다.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

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

      <GlossaryFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        initialData={editingGlossary}
        selectedBotIdForCreate={botId}
        onSubmit={handleFormSubmit}
        isPending={isCreating || isUpdating}
      />
    </div>
  )
}
