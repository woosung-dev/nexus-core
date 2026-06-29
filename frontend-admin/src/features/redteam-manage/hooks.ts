"use client"

/**
 * 중간보고 입력관리 도메인 — React Query 커스텀 훅.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  fetchGroupCompare,
  fetchManageGroupDetail,
  fetchManageGroups,
  fetchManageStats,
  fetchManageTags,
  fetchUnmatched,
  linkCandidate,
  manageKeys,
  updateGroupManage,
  type UnmatchedParams,
} from "./api"
import type { GroupManageUpdate, ManageGroupListParams } from "./types"

// ─── Query 훅 ─────────────────────────────────────────────────

export function useManageGroups(params: ManageGroupListParams) {
  return useQuery({
    queryKey: manageKeys.list(params),
    queryFn: () => fetchManageGroups(params),
    placeholderData: (prev) => prev, // 필터 변경 시 깜빡임 방지
  })
}

export function useManageGroupDetail(groupId: number | null) {
  return useQuery({
    queryKey: manageKeys.detail(groupId ?? -1),
    queryFn: () => fetchManageGroupDetail(groupId as number),
    enabled: groupId !== null,
  })
}

export function useGroupCompare(groupId: number | null) {
  return useQuery({
    queryKey: manageKeys.compare(groupId ?? -1),
    queryFn: () => fetchGroupCompare(groupId as number),
    enabled: groupId !== null,
  })
}

export function useManageStats() {
  return useQuery({ queryKey: manageKeys.stats(), queryFn: fetchManageStats })
}

export function useUnmatched(params: UnmatchedParams) {
  return useQuery({
    queryKey: manageKeys.unmatched(params),
    queryFn: () => fetchUnmatched(params),
    placeholderData: (prev) => prev,
  })
}

export function useManageTags() {
  return useQuery({ queryKey: manageKeys.tags(), queryFn: fetchManageTags })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

export function useUpdateGroupManage(groupId: number | null) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (patch: GroupManageUpdate) => updateGroupManage(groupId as number, patch),
    onSuccess: (detail) => {
      // PATCH는 전체 GroupDetail을 반환 → 상세 캐시 갱신 + 목록/요약 무효화
      if (groupId !== null) qc.setQueryData(manageKeys.detail(groupId), detail)
      qc.invalidateQueries({ queryKey: manageKeys.lists() })
      qc.invalidateQueries({ queryKey: manageKeys.stats() })
      qc.invalidateQueries({ queryKey: manageKeys.tags() })
    },
  })
}

// 미분류 큐 → 그룹 연결 (기존 redteam links 재사용). 연결 후 미분류·요약 무효화.
export function useLinkUnmatched() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { groupId: number; responseId: number; action: "confirm" | "reject" }) =>
      linkCandidate(vars.groupId, vars.responseId, vars.action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: manageKeys.all })
    },
  })
}
