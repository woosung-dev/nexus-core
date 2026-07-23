"use client"

// 지침 빌더의 조회와 변경을 React Query로 연결한다.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
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

export function useUpdateGem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: Parameters<typeof updateInstruction>[1] }) =>
      updateInstruction(id, body),
    onSuccess: (_, { id }) => {
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
