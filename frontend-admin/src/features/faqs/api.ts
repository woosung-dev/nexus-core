import { apiClient } from "@/lib/api-client"
import type {
  FaqCreateRequest,
  FaqListResponse,
  FaqResponse,
  FaqUpdateRequest,
} from "./types"

// ─── Query Key Factory ────────────────────────────────────────
export const faqKeys = {
  all: ["faqs"] as const,
  lists: (botId: number) => [...faqKeys.all, "list", botId] as const,
  detail: (id: number) => [...faqKeys.all, "detail", id] as const,
}

// ─── API 함수 ─────────────────────────────────────────────────

/** FAQ 목록 조회 (특정 봇) */
export async function fetchFaqs(botId: number): Promise<FaqListResponse> {
  const { data } = await apiClient.get<FaqListResponse>(
    `/api/v1/admin/bots/${botId}/faqs`
  )
  return data
}

/** FAQ 단일 조회 */
export async function fetchFaq(id: number): Promise<FaqResponse> {
  const { data } = await apiClient.get<FaqResponse>(`/api/v1/admin/faqs/${id}`)
  return data
}

/** FAQ 등록 */
export async function createFaq(
  request: FaqCreateRequest
): Promise<FaqResponse> {
  const { data } = await apiClient.post<FaqResponse>(
    `/api/v1/admin/bots/${request.bot_id}/faqs`,
    {
      question: request.question,
      answer: request.answer,
      threshold: request.threshold,
    }
  )
  return data
}

/** FAQ 수정 (부분 업데이트) */
export async function updateFaq(
  id: number,
  request: FaqUpdateRequest
): Promise<FaqResponse> {
  const { data } = await apiClient.put<FaqResponse>(
    `/api/v1/admin/faqs/${id}`,
    request
  )
  return data
}

/** FAQ 삭제 */
export async function deleteFaq(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/admin/faqs/${id}`)
}
