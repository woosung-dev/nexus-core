"use client"

/**
 * 못 답한 질문 도메인 — React Query 훅.
 *
 * 성공 확인은 목록이 즉시 다시 그려지는 것이고, 실패는 토스트로 알린다.
 * (전에는 토스트 라이브러리가 없어 실패가 화면에 전혀 안 나타났다.)
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  fetchUnanswered,
  fetchUnansweredOccurrences,
  setUnansweredTriage,
  unansweredKeys,
} from "./api"
import type { UnansweredListParams, UnansweredTriageRequest } from "./types"
import { toastError } from "@/lib/toast"

/** 빈도순 질문 그룹 목록 */
export function useUnanswered(params: UnansweredListParams = {}) {
  return useQuery({
    queryKey: unansweredKeys.list(params),
    queryFn: () => fetchUnanswered(params),
  })
}

/** 한 그룹의 개별 발생 — 상세 시트를 열 때만 부른다 */
export function useUnansweredOccurrences(questionNorm: string | null) {
  return useQuery({
    queryKey: unansweredKeys.occurrences(questionNorm ?? ""),
    queryFn: () => fetchUnansweredOccurrences(questionNorm as string),
    enabled: !!questionNorm,
  })
}

/** 처리 경로 찍기 */
export function useSetTriage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (request: UnansweredTriageRequest) => setUnansweredTriage(request),
    onSuccess: () => qc.invalidateQueries({ queryKey: unansweredKeys.all }),
    onError: (error) => toastError(error, "처리 경로를 저장하지 못했습니다."),
  })
}
