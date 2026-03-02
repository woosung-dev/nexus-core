"use client"

/**
 * 봇 도메인 — React Query 커스텀 훅.
 * 비즈니스 로직(API 호출, 캐싱, 에러 처리)을 컴포넌트에서 분리.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useRouter } from "next/navigation"
import {
  botKeys,
  createBot,
  deleteBot,
  fetchBot,
  fetchBots,
  updateBot,
  uploadBotImage,
} from "./api"
import type { BotCreateRequest, BotUpdateRequest } from "./types"

// ─── Query 훅 ─────────────────────────────────────────────────

/** 봇 목록 조회 훅 */
export function useBots() {
  return useQuery({
    queryKey: botKeys.lists(),
    queryFn: fetchBots,
  })
}

/** 봇 단일 상세 조회 훅 */
export function useBot(id: number) {
  return useQuery({
    queryKey: botKeys.detail(id),
    queryFn: () => fetchBot(id),
    enabled: !!id,
  })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

/** 봇 생성 훅 — 봇 생성 후 이미지가 있으면 순차 업로드 */
export function useCreateBot() {
  const queryClient = useQueryClient()
  const router = useRouter()

  return useMutation({
    mutationFn: async ({
      request,
      imageFile,
    }: {
      request: BotCreateRequest
      imageFile?: File | null
    }) => {
      // ① 봇 메타데이터 생성 → bot_id 확보
      const bot = await createBot(request)

      // ② 이미지가 있으면 순차적으로 업로드
      if (imageFile) {
        await uploadBotImage(bot.id, imageFile)
      }

      return bot
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: botKeys.lists() })
      router.push("/bots")
    },
  })
}

/** 봇 수정 훅 */
export function useUpdateBot(id: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: BotUpdateRequest) => updateBot(id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: botKeys.lists() })
      queryClient.invalidateQueries({ queryKey: botKeys.detail(id) })
    },
  })
}

/** 봇 삭제 훅 */
export function useDeleteBot() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => deleteBot(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: botKeys.lists() })
    },
  })
}
