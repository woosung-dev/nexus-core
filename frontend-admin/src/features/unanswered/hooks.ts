"use client"

/**
 * 못 답한 질문 도메인 — React Query 훅.
 *
 * 성공 피드백은 토스트가 아니라 **캐시 무효화 + 인라인 상태**다. 이 레포에는 토스트
 * 라이브러리가 없고(sonner·Toaster 0건), 목록이 즉시 다시 그려지는 것이 곧 확인이다.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import {
  fetchUnanswered,
  fetchUnansweredOccurrences,
  setUnansweredTriage,
  unansweredKeys,
} from "./api"
import type { UnansweredListParams, UnansweredTriageRequest } from "./types"

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
  })
}
