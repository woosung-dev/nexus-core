import { z } from "zod/v4"

// --- Bot 도메인 타입 ---
export type Bot = {
  id: string
  name: string
  description: string | null
  tags: string[]
  is_active: boolean
  system_prompt: string
  llm_model: string
  created_at: string
  updated_at: string
}

// --- LLM 모델 옵션 ---
export const LLM_MODEL_OPTIONS = [
  { label: "GPT-4o", value: "gpt-4o" },
  { label: "GPT-4o Mini", value: "gpt-4o-mini" },
  { label: "Gemini 2.5 Flash", value: "gemini-2.5-flash" },
  { label: "Gemini 3.0 Flash", value: "gemini-3-flash" },
] as const

// --- Zod 폼 검증 스키마 ---
export const botFormSchema = z.object({
  name: z.string().min(2, { message: "봇 이름은 최소 2자 이상이어야 합니다." }),
  description: z.string(),
  tags: z.array(z.string()),
  is_active: z.boolean(),
  system_prompt: z.string().min(1, { message: "시스템 프롬프트는 필수입니다." }),
  llm_model: z.string().min(1, { message: "LLM 모델을 선택해 주세요." }),
})

export type BotFormValues = z.infer<typeof botFormSchema>
