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
import { toastError, toastSuccess } from "@/lib/toast"

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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: opsFactKeys.all })
      // 등록만으로는 챗봇이 안 바뀐다 — 승인분만 런타임이 읽는다.
      toastSuccess("초안으로 등록했습니다. 승인해야 챗봇에 반영됩니다.")
    },
    onError: (error) => toastError(error, "운영 사실을 등록하지 못했습니다."),
  })
}

/** 판정 / 수정 */
export function useUpdateOpsFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: OpsFactUpdateRequest }) =>
      updateOpsFact(id, request),
    onSuccess: () => qc.invalidateQueries({ queryKey: opsFactKeys.all }),
    onError: (error) => toastError(error, "운영 사실을 저장하지 못했습니다."),
  })
}

/** 비활성화 */
export function useDeleteOpsFact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => deleteOpsFact(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: opsFactKeys.all })
      toastSuccess("비활성화했습니다.")
    },
    onError: (error) => toastError(error, "비활성화하지 못했습니다."),
  })
}
