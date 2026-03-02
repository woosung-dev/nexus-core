"use client"

/**
 * 사용자 도메인 — React Query 커스텀 훅.
 * 비즈니스 로직(API 호출, 캐싱, 에러 처리)을 컴포넌트에서 분리.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  deactivateUser,
  fetchUsers,
  updateUser,
  userKeys,
} from "./api"
import type { UserAdminUpdateRequest } from "./types"

// ─── Query 훅 ─────────────────────────────────────────────────

/** 사용자 목록 조회 — 검색어·플랜 필터 사용 */
export function useUsers(params?: { email?: string; plan_type?: string }) {
  return useQuery({
    queryKey: userKeys.listWithFilters(params ?? {}),
    queryFn: () => fetchUsers(params),
  })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

/** 사용자 정보 수정 훅 — plan_type 또는 is_active 변경 */
export function useUpdateUser(userId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: UserAdminUpdateRequest) => updateUser(userId, request),
    onSuccess: () => {
      // 목록 캐시 전체 무효화 (필터 조합과 무관하게 최신 데이터 유지)
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
  })
}

/** 사용자 비활성화 훅 */
export function useDeactivateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (userId: number) => deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: userKeys.lists() })
    },
  })
}
