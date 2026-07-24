// 용어집 목록과 변경 작업을 위한 React Query 훅을 제공합니다.
"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createGlossary,
  deleteGlossary,
  fetchGlossary,
  glossaryKeys,
  updateGlossary,
} from "./api"
import type { GlossaryCreateRequest, GlossaryUpdateRequest } from "./types"

export function useGlossary(botId: number | null) {
  return useQuery({
    queryKey: glossaryKeys.lists(botId),
    queryFn: () => fetchGlossary(botId),
  })
}

export function useCreateGlossary() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: GlossaryCreateRequest) => createGlossary(request),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: glossaryKeys.all }),
  })
}

export function useUpdateGlossary() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, request }: { id: number; request: GlossaryUpdateRequest }) =>
      updateGlossary(id, request),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: glossaryKeys.all }),
  })
}

export function useDeleteGlossary() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => deleteGlossary(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: glossaryKeys.all }),
  })
}
