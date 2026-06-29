/**
 * 레드팀 피드백 도메인 — BE 응답 타입 정의.
 * backend/app/schemas/redteam.py 기반.
 */

export type ReflectValue = "pending" | "reflect" | "skip"

export type ReviewItem = {
  reviewer: string
  correct_answer: string
  week1_reflect: ReflectValue
  week2_reflect: ReflectValue
  week3_reflect: ReflectValue
  updated_at: string | null
}

export type ResponseItem = {
  id: number
  week: number
  submitter: string | null
  submitted_at: string | null
  question: string
  category: string | null
  rating: number | null
  risk: string | null
  bot_responses: Record<string, string | null> | null
  feedback_text: string | null
  match_score: number | null
  match_status: string
}

export type ReviewerStatus = {
  reviewer: string
  filled: boolean
}

export type GroupSummary = {
  id: number
  question: string
  category: string | null
  category_source: string
  risk: string | null
  week2_matched: boolean
  week1_matched: boolean
  review_status: ReviewerStatus[]
}

export type GroupListResponse = {
  groups: GroupSummary[]
  total: number
  page: number
  page_size: number
}

export type GroupDetail = {
  id: number
  question: string
  question_norm: string
  category: string | null
  category_source: string
  risk: string | null
  base_responses: ResponseItem[]
  week2_responses: ResponseItem[]
  week1_responses: ResponseItem[]
  reviews: ReviewItem[]
}

export type CandidateItem = {
  id: number
  week: number
  question: string
  submitter: string | null
  category: string | null
  match_score: number | null
}

export type StatsResponse = {
  total_groups: number
  total_responses: number
  by_category: Record<string, number>
  by_risk: Record<string, number>
  matched_week2: number
  matched_week1: number
  review_progress: Record<string, number>
}

export type GroupListParams = {
  category?: string
  risk?: string
  week_present?: 1 | 2
  matched_only?: boolean
  q?: string
  page?: number
  page_size?: number
}

export type ReviewUpsertRequest = {
  group_id: number
  reviewer: string
  correct_answer: string
  week1_reflect: ReflectValue
  week2_reflect: ReflectValue
  week3_reflect: ReflectValue
}

// ─── 보고용 리포트 ─────────────────────────────────────────────

export type ReportSummary = {
  total_groups: number
  total_responses: number
  responses_by_week: Record<string, number>
  high_risk: number
  mid_risk: number
  avg_rating_week1: number | null
  avg_rating_week3: number | null
  bot_c: number
  bot_d: number
  bot_none: number
}

export type TopRiskQuestion = {
  group_id: number
  question: string
  category: string | null
  risk: string | null
  rating_avg: number | null
}

export type ImprovementRow = {
  group_id: number
  question: string
  category: string | null
  week1_avg: number
  week3_avg: number
  delta: number
}

export type BotImprovement = {
  improved: number
  same: number
  declined: number
  compared: number
  top_improved: ImprovementRow[]
  top_declined: ImprovementRow[]
}

export type PendingHighRisk = {
  group_id: number
  question: string
  category: string | null
  risk: string | null
  reviewer_count: number
}

export type SplitGroup = {
  group_id: number
  question: string
  category: string | null
  risk: string | null
  reflect: number
  skip: number
}

export type ReviewerAgreement = {
  unanimous_reflect: number
  unanimous_skip: number
  split: number
}

export type ReportResponse = {
  summary: ReportSummary
  risk_distribution: { level: string; count: number }[]
  category_distribution: { category: string; count: number }[]
  risk_by_category: { category: string; 없음: number; 하: number; 중: number; 상: number }[]
  rating_by_week: { rating: number; week1: number; week3: number }[]
  rating_trend: { week: number; label: string; avg: number | null; count: number }[]
  bot_preference: { bot: string; count: number }[]
  bot_by_category: { category: string; C: number; D: number; 부적절: number }[]
  reflect_summary: { week: number; reflect: number; skip: number; pending: number }[]
  reflect_by_risk: { risk: string; reflect: number; skip: number; pending: number }[]
  reviewer_agreement: ReviewerAgreement
  pending_high_risk: PendingHighRisk[]
  split_groups: SplitGroup[]
  bot_improvement: BotImprovement
  top_risk_questions: TopRiskQuestion[]
}
