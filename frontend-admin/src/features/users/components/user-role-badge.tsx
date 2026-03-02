"use client"

/**
 * 사용자 권한(Plan) 배지 컴포넌트.
 */
import { Badge } from "@/components/ui/badge"
import type { PlanType } from "@/features/users/types"

interface UserRoleBadgeProps {
  planType: PlanType
}

export function UserRoleBadge({ planType }: UserRoleBadgeProps) {
  if (planType === "PRO") {
    return (
      <Badge className="bg-violet-500 hover:bg-violet-500 text-white">PRO</Badge>
    )
  }
  return (
    <Badge variant="secondary">FREE</Badge>
  )
}
