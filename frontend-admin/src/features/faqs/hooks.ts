"use client"

/**
 * FAQ 도메인 — React Query 커스텀 훅.
 * 비즈니스 로직(API 호출, 캐싱, 에러 처리)을 컴포넌트에서 분리.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createFaq,
  deleteFaq,
  faqKeys,
  fetchFaqs,
  updateFaq,
} from "./api"
import type { FaqCreateRequest, FaqUpdateRequest } from "./types"

// ─── Query 훅 ─────────────────────────────────────────────────

/** FAQ 목록 조회 훅 — 선택된 봇(botId)의 FAQ만 조회 */
export function useFaqs(botId: number | null) {
  return useQuery({
    queryKey: faqKeys.lists(botId ?? 0),
    queryFn: () => fetchFaqs(botId!),
    enabled: !!botId,
  })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

/** FAQ 등록 훅 */
export function useCreateFaq() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: FaqCreateRequest) => createFaq(request),
    onSuccess: (_data, variables) => {
      // 해당 봇의 FAQ 목록 캐시 무효화
      queryClient.invalidateQueries({
        queryKey: faqKeys.lists(variables.bot_id),
      })
    },
  })
}

/** FAQ 수정 훅 */
export function useUpdateFaq(botId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: FaqUpdateRequest }) =>
      updateFaq(id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: faqKeys.lists(botId),
      })
    },
  })
}

/** FAQ 삭제 훅 */
export function useDeleteFaq(botId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => deleteFaq(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: faqKeys.lists(botId),
      })
    },
  })
}
