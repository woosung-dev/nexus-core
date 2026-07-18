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

type InstructionBody = Omit<BotInstruction, "id" | "version" | "is_applied" | "created_at" | "updated_at">

type GenerateBody = Pick<
  BotInstruction,
  "role" | "goal" | "tone" | "audience" | "constraints" | "dos" | "donts" | "examples" | "llm_model"
> & {
  mode: "generate" | "improve"
  draft?: string
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
  body: Partial<InstructionBody>
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
