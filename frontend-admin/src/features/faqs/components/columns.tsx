"use client"

import { ColumnDef } from "@tanstack/react-table"
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
import type { FaqResponse } from "@/features/faqs/types"

// --- 액션 셀 Props ---
interface FaqActionCellProps {
  faq: FaqResponse
  onEdit: (faq: FaqResponse) => void
  onDelete: (id: number) => void
  isDeleting: boolean
}

// --- 액션 셀 컴포넌트 (훅 의존 없이 콜백으로 처리) ---
function FaqActionCell({ faq, onEdit, onDelete, isDeleting }: FaqActionCellProps) {
  function handleDelete() {
    if (confirm(`'${faq.question}' FAQ를 삭제하시겠습니까?`)) {
      onDelete(faq.id)
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
        <DropdownMenuItem
          onClick={() => onEdit(faq)}
          className="gap-2"
        >
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

// --- 컬럼 정의 팩토리 (콜백 주입을 위해 함수 형태) ---
export function createFaqColumns({
  onEdit,
  onDelete,
  isDeleting,
}: {
  onEdit: (faq: FaqResponse) => void
  onDelete: (id: number) => void
  isDeleting: boolean
}): ColumnDef<FaqResponse>[] {
  return [
    {
      accessorKey: "question",
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
        >
          질문
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="max-w-[280px] font-medium">
          {row.getValue("question")}
        </div>
      ),
    },
    {
      accessorKey: "answer",
      header: "답변",
      cell: ({ row }) => {
        const answer = row.getValue("answer") as string
        return (
          <div className="max-w-[320px] truncate text-muted-foreground">
            {answer || "-"}
          </div>
        )
      },
    },
    {
      accessorKey: "threshold",
      header: "유사도 임계값",
      cell: ({ row }) => {
        const threshold = row.getValue("threshold") as number
        return (
          <Badge variant="outline" className="font-mono">
            {threshold.toFixed(2)}
          </Badge>
        )
      },
    },
    {
      accessorKey: "is_active",
      header: "상태",
      cell: ({ row }) => {
        const isActive = row.getValue("is_active") as boolean
        return (
          <Badge variant={isActive ? "default" : "secondary"}>
            {isActive ? "활성" : "비활성"}
          </Badge>
        )
      },
    },
    {
      id: "actions",
      cell: ({ row }) => (
        <FaqActionCell
          faq={row.original}
          onEdit={onEdit}
          onDelete={onDelete}
          isDeleting={isDeleting}
        />
      ),
    },
  ]
}
