/**
 * 봇 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/bot.py의 Pydantic 스키마를 기반으로 작성.
 */

// PlanType enum (backend/app/models/enums.py 동기화)
export type PlanType = "FREE" | "PRO"

// GET /api/v1/admin/bots, GET /api/v1/admin/bots/:id
export type BotResponse = {
  id: number
  name: string
  description: string
  image_url: string | null
  tags: string[]
  is_verified: boolean
  is_new: boolean
  plan_required: PlanType
  llm_model: string
  system_prompt: string
}

// GET /api/v1/admin/bots (목록)
export type BotListResponse = {
  bots: BotResponse[]
  total: number
}

// POST /api/v1/admin/bots — 봇 생성 요청
export type BotCreateRequest = {
  name: string
  description: string
  image_url?: string | null
  tags?: string[]
  is_verified?: boolean
  is_new?: boolean
  plan_required?: PlanType
  system_prompt?: string
  llm_model?: string
}

// PUT /api/v1/admin/bots/:id — 봇 수정 요청 (부분 업데이트)
export type BotUpdateRequest = Partial<BotCreateRequest> & {
  is_active?: boolean
}

// POST /api/v1/admin/bots/:id/image
export type BotImageUploadResponse = {
  bot_id: number
  image_url: string
}
