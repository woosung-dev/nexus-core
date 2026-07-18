"use client"

// 지침 빌더의 조회와 변경을 React Query로 연결한다.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { botKeys, updateBot } from "@/features/bots/api"
import {
  createInstruction,
  deleteInstruction,
  fetchInstructions,
  generateInstruction,
  instructionKeys,
  previewInstruction,
  updateInstruction,
} from "./api"

export function useGenerateInstruction() {
  return useMutation({ mutationFn: generateInstruction })
}

export function usePreviewInstruction() {
  return useMutation({ mutationFn: previewInstruction })
}

export function useApplyToBot() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      botId,
      system_prompt,
      llm_model,
    }: {
      botId: number
      system_prompt: string
      llm_model?: string
    }) => updateBot(botId, { system_prompt, ...(llm_model ? { llm_model } : {}) }),
    onSuccess: (_, { botId }) => {
      queryClient.invalidateQueries({ queryKey: botKeys.lists() })
      queryClient.invalidateQueries({ queryKey: botKeys.detail(botId) })
    },
  })
}

export function useInstructions(botId?: number) {
  return useQuery({
    queryKey: botId === undefined ? instructionKeys.lists() : instructionKeys.byBot(botId),
    queryFn: () => fetchInstructions(botId),
  })
}

export function useCreateInstruction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createInstruction,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: instructionKeys.lists() }),
  })
}

export function useUpdateInstruction(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: Parameters<typeof updateInstruction>[1]) => updateInstruction(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: instructionKeys.lists() })
      queryClient.invalidateQueries({ queryKey: instructionKeys.detail(id) })
    },
  })
}

export function useDeleteInstruction() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteInstruction,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: instructionKeys.lists() }),
  })
}
