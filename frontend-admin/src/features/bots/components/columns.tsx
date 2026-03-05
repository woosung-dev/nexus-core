"use client"

import { ColumnDef } from "@tanstack/react-table"
import { ArrowUpDown, MoreHorizontal, Pencil } from "lucide-react"
import { useRouter } from "next/navigation"

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
import { useDeleteBot } from "@/features/bots/hooks"
import type { BotResponse } from "@/features/bots/types"

// --- 삭제 액션 셀 (훅 사용을 위해 별도 컴포넌트로 분리) ---
function BotActionCell({ bot }: { bot: BotResponse }) {
  const router = useRouter()
  const { mutate: deleteBot, isPending } = useDeleteBot()

  function handleDelete() {
    if (confirm(`'${bot.name}' 봇을 삭제하시겠습니까?`)) {
      deleteBot(bot.id)
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
          onClick={() => navigator.clipboard.writeText(String(bot.id))}
        >
          ID 복사
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => router.push(`/bots/${bot.id}/edit`)}
          className="gap-2"
        >
          <Pencil className="h-3.5 w-3.5" />
          수정
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={handleDelete}
          disabled={isPending || !bot.is_active}
          className="text-destructive"
        >
          {isPending ? "처리 중..." : bot.is_active ? "비활성화 (삭제)" : "비활성 상태"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// --- 봇 테이블 컬럼 정의 ---
export const columns: ColumnDef<BotResponse>[] = [
  {
    accessorKey: "name",
    header: ({ column }) => (
      <Button
        variant="ghost"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        봇 이름
        <ArrowUpDown className="ml-2 h-4 w-4" />
      </Button>
    ),
    cell: ({ row }) => {
      const isActive = row.original.is_active
      return (
        <div className="flex items-center gap-2">
          <span className={`font-medium ${!isActive ? "text-muted-foreground line-through opacity-70" : ""}`}>
            {row.getValue("name")}
          </span>
          {!isActive && (
            <Badge variant="destructive" className="ml-2 h-5 text-[10px] px-1.5">비활성</Badge>
          )}
        </div>
      )
    },
  },
  {
    accessorKey: "description",
    header: "설명",
    cell: ({ row }) => {
      const desc = row.getValue("description") as string | null
      return (
        <div className="max-w-[300px] truncate text-muted-foreground">
          {desc || "-"}
        </div>
      )
    },
  },
  {
    accessorKey: "tags",
    header: "태그",
    cell: ({ row }) => {
      const tags = row.getValue("tags") as string[]
      return (
        <div className="flex flex-wrap gap-1">
          {tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="text-xs">
              {tag}
            </Badge>
          ))}
        </div>
      )
    },
  },
  {
    accessorKey: "llm_model",
    header: "LLM 모델",
    cell: ({ row }) => (
      <Badge variant="outline">{row.getValue("llm_model")}</Badge>
    ),
  },
  {
    accessorKey: "is_verified",
    header: "상태",
    cell: ({ row }) => {
      const isVerified = row.getValue("is_verified") as boolean
      return (
        <Badge variant={isVerified ? "default" : "secondary"}>
          {isVerified ? "인증됨" : "미인증"}
        </Badge>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => <BotActionCell bot={row.original} />,
  },
]
