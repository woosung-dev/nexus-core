import { z } from "zod"

// ─── FAQ 등록/수정 폼 Zod 스키마 ─────────────────────────────────
export const faqFormSchema = z.object({
  question: z
    .string()
    .min(2, { message: "질문은 최소 2자 이상이어야 합니다." }),
  answer: z
    .string()
    .min(1, { message: "답변은 필수 입력 항목입니다." }),
  threshold: z.coerce
    .number()
    .min(0, { message: "0.0 이상의 값을 입력해 주세요." })
    .max(1, { message: "1.0 이하의 값을 입력해 주세요." }),
})

export type FaqFormValues = z.infer<typeof faqFormSchema>
