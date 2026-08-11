"use client"

/**
 * 문서 도메인 — React Query 커스텀 훅.
 * 비즈니스 로직(API 호출, 캐싱, 에러 처리)을 컴포넌트에서 분리.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  documentKeys,
  deleteDocument,
  fetchDocuments,
  uploadDocument,
} from "./api"
import { toastError, toastSuccess } from "@/lib/toast"

// ─── Query 훅 ─────────────────────────────────────────────────

/** 특정 봇의 문서 목록 조회 훅 — botId가 null이면 호출하지 않음 */
export function useDocuments(botId: number | null) {
  return useQuery({
    queryKey: botId ? documentKeys.byBot(botId) : documentKeys.all,
    queryFn: () => fetchDocuments(botId!),
    enabled: botId !== null,
  })
}

// ─── Mutation 훅 ──────────────────────────────────────────────

/** 문서 업로드 훅 — 완료 후 해당 봇의 문서 목록 캐시 무효화 */
export function useUploadDocument(botId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => uploadDocument(botId, file),
    onSuccess: (_data, file) => {
      queryClient.invalidateQueries({ queryKey: documentKeys.byBot(botId) })
      toastSuccess(`「${file.name}」을 올렸습니다.`)
    },
    onError: (error) => toastError(error, "문서를 올리지 못했습니다."),
  })
}

/** 문서 삭제 훅 — 완료 후 해당 봇의 문서 목록 캐시 무효화 */
export function useDeleteDocument(botId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (fileId: string) => deleteDocument(botId, fileId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.byBot(botId) })
      toastSuccess("문서를 삭제했습니다.")
    },
    onError: (error) => toastError(error, "문서를 삭제하지 못했습니다."),
  })
}
