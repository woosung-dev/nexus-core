/**
 * 중간보고 입력관리 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/redteam.py (관리 필드 확장) 기반. 공통 하위 타입은 redteam 도메인 재사용.
 */
import type { ResponseItem, ReviewItem, ReviewerStatus } from "../redteam/types"

export type { ResponseItem, ReviewItem, ReviewerStatus }

export type ManageStatus = "대기" | "진행중" | "검증완료"
export type Disposition = "학습" | "FAQ" | "미정"
export type ManageLevel = 0 | 1 | 2 | 3

export type ManageGroupSummary = {
  id: number
  question: string
  category: string | null
  category_source: string
  risk: string | null
  rating_avg: number | null // 전 주차 평균 평점(1-5), 평점 응답 없으면 null
  status: string
  level: number | null
  disposition: string
  tags: string[]
  assignee: string | null
  model_answer: string
  week3_present: boolean // 3주차에 출현(=3주차 기준)
  week2_matched: boolean // 2주차에 동일 질문 출현
  week1_matched: boolean // 1주차에 동일 질문 출현
  review_status: ReviewerStatus[]
}

export type ManageGroupListResponse = {
  groups: ManageGroupSummary[]
  total: number
  page: number
  page_size: number
}

export type ManageGroupDetail = {
  id: number
  question: string
  question_norm: string
  category: string | null
  category_source: string
  risk: string | null
  status: string
  level: number | null
  disposition: string
  tags: string[]
  assignee: string | null
  model_answer: string
  base_responses: ResponseItem[]
  week2_responses: ResponseItem[]
  week1_responses: ResponseItem[]
  reviews: ReviewItem[]
  feedback: ManageFeedbackItem[]
}

/**
 * 부분 업데이트 — 보낸 키만 갱신. 키를 생략하면 미변경, null을 명시하면 비우기.
 * (BE는 model_fields_set 기준으로 처리. JSON.stringify가 undefined 키를 제거하므로
 *  값을 건드리지 않을 필드는 undefined, 비울 필드는 null로 둔다.)
 */
export type GroupManageUpdate = {
  status?: ManageStatus
  level?: number | null
  disposition?: Disposition
  tags?: string[]
  assignee?: string | null
  model_answer?: string
}

export type ManageFeedbackItem = {
  id: number
  author: string
  content: string
  created_at: string | null
}

export type CompareWeekResponse = {
  week: number
  submitter: string | null
  same_question: boolean
  match_score: number | null
  rating: number | null
  risk: string | null
  feedback_text: string | null
  etc: string | null
  bots: Record<string, string | null>
  bot_note: string | null
}

export type GroupCompare = {
  id: number
  question: string
  category: string | null
  risk: string | null
  week3: CompareWeekResponse[]
  week2: CompareWeekResponse[]
  week1: CompareWeekResponse[]
}

export type ManageStatsResponse = {
  total_groups: number
  by_status: Record<string, number>
  by_level: Record<string, number>
  by_disposition: Record<string, number>
  by_tag: Record<string, number>
  week3_groups: number // 3주차 기준 질문 수
  prior_only_groups: number // 1·2주차 전용 질문 수
  multiweek_groups: number // 2개 주차 이상 출현
  assignee_load: Record<string, number>
}

export type UnmatchedItem = {
  id: number
  week: number
  question: string
  submitter: string | null
  category: string | null
  match_status: string
}

export type ManageReportResponse = {
  total_groups: number
  week3_groups: number
  prior_only_groups: number
  multiweek_groups: number
  rating: {
    week: number
    rated: number
    high_pct: number | null
    low_pct: number | null
    net: number | null
    avg: number | null
  }[]
  appropriate: { total: number; appropriate: number; inappropriate: number; rate: number | null }
  bot_pref: { C: number; D: number; none: number }
  risk_dist: { level: string; count: number; pct: number }[]
  high_risk: number
  category_dist: { category: string; count: number }[]
  risk_by_category: { category: string; 상: number; 중: number }[]
  top_risk_questions: {
    group_id: number
    question: string
    category: string | null
    risk: string | null
    rating_avg: number | null
  }[]
}

export type ManageGroupListParams = {
  category?: string
  risk?: string
  rating?: string // 평점 버킷: '5'~'1' | '없음'
  status?: string
  level?: number
  disposition?: string
  assignee?: string
  tag?: string
  origin?: "week3" | "prior" // 3주차 기준 | 1·2주차 전용
  multiweek?: boolean // 2개 주차 이상 출현
  week_present?: 1 | 2 | 3
  matched_only?: boolean
  q?: string
  page?: number
  page_size?: number
}
