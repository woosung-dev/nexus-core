"use client"

/**
 * 운영 사실 도메인 — React Query 훅.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createOpsFact,
  deleteOpsFact,
  fetchOpsFacts,
  opsFactKeys,
  updateOpsFact,
} from "./api"
import type {
  OpsFactCreateRequest,
  OpsFactListParams,
  OpsFactUpdateRequest,
} from "./types"

/** 목록 조회 — 초안 포함 전건 */
export function useOpsFacts(params: OpsFactListParams = {}) {
  return useQuery({
    queryKey: opsFactKeys.list(params),
    queryFn: () => fetchOpsFacts(params),
  })
}

/** 등록 */
export function useCreateOpsFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (request: OpsFactCreateRequest) => createOpsFact(request),
    onSuccess: () => qc.invalidateQueries({ queryKey: opsFactKeys.all }),
  })
}

/** 판정 / 수정 */
export function useUpdateOpsFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: OpsFactUpdateRequest }) =>
      updateOpsFact(id, request),
    onSuccess: () => qc.invalidateQueries({ queryKey: opsFactKeys.all }),
  })
}

/** 비활성화 */
export function useDeleteOpsFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteOpsFact(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: opsFactKeys.all }),
  })
}
