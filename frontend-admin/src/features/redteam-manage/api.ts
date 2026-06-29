/**
 * 중간보고 입력관리 도메인 — API 호출 함수 + Query Key Factory.
 * 기존 redteam 라우터(/api/v1/admin/redteam)에 추가된 관리 엔드포인트를 호출한다.
 */
import { apiClient } from "@/lib/api-client"
import { linkCandidate } from "../redteam/api"
import type {
  GroupCompare,
  GroupManageUpdate,
  ManageFeedbackItem,
  ManageGroupDetail,
  ManageGroupListParams,
  ManageGroupListResponse,
  ManageReportResponse,
  ManageStatsResponse,
  UnmatchedItem,
} from "./types"

const BASE = "/api/v1/admin/redteam"

export type UnmatchedParams = { week?: number; q?: string; page?: number; page_size?: number }

// ─── Query Key Factory ─────────────────────────────────────────
export const manageKeys = {
  all: ["redteam-manage"] as const,
  stats: () => [...manageKeys.all, "stats"] as const,
  lists: () => [...manageKeys.all, "groups"] as const,
  list: (params: ManageGroupListParams) => [...manageKeys.lists(), params] as const,
  detail: (id: number) => [...manageKeys.all, "detail", id] as const,
  compare: (id: number) => [...manageKeys.all, "compare", id] as const,
  unmatched: (params: UnmatchedParams) => [...manageKeys.all, "unmatched", params] as const,
  tags: () => [...manageKeys.all, "tags"] as const,
  report: () => [...manageKeys.all, "report"] as const,
}

// ─── API 함수 ──────────────────────────────────────────────────

export async function fetchManageGroups(
  params: ManageGroupListParams
): Promise<ManageGroupListResponse> {
  const { data } = await apiClient.get<ManageGroupListResponse>(`${BASE}/groups`, {
    params: {
      ...(params.category ? { category: params.category } : {}),
      ...(params.risk ? { risk: params.risk } : {}),
      ...(params.status ? { status: params.status } : {}),
      ...(params.level != null ? { level: params.level } : {}), // level=0 도 포함되도록 != null
      ...(params.disposition ? { disposition: params.disposition } : {}),
      ...(params.assignee ? { assignee: params.assignee } : {}),
      ...(params.tag ? { tag: params.tag } : {}),
      ...(params.origin ? { origin: params.origin } : {}),
      ...(params.multiweek ? { multiweek: true } : {}),
      ...(params.week_present ? { week_present: params.week_present } : {}),
      ...(params.matched_only ? { matched_only: true } : {}),
      ...(params.q ? { q: params.q } : {}),
      page: params.page ?? 1,
      page_size: params.page_size ?? 50,
    },
  })
  return data
}

export async function fetchManageGroupDetail(groupId: number): Promise<ManageGroupDetail> {
  const { data } = await apiClient.get<ManageGroupDetail>(`${BASE}/groups/${groupId}`)
  return data
}

export async function updateGroupManage(
  groupId: number,
  patch: GroupManageUpdate
): Promise<ManageGroupDetail> {
  const { data } = await apiClient.patch<ManageGroupDetail>(
    `${BASE}/groups/${groupId}/manage`,
    patch
  )
  return data
}

export async function fetchGroupCompare(groupId: number): Promise<GroupCompare> {
  const { data } = await apiClient.get<GroupCompare>(`${BASE}/groups/${groupId}/compare`)
  return data
}

export async function fetchManageStats(): Promise<ManageStatsResponse> {
  const { data } = await apiClient.get<ManageStatsResponse>(`${BASE}/manage/stats`)
  return data
}

export async function fetchUnmatched(params: UnmatchedParams): Promise<UnmatchedItem[]> {
  const { data } = await apiClient.get<UnmatchedItem[]>(`${BASE}/manage/unmatched`, {
    params: {
      ...(params.week ? { week: params.week } : {}),
      ...(params.q ? { q: params.q } : {}),
      page: params.page ?? 1,
      page_size: params.page_size ?? 50,
    },
  })
  return data
}

export async function fetchManageTags(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>(`${BASE}/manage/tags`)
  return data
}

export async function fetchManageReport(): Promise<ManageReportResponse> {
  const { data } = await apiClient.get<ManageReportResponse>(`${BASE}/manage/report`)
  return data
}

export async function addManageFeedback(
  groupId: number,
  author: string,
  content: string
): Promise<ManageFeedbackItem> {
  const { data } = await apiClient.post<ManageFeedbackItem>(
    `${BASE}/groups/${groupId}/feedback`,
    { author, content }
  )
  return data
}

export async function deleteManageFeedback(feedbackId: number): Promise<void> {
  await apiClient.delete(`${BASE}/feedback/${feedbackId}`)
}

// 미분류 큐 → 그룹 연결은 기존 redteam links 엔드포인트 재사용
export { linkCandidate }
