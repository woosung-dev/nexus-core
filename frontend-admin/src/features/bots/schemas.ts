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
  { label: "GPT-4o", value: "gpt-4o", provider: "openai" },
  { label: "GPT-4o Mini", value: "gpt-4o-mini", provider: "openai" },
  { label: "GPT-5 Mini", value: "gpt-5-mini", provider: "openai" },
  { label: "Gemini 2.5 Flash", value: "gemini-2.5-flash", provider: "gemini" },
  { label: "Gemini 3.0 Flash", value: "gemini-3-flash-preview", provider: "gemini" },
  { label: "Gemini 3.1 Flash Lite", value: "gemini-3.1-flash-lite-preview", provider: "gemini" },
] as const

export type LLMProvider = "openai" | "gemini" | "unknown"

/** 모델명으로 Provider (OpenAI/Gemini) 판별 */
export function getModelProvider(modelName: string): LLMProvider {
  if (!modelName) return "unknown"
  const lower = modelName.toLowerCase()
  if (lower.startsWith("gpt")) return "openai"
  if (lower.startsWith("gemini")) return "gemini"
  return "unknown"
}

// --- Plan 타입 옵션 ---
export const PLAN_TYPE_OPTIONS = [
  { label: "무료 (Free)", value: "FREE" },
  { label: "프로 (Pro)", value: "PRO" },
] as const

// --- 봇 생성 폼 Zod 스키마 ---
export const botFormSchema = z.object({
  name: z.string().min(2, { message: "봇 이름은 최소 2자 이상이어야 합니다." }),
  description: z.string(),
  tags: z.array(z.string()),
  is_active: z.boolean(),
  system_prompt: z.string().min(1, { message: "시스템 프롬프트는 필수입니다." }),
  llm_model: z.string().min(1, { message: "LLM 모델을 선택해 주세요." }),
})

export type BotFormValues = z.infer<typeof botFormSchema>

// --- 봇 수정 폼 Zod 스키마 (생성 폼 + 운영 메타데이터 필드 포함) ---
export const botEditFormSchema = z.object({
  name: z.string().min(2, { message: "봇 이름은 최소 2자 이상이어야 합니다." }),
  description: z.string(),
  tags: z.array(z.string()),
  is_active: z.boolean(),
  is_verified: z.boolean(),
  is_new: z.boolean(),
  plan_required: z.enum(["FREE", "PRO"]),
  system_prompt: z.string().min(1, { message: "시스템 프롬프트는 필수입니다." }),
  llm_model: z.string().min(1, { message: "LLM 모델을 선택해 주세요." }),
})

export type BotEditFormValues = z.infer<typeof botEditFormSchema>
