import { apiClient } from "@/lib/api-client"
import type {
  UnansweredListParams,
  UnansweredListResponse,
  UnansweredOccurrenceListResponse,
  UnansweredTriageRequest,
  UnansweredTriageResponse,
} from "./types"

const BASE = "/api/v1/admin/unanswered"

// ─── Query Key Factory ────────────────────────────────────────
export const unansweredKeys = {
  all: ["unanswered"] as const,
  list: (params: UnansweredListParams) => [...unansweredKeys.all, "list", params] as const,
  occurrences: (norm: string) => [...unansweredKeys.all, "occurrences", norm] as const,
}

// ─── API 함수 ─────────────────────────────────────────────────

/** 빈도순 질문 그룹 목록 — 「무엇부터 채울지」를 이 순서가 정해 준다 */
export async function fetchUnanswered(
  params: UnansweredListParams = {}
): Promise<UnansweredListResponse> {
  const { data } = await apiClient.get<UnansweredListResponse>(BASE, { params })
  return data
}

/**
 * 한 그룹의 개별 발생.
 *
 * `question_norm` 은 정규화 결과라 임의 유니코드가 들어온다 — 경로가 아니라 쿼리로 보낸다.
 */
export async function fetchUnansweredOccurrences(
  questionNorm: string
): Promise<UnansweredOccurrenceListResponse> {
  const { data } = await apiClient.get<UnansweredOccurrenceListResponse>(
    `${BASE}/occurrences`,
    { params: { question_norm: questionNorm } }
  )
  return data
}

/** 그룹 전체에 처리 경로를 찍는다 */
export async function setUnansweredTriage(
  request: UnansweredTriageRequest
): Promise<UnansweredTriageResponse> {
  const { data } = await apiClient.patch<UnansweredTriageResponse>(`${BASE}/triage`, request)
  return data
}
