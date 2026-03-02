"use client"

/**
 * 사용자 활성 상태 배지 컴포넌트.
 */
import { Badge } from "@/components/ui/badge"

interface UserStatusBadgeProps {
  isActive: boolean
}

export function UserStatusBadge({ isActive }: UserStatusBadgeProps) {
  if (isActive) {
    return (
      <Badge className="bg-emerald-500 hover:bg-emerald-500 text-white">활성</Badge>
    )
  }
  return (
    <Badge variant="destructive">비활성</Badge>
  )
}
