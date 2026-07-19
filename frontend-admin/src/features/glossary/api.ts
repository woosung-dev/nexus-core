// 용어집 관리 API 호출과 React Query 키를 제공합니다.
import { apiClient } from "@/lib/api-client"
import type {
  Glossary,
  GlossaryCreateRequest,
  GlossaryListResponse,
  GlossaryUpdateRequest,
} from "./types"

export const glossaryKeys = {
  all: ["glossary"] as const,
  lists: (botId: number | null) =>
    [...glossaryKeys.all, "list", botId ?? "global"] as const,
  detail: (id: number) => [...glossaryKeys.all, "detail", id] as const,
}

export async function fetchGlossary(botId: number | null): Promise<GlossaryListResponse> {
  const { data } = await apiClient.get<GlossaryListResponse>(
    botId
      ? `/api/v1/admin/bots/${botId}/glossary`
      : "/api/v1/admin/glossary?scope=global"
  )
  return data
}

export async function fetchGlossaryTerm(id: number): Promise<Glossary> {
  const { data } = await apiClient.get<Glossary>(`/api/v1/admin/glossary/${id}`)
  return data
}

export async function createGlossary(
  request: GlossaryCreateRequest
): Promise<Glossary> {
  const { data } = await apiClient.post<Glossary>(
    request.bot_id
      ? `/api/v1/admin/bots/${request.bot_id}/glossary`
      : "/api/v1/admin/glossary",
    request
  )
  return data
}

export async function updateGlossary(
  id: number,
  request: GlossaryUpdateRequest
): Promise<Glossary> {
  const { data } = await apiClient.put<Glossary>(
    `/api/v1/admin/glossary/${id}`,
    request
  )
  return data
}

export async function deleteGlossary(id: number): Promise<{ deleted: boolean }> {
  const { data } = await apiClient.delete<{ deleted: boolean }>(
    `/api/v1/admin/glossary/${id}`
  )
  return data
}
