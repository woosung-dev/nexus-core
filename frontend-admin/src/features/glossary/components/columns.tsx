// 용어집 목록 테이블의 컬럼과 행 작업을 정의합니다.
"use client"

import type { ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown, MoreHorizontal, Pencil, Trash2 } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Glossary } from "@/features/glossary/types"

interface GlossaryActionCellProps {
  glossary: Glossary
  onEdit: (glossary: Glossary) => void
  onDelete: (id: number) => void
  isDeleting: boolean
}

function GlossaryActionCell({
  glossary,
  onEdit,
  onDelete,
  isDeleting,
}: GlossaryActionCellProps) {
  function handleDelete() {
    if (confirm(`'${glossary.term}' 용어를 삭제하시겠습니까?`)) {
      onDelete(glossary.id)
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="h-8 w-8 p-0">
          <span className="sr-only">메뉴 열기</span>
          <MoreHorizontal className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>작업</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => onEdit(glossary)} className="gap-2">
          <Pencil className="h-3.5 w-3.5" />
          수정
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleDelete}
          disabled={isDeleting}
          className="text-destructive gap-2"
        >
          <Trash2 className="h-3.5 w-3.5" />
          {isDeleting ? "삭제 중..." : "삭제"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export function createGlossaryColumns({
  onEdit,
  onDelete,
  isDeleting,
}: {
  onEdit: (glossary: Glossary) => void
  onDelete: (id: number) => void
  isDeleting: boolean
}): ColumnDef<Glossary>[] {
  return [
    {
      accessorKey: "term",
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          용어
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="max-w-[180px] font-medium">{row.getValue("term")}</div>
      ),
    },
    {
      accessorKey: "aliases",
      header: "동의어",
      cell: ({ row }) => {
        const aliases = row.getValue("aliases") as string[]
        return <div className="max-w-[180px] truncate">{aliases.join(", ") || "-"}</div>
      },
    },
    {
      accessorKey: "definition",
      header: "정의",
      cell: ({ row }) => (
        <div className="max-w-[320px] truncate text-muted-foreground">
          {row.getValue("definition") || "-"}
        </div>
      ),
    },
    {
      id: "scope",
      header: "범위",
      cell: ({ row }) => (
        <Badge variant={row.original.bot_id ? "secondary" : "default"}>
          {row.original.bot_id ? "봇" : "전역"}
        </Badge>
      ),
    },
    {
      accessorKey: "priority",
      header: "우선순위",
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <GlossaryActionCell
          glossary={row.original}
          onEdit={onEdit}
          onDelete={onDelete}
          isDeleting={isDeleting}
        />
      ),
    },
  ]
}
