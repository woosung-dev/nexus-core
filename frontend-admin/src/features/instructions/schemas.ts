// 지침 빌더 폼의 선택지와 검증 스키마.
import { z } from "zod/v4"

export { LLM_MODEL_OPTIONS } from "@/features/bots/schemas"

export const TONE_PRESETS = [
  { label: "따뜻하고 공감적", value: "따뜻하고 공감적" },
  { label: "전문적·정확", value: "전문적이고 정확한" },
  { label: "간결·직설", value: "간결하고 직설적인" },
  { label: "목회적·신앙적", value: "목회적이고 신앙적인" },
  { label: "친근한 선배", value: "친근한 선배 같은" },
] as const

export const builderSchema = z.object({
  role: z.string(),
  goal: z.string(),
  tone: z.string(),
  audience: z.string(),
  constraints: z.string(),
  dos: z.array(z.string()),
  donts: z.array(z.string()),
  examples: z.array(z.object({ input: z.string(), output: z.string() })),
  system_prompt: z.string(),
  llm_model: z.string(),
})

export type BuilderValues = z.infer<typeof builderSchema>
