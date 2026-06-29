"use client"

/**
 * 레드팀 피드백 도메인 — React Query 커스텀 훅.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  fetchCandidates,
  fetchGroupDetail,
  fetchGroups,
  fetchReport,
  fetchStats,
  linkCandidate,
  redteamKeys,
  updateGroupCategory,
  upsertReview,
} from "./api"
import type { GroupListParams, ReviewUpsertRequest } from "./types"

// ─── Query 훅 ─────────────────────────────────────────────────

export function useRedteamStats() {
  return useQuery({ queryKey: redteamKeys.stats(), queryFn: fetchStats })
}

export function useRedteamReport() {
  return useQuery({ queryKey: redteamKeys.report(), queryFn: fetchReport })
}

export function useRedteamGroups(params: GroupListParams) {
  return useQuery({
    queryKey: redteamKeys.list(params),
    queryFn: () => fetchGroups(params),
    placeholderData: (prev) => prev, // 필터 변경 시 깜빡임 방지
  })
}

export function useRedteamGroupDetail(groupId: number | null) {
  return useQuery({
    queryKey: redteamKeys.detail(groupId ?? -1),
    queryFn: () => fetchGroupDetail(groupId as number),
    enabled: groupId !== null,
  })
}

export function useRedteamCandidates(groupId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: redteamKeys.candidates(groupId ?? -1),
    queryFn: () => fetchCandidates(groupId as number),
    enabled: groupId !== null && enabled,
  })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

function useInvalidateGroup(groupId: number | null) {
  const qc = useQueryClient()
  return () => {
    qc.invalidateQueries({ queryKey: redteamKeys.lists() })
    qc.invalidateQueries({ queryKey: redteamKeys.stats() })
    if (groupId !== null) {
      qc.invalidateQueries({ queryKey: redteamKeys.detail(groupId) })
      qc.invalidateQueries({ queryKey: redteamKeys.candidates(groupId) })
    }
  }
}

export function useUpdateCategory(groupId: number | null) {
  const invalidate = useInvalidateGroup(groupId)
  return useMutation({
    mutationFn: (category: string | null) =>
      updateGroupCategory(groupId as number, category),
    onSuccess: invalidate,
  })
}

export function useLinkCandidate(groupId: number | null) {
  const invalidate = useInvalidateGroup(groupId)
  return useMutation({
    mutationFn: (vars: { responseId: number; action: "confirm" | "reject" }) =>
      linkCandidate(groupId as number, vars.responseId, vars.action),
    onSuccess: invalidate,
  })
}

export function useUpsertReview(groupId: number | null) {
  const invalidate = useInvalidateGroup(groupId)
  return useMutation({
    mutationFn: (request: ReviewUpsertRequest) => upsertReview(request),
    onSuccess: invalidate,
  })
}
