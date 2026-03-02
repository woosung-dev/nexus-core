"use client"

/**
 * 사용자 목록 Data Table 컴포넌트.
 * 아바타, 이메일, 플랜, 가입일, 상태, 액션 컬럼을 표시한다.
 */
import * as React from "react"
import { Loader2, Pencil, UserX } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useDeactivateUser } from "@/features/users/hooks"
import { UserRoleBadge } from "./user-role-badge"
import { UserStatusBadge } from "./user-status-badge"
import { UserEditDialog } from "./user-edit-dialog"
import type { UserResponse } from "@/features/users/types"

interface UserTableProps {
  users: UserResponse[]
  isLoading: boolean
}

// 이메일 첫 글자로 Avatar Fallback 텍스트 생성
function getInitials(email: string): string {
  return email[0]?.toUpperCase() ?? "U"
}

// 날짜 포맷 변환
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
  })
}

// --- 액션 셀 (훅 사용을 위해 별도 컴포넌트로 분리) ---
function UserActionCell({ user }: { user: UserResponse }) {
  const [editOpen, setEditOpen] = React.useState(false)
  const { mutate: deactivate, isPending } = useDeactivateUser()

  function handleDeactivate() {
    if (confirm(`'${user.email}' 사용자를 비활성화하시겠습니까?`)) {
      deactivate(user.id)
    }
  }

  return (
    <>
      <div className="flex items-center gap-1">
        {/* 수정 */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0"
          onClick={() => setEditOpen(true)}
        >
          <Pencil className="h-4 w-4" />
          <span className="sr-only">수정</span>
        </Button>

        {/* 비활성화 */}
        <Button
          variant="ghost"
          size="sm"
          className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
          onClick={handleDeactivate}
          disabled={isPending || !user.is_active}
        >
          {isPending
            ? <Loader2 className="h-4 w-4 animate-spin" />
            : <UserX className="h-4 w-4" />
          }
          <span className="sr-only">비활성화</span>
        </Button>
      </div>

      {/* 수정 Dialog */}
      <UserEditDialog user={user} open={editOpen} onOpenChange={setEditOpen} />
    </>
  )
}

// --- 사용자 목록 테이블 ---
export function UserTable({ users, isLoading }: UserTableProps) {
  return (
    <div className="overflow-hidden rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[48px]" />
            <TableHead>이메일</TableHead>
            <TableHead className="w-[100px]">플랜</TableHead>
            <TableHead className="w-[130px]">가입일</TableHead>
            <TableHead className="w-[100px]">상태</TableHead>
            <TableHead className="w-[80px]">액션</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* 로딩 */}
          {isLoading && (
            <TableRow>
              <TableCell colSpan={6} className="h-32 text-center">
                <Loader2 className="mx-auto h-5 w-5 animate-spin text-muted-foreground" />
              </TableCell>
            </TableRow>
          )}

          {/* 데이터 */}
          {!isLoading && users.map((user) => (
            <TableRow key={user.id}>
              {/* 아바타 */}
              <TableCell>
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user.avatar_url ?? undefined} alt={user.email} />
                  <AvatarFallback className="text-xs">{getInitials(user.email)}</AvatarFallback>
                </Avatar>
              </TableCell>

              {/* 이메일 */}
              <TableCell>
                <div className="flex flex-col">
                  <span className="text-sm font-medium">{user.email}</span>
                  {user.provider && (
                    <span className="text-xs text-muted-foreground capitalize">{user.provider}</span>
                  )}
                </div>
              </TableCell>

              {/* 플랜 */}
              <TableCell><UserRoleBadge planType={user.plan_type} /></TableCell>

              {/* 가입일 */}
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(user.created_at)}
              </TableCell>

              {/* 상태 */}
              <TableCell><UserStatusBadge isActive={user.is_active} /></TableCell>

              {/* 액션 */}
              <TableCell><UserActionCell user={user} /></TableCell>
            </TableRow>
          ))}

          {/* 빈 상태 */}
          {!isLoading && users.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="h-32 text-center text-sm text-muted-foreground">
                검색 결과가 없습니다.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
