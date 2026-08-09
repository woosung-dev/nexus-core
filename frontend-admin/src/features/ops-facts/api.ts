import { apiClient } from "@/lib/api-client"
import type {
  OpsFactCreateRequest,
  OpsFactListParams,
  OpsFactListResponse,
  OpsFactResponse,
  OpsFactUpdateRequest,
} from "./types"

const BASE = "/api/v1/admin/ops-facts"

// ─── Query Key Factory ────────────────────────────────────────
export const opsFactKeys = {
  all: ["ops-facts"] as const,
  list: (params: OpsFactListParams) => [...opsFactKeys.all, "list", params] as const,
  detail: (id: number) => [...opsFactKeys.all, "detail", id] as const,
}

// ─── API 함수 ─────────────────────────────────────────────────

/** 운영 사실 목록 — 초안 포함 전건 */
export async function fetchOpsFacts(
  params: OpsFactListParams = {}
): Promise<OpsFactListResponse> {
  const { data } = await apiClient.get<OpsFactListResponse>(BASE, { params })
  return data
}

/** 운영 사실 단일 조회 */
export async function fetchOpsFact(id: number): Promise<OpsFactResponse> {
  const { data } = await apiClient.get<OpsFactResponse>(`${BASE}/${id}`)
  return data
}

/** 운영 사실 등록 — 서버가 status='초안' 으로 고정한다 */
export async function createOpsFact(
  request: OpsFactCreateRequest
): Promise<OpsFactResponse> {
  const { data } = await apiClient.post<OpsFactResponse>(BASE, request)
  return data
}

/** 관리자 판정 / 내용 수정 (부분 업데이트) */
export async function updateOpsFact(
  id: number,
  request: OpsFactUpdateRequest
): Promise<OpsFactResponse> {
  const { data } = await apiClient.put<OpsFactResponse>(`${BASE}/${id}`, request)
  return data
}

/** 비활성화 (소프트 삭제) */
export async function deleteOpsFact(id: number): Promise<void> {
  await apiClient.delete(`${BASE}/${id}`)
}
