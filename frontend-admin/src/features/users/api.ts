/**
 * 사용자 도메인 — API 호출 함수 + Query Key Factory.
 * 모든 사용자 관련 API는 이 파일을 통해 호출한다.
 */
import { apiClient } from "@/lib/api-client"
import type {
  UserAdminUpdateRequest,
  UserListResponse,
  UserResponse,
} from "./types"

// ─── Query Key Factory ─────────────────────────────────────────
export const userKeys = {
  all: ["users"] as const,
  lists: () => [...userKeys.all, "list"] as const,
  listWithFilters: (params: { email?: string; plan_type?: string }) =>
    [...userKeys.lists(), params] as const,
  detail: (id: number) => [...userKeys.all, "detail", id] as const,
}

// ─── API 함수 ──────────────────────────────────────────────────

/** 전체 사용자 목록 조회 (검색·필터 지원) */
export async function fetchUsers(params?: {
  email?: string
  plan_type?: string
}): Promise<UserListResponse> {
  const { data } = await apiClient.get<UserListResponse>("/api/v1/admin/users", {
    params: {
      ...(params?.email ? { email: params.email } : {}),
      ...(params?.plan_type ? { plan_type: params.plan_type } : {}),
    },
  })
  return data
}

/** 사용자 정보 수정 (부분 업데이트) */
export async function updateUser(
  userId: number,
  request: UserAdminUpdateRequest
): Promise<UserResponse> {
  const { data } = await apiClient.patch<UserResponse>(
    `/api/v1/admin/users/${userId}`,
    request
  )
  return data
}

/** 사용자 비활성화 (소프트 삭제) */
export async function deactivateUser(userId: number): Promise<void> {
  await apiClient.delete(`/api/v1/admin/users/${userId}`)
}
