/**
 * 레드팀 피드백 도메인 — API 호출 함수 + Query Key Factory.
 */
import { apiClient } from "@/lib/api-client"
import type {
  CandidateItem,
  GroupDetail,
  GroupListParams,
  GroupListResponse,
  ReportResponse,
  ResponseItem,
  ReviewItem,
  ReviewUpsertRequest,
  StatsResponse,
} from "./types"

const BASE = "/api/v1/admin/redteam"

// ─── Query Key Factory ─────────────────────────────────────────
export const redteamKeys = {
  all: ["redteam"] as const,
  stats: () => [...redteamKeys.all, "stats"] as const,
  lists: () => [...redteamKeys.all, "groups"] as const,
  list: (params: GroupListParams) => [...redteamKeys.lists(), params] as const,
  detail: (id: number) => [...redteamKeys.all, "detail", id] as const,
  candidates: (id: number) => [...redteamKeys.all, "candidates", id] as const,
  report: () => [...redteamKeys.all, "report"] as const,
}

// ─── API 함수 ──────────────────────────────────────────────────

export async function fetchStats(): Promise<StatsResponse> {
  const { data } = await apiClient.get<StatsResponse>(`${BASE}/stats`)
  return data
}

export async function fetchReport(): Promise<ReportResponse> {
  const { data } = await apiClient.get<ReportResponse>(`${BASE}/report`)
  return data
}

export async function fetchGroups(params: GroupListParams): Promise<GroupListResponse> {
  const { data } = await apiClient.get<GroupListResponse>(`${BASE}/groups`, {
    params: {
      ...(params.category ? { category: params.category } : {}),
      ...(params.risk ? { risk: params.risk } : {}),
      ...(params.week_present ? { week_present: params.week_present } : {}),
      ...(params.matched_only ? { matched_only: true } : {}),
      ...(params.q ? { q: params.q } : {}),
      page: params.page ?? 1,
      page_size: params.page_size ?? 50,
    },
  })
  return data
}

export async function fetchGroupDetail(groupId: number): Promise<GroupDetail> {
  const { data } = await apiClient.get<GroupDetail>(`${BASE}/groups/${groupId}`)
  return data
}

export async function updateGroupCategory(
  groupId: number,
  category: string | null
): Promise<GroupDetail> {
  const { data } = await apiClient.patch<GroupDetail>(`${BASE}/groups/${groupId}`, {
    category,
  })
  return data
}

export async function fetchCandidates(
  groupId: number,
  limit = 10
): Promise<CandidateItem[]> {
  const { data } = await apiClient.get<CandidateItem[]>(
    `${BASE}/groups/${groupId}/candidates`,
    { params: { limit } }
  )
  return data
}

export async function linkCandidate(
  groupId: number,
  responseId: number,
  action: "confirm" | "reject"
): Promise<ResponseItem> {
  const { data } = await apiClient.post<ResponseItem>(`${BASE}/groups/${groupId}/links`, {
    response_id: responseId,
    action,
  })
  return data
}

export async function upsertReview(request: ReviewUpsertRequest): Promise<ReviewItem> {
  const { data } = await apiClient.put<ReviewItem>(`${BASE}/reviews`, request)
  return data
}
