/**
 * 사용자 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/user.py의 Pydantic 스키마를 기반으로 작성.
 */

export type PlanType = "FREE" | "PRO"

// GET /api/v1/admin/users (개별 사용자)
export type UserResponse = {
  id: number
  email: string
  provider: string | null
  plan_type: PlanType
  avatar_url: string | null
  is_active: boolean
  created_at: string
}

// GET /api/v1/admin/users (목록)
export type UserListResponse = {
  users: UserResponse[]
  total: number
}

// PATCH /api/v1/admin/users/:id (수정 요청)
export type UserAdminUpdateRequest = {
  plan_type?: PlanType
  is_active?: boolean
}
