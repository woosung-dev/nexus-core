// 지침 빌더 백엔드와 통신하는 API 함수.
import { apiClient } from "@/lib/api-client"
import type {
  BotInstruction,
  BotInstructionListResponse,
  InstructionGenerateResponse,
  InstructionPreviewResponse,
} from "./types"

export const instructionKeys = {
  all: ["instructions"] as const,
  lists: () => [...instructionKeys.all, "list"] as const,
  byBot: (botId: number) => [...instructionKeys.all, "bot", botId] as const,
  detail: (id: number) => [...instructionKeys.all, "detail", id] as const,
}

// Gem 저장에 필요한 최소 필드 — 나머지 컬럼은 백엔드 기본값에 위임.
type InstructionBody = {
  name: string
  description: string
  system_prompt: string
  llm_model: string
}

type InstructionUpdateBody = Partial<InstructionBody>

// AI 다듬기 — 붙여넣은 문서(draft)를 개선한다.
type GenerateBody = {
  mode: "generate" | "improve"
  draft?: string
  llm_model: string
}

type PreviewBody = {
  system_prompt: string
  message: string
  bot_id: number | null
  use_rag: boolean
  llm_model: string
}

export async function generateInstruction(
  body: GenerateBody
): Promise<InstructionGenerateResponse> {
  const { data } = await apiClient.post<InstructionGenerateResponse>(
    "/api/v1/admin/instructions/generate",
    body,
    { timeout: 60_000 }
  )
  return data
}

export async function previewInstruction(
  body: PreviewBody
): Promise<InstructionPreviewResponse> {
  const { data } = await apiClient.post<InstructionPreviewResponse>(
    "/api/v1/admin/instructions/preview",
    body,
    { timeout: 60_000 }
  )
  return data
}

export async function fetchInstructions(
  botId?: number
): Promise<BotInstructionListResponse> {
  const { data } = await apiClient.get<BotInstructionListResponse>(
    "/api/v1/admin/instructions",
    { params: botId === undefined ? undefined : { bot_id: botId } }
  )
  return data
}

export async function fetchInstruction(id: number): Promise<BotInstruction> {
  const { data } = await apiClient.get<BotInstruction>(
    `/api/v1/admin/instructions/${id}`
  )
  return data
}

export async function createInstruction(
  body: InstructionBody
): Promise<BotInstruction> {
  const { data } = await apiClient.post<BotInstruction>(
    "/api/v1/admin/instructions",
    body
  )
  return data
}

export async function updateInstruction(
  id: number,
  body: InstructionUpdateBody
): Promise<BotInstruction> {
  const { data } = await apiClient.put<BotInstruction>(
    `/api/v1/admin/instructions/${id}`,
    body
  )
  return data
}

export async function deleteInstruction(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/admin/instructions/${id}`)
}
