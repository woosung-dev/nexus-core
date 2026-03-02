/**
 * 문서 도메인 — API 호출 함수 + Query Key Factory.
 * 모든 문서 관련 API는 이 파일을 통해 호출한다.
 */
import { apiClient } from "@/lib/api-client"
import type {
  DocumentListResponse,
  DocumentUploadResponse,
} from "./types"

// ─── Query Key Factory ─────────────────────────────────────────
export const documentKeys = {
  all: ["documents"] as const,
  byBot: (botId: number) => [...documentKeys.all, "bot", botId] as const,
}

// ─── API 함수 ──────────────────────────────────────────────────

/** 특정 봇의 문서 목록 조회 */
export async function fetchDocuments(botId: number): Promise<DocumentListResponse> {
  const { data } = await apiClient.get<DocumentListResponse>(
    `/api/v1/admin/bots/${botId}/documents`
  )
  return data
}

/** 특정 봇에 문서 업로드 (multipart/form-data) */
export async function uploadDocument(
  botId: number,
  file: File
): Promise<DocumentUploadResponse> {
  const formData = new FormData()
  formData.append("file", file)

  const { data } = await apiClient.post<DocumentUploadResponse>(
    `/api/v1/admin/bots/${botId}/documents`,
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  )
  return data
}

/** 특정 봇의 문서 삭제 */
export async function deleteDocument(botId: number, fileId: string): Promise<void> {
  await apiClient.delete(`/api/v1/admin/bots/${botId}/documents/${fileId}`)
}
