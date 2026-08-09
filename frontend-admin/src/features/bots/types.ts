/**
 * 봇 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/bot.py의 Pydantic 스키마를 기반으로 작성.
 */

// PlanType enum (backend/app/models/enums.py 동기화)
export type PlanType = "FREE" | "PRO"

export type ClarificationPolicyOption = {
  id: string
  label: string
}

export type ClarificationPolicyDocumentRef = {
  document_id: string
  label: string
}

export type ClarificationRequiredSlot = {
  id: string
  label: string
  question: string
  selection_mode: "single" | "multiple"
  options: ClarificationPolicyOption[]
  allow_custom: boolean
}

export type ClarificationPolicyRule = {
  id: string
  name: string
  enabled: boolean
  priority: number
  request_examples: string[]
  why_ask: string
  document_refs: ClarificationPolicyDocumentRef[]
  required_slots: ClarificationRequiredSlot[]
  when_unknown: "ask" | "handoff" | "allow_answer"
}

export type ClarificationPolicy = {
  enabled: boolean
  rules: ClarificationPolicyRule[]
}

export type ClarificationPolicyTestResponse = {
  status: "ask" | "ready" | "handoff"
  applied_rule_name: string | null
  matched: boolean
  missing_slots: string[]
  questions: ClarificationRequiredSlot[]
  document_refs: ClarificationPolicyDocumentRef[]
  message: string
}

export const DEFAULT_CLARIFICATION_POLICY: ClarificationPolicy = {
  enabled: false,
  rules: [],
}

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
  is_active: boolean
  llm_model: string
  system_prompt: string
  history_window: number
  evidence_policy_mode: "legacy" | "strict"
  // 근거를 무엇으로 조달할지. 미설정 봇은 서버가 file_search 로 채운다.
  retrieval_mode: "file_search" | "lexical" | "both"
  clarify_enabled: boolean
  clarification_policy: ClarificationPolicy
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
  evidence_policy_mode?: "legacy" | "strict"
  retrieval_mode?: "file_search" | "lexical" | "both"
  clarify_enabled?: boolean
  clarification_policy?: ClarificationPolicy
}

// PUT /api/v1/admin/bots/:id — 봇 수정 요청 (부분 업데이트)
export type BotUpdateRequest = Partial<BotCreateRequest> & {
  is_active?: boolean
  history_window?: number
}

// POST /api/v1/admin/bots/:id/image
export type BotImageUploadResponse = {
  bot_id: number
  image_url: string
}

// GET /api/v1/admin/bots/:id/kakao — 카카오 채널 단건
export interface KakaoChannelResponse {
  id: number
  bot_id: number
  kakao_bot_id: string
  is_active: boolean
  created_at: string
}

// GET /api/v1/admin/bots/:id/kakao — 카카오 채널 목록
export interface KakaoChannelListResponse {
  items: KakaoChannelResponse[]
  total: number
}
