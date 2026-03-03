import { z } from "zod/v4"

// ─── FAQ 등록/수정 폼 Zod 스키마 ─────────────────────────────────
// react-hook-form의 useForm<T>은 입출력 타입이 동일해야 하므로,
// threshold를 string으로 유지하고 refine만 적용한다.
// Number 변환은 submit 핸들러에서 수행.
export const faqFormSchema = z.object({
  question: z
    .string()
    .min(2, { message: "질문은 최소 2자 이상이어야 합니다." }),
  answer: z
    .string()
    .min(1, { message: "답변은 필수 입력 항목입니다." }),
  threshold: z
    .string()
    .min(1, { message: "유사도 임계값은 필수입니다." })
    .refine(
      (val) => {
        const num = Number(val)
        return !isNaN(num) && num >= 0 && num <= 1
      },
      { message: "0.0 ~ 1.0 사이의 값을 입력해 주세요." }
    ),
})

/** 폼 값 타입 (threshold는 string — submit 시 Number 변환) */
export type FaqFormValues = z.infer<typeof faqFormSchema>
