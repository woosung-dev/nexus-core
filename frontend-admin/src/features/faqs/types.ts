/**
 * FAQ 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/faq.py의 Pydantic 스키마를 기반으로 작성.
 */

// GET /api/v1/admin/faqs/:id, GET /api/v1/admin/faqs?bot_id=
export type FaqResponse = {
  id: number
  bot_id: number
  question: string
  answer: string
  /** 유사도 임계값 (0.0 ~ 1.0). 이 값 이상이면 해당 FAQ 답변을 우선 출력 */
  threshold: number
  is_active: boolean
  created_at: string
  updated_at: string
}

// GET /api/v1/admin/faqs?bot_id= (목록)
export type FaqListResponse = {
  faqs: FaqResponse[]
  total: number
}

// POST /api/v1/admin/bots/{bot_id}/faqs — FAQ 등록 요청
export type FaqCreateRequest = {
  bot_id: number
  question: string
  answer: string
  threshold?: number
}

// PUT /api/v1/admin/faqs/:id — FAQ 수정 요청 (부분 업데이트)
export type FaqUpdateRequest = Partial<Omit<FaqCreateRequest, "bot_id">> & {
  is_active?: boolean
}
