// 용어집 도메인의 API 요청과 응답 타입을 정의합니다.
export type Glossary = {
  id: number
  bot_id: number | null
  term: string
  aliases: string[]
  definition: string
  priority: number
  threshold: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export type GlossaryListResponse = {
  terms: Glossary[]
  total: number
}

export type GlossaryCreateRequest = {
  term: string
  aliases: string[]
  definition: string
  bot_id?: number
  priority?: number
  threshold?: number
}

export type GlossaryUpdateRequest = Partial<
  Omit<GlossaryCreateRequest, "bot_id">
> & {
  is_active?: boolean
}
