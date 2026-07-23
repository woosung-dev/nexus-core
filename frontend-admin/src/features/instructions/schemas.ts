// Gem(지침) 편집 폼의 검증 스키마와 모델 선택지.
import { z } from "zod/v4"

export { LLM_MODEL_OPTIONS } from "@/features/bots/schemas"

export const gemSchema = z.object({
  name: z.string().min(1, { message: "Gem의 이름을 지정해 주세요." }).max(200),
  description: z.string(),
  system_prompt: z.string(),
  llm_model: z.string(),
})

export type GemValues = z.infer<typeof gemSchema>
