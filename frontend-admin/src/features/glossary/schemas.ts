// 용어집 등록과 수정 폼의 입력 규칙을 정의합니다.
import z from "zod/v4"

export const glossaryFormSchema = z.object({
  term: z.string().min(1, { message: "용어는 필수 입력 항목입니다." }),
  aliases: z.array(z.string()),
  definition: z.string().min(1, { message: "정의는 필수 입력 항목입니다." }),
  priority: z.coerce.number().default(100),
  threshold: z.coerce
    .number()
    .min(0, { message: "0.0 이상의 값을 입력해 주세요." })
    .max(1, { message: "1.0 이하의 값을 입력해 주세요." })
    .default(0.88),
  scope: z.enum(["global", "bot"]),
})

export type GlossaryFormValues = z.infer<typeof glossaryFormSchema>
