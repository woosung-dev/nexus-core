/**
 * 봇 도메인 — API 호출 함수 + Query Key Factory.
 * 모든 API 호출은 apiClient (Axios 인스턴스)를 통해 수행한다.
 */
import { apiClient } from "@/lib/api-client"
import type {
  BotCreateRequest,
  BotImageUploadResponse,
  BotListResponse,
  BotResponse,
  BotUpdateRequest,
} from "./types"

// ─── Query Key Factory ────────────────────────────────────────
// Query Key 파편화 방지: 중앙에서 일관되게 관리
export const botKeys = {
  all: ["bots"] as const,
  lists: () => [...botKeys.all, "list"] as const,
  detail: (id: number) => [...botKeys.all, "detail", id] as const,
}

// ─── API 함수 ─────────────────────────────────────────────────

/** 봇 전체 목록 조회 (Admin) */
export async function fetchBots(): Promise<BotListResponse> {
  const { data } = await apiClient.get<BotListResponse>("/api/v1/admin/bots")
  return data
}

/** 봇 단일 상세 조회 (Admin) */
export async function fetchBot(id: number): Promise<BotResponse> {
  const { data } = await apiClient.get<BotResponse>(`/api/v1/admin/bots/${id}`)
  return data
}

/** 봇 생성 */
export async function createBot(
  request: BotCreateRequest
): Promise<BotResponse> {
  const { data } = await apiClient.post<BotResponse>(
    "/api/v1/admin/bots",
    request
  )
  return data
}

/** 봇 수정 (부분 업데이트) */
export async function updateBot(
  id: number,
  request: BotUpdateRequest
): Promise<BotResponse> {
  const { data } = await apiClient.put<BotResponse>(
    `/api/v1/admin/bots/${id}`,
    request
  )
  return data
}

/** 봇 삭제 (소프트 삭제 — is_active=false) */
export async function deleteBot(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/admin/bots/${id}`)
}

/** 봇 대표 이미지 업로드 (multipart/form-data) */
export async function uploadBotImage(
  botId: number,
  file: File
): Promise<BotImageUploadResponse> {
  const formData = new FormData()
  formData.append("file", file)

  const { data } = await apiClient.post<BotImageUploadResponse>(
    `/api/v1/admin/bots/${botId}/image`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" },
    }
  )
  return data
}
