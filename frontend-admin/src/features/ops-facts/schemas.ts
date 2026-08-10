import { z } from "zod"

/**
 * 운영 사실 등록 폼.
 *
 * `kind` 다섯은 전부 **부정·치환·연락처**다 — 모델 규약이 positive 지식("무엇이 맞다")을
 * 담지 않도록 설계돼 있기 때문이다(`backend/app/models/ops_facts.py`). 그래서 이 폼은
 * 「쓰면 안 되는 것 → 대신 쓸 것」 모양을 그대로 강제한다.
 *
 * 답이 어느 kind 에도 안 맞으면 그건 **문서를 채워야 하는 일**이지 덮개로 덮을 일이 아니다.
 */
export const opsFactCreateSchema = z.object({
  bot_id: z.number().nullable(),
  kind: z.enum(["deprecated", "forbidden", "term", "contact", "crisis"]),
  title: z.string().min(2, { message: "제목은 최소 2자 이상이어야 합니다." }),
  superseded: z.string(),
  statement: z.string().min(1, { message: "대신 쓸 내용은 필수입니다." }),
})

export type OpsFactCreateValues = z.infer<typeof opsFactCreateSchema>
