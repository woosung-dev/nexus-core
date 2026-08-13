/**
 * 못 답한 질문 도메인 — BE 응답 타입.
 * backend/app/schemas/unanswered.py 를 1:1로 옮긴 것.
 */

/** 무엇을 관측했는가. 전부 **관찰**이지 추정이 아니다 — 검색 점수로 판정하지 않는다. */
export type UnansweredReason =
  | "empty_answer" // 최종 답변이 빈 문자열 — 유일하게 사용자 문구를 치환한다
  | "lexical_empty" // 어휘 1단이 빈손이라 file_search 로 폴백했다
  | "corpus_unavailable" // 어휘 코퍼스 자체가 없어 폴백했다
  | "self_refusal" // 봇이 스스로 「답할 수 없다」고 말했다

/** 어느 트랙의 일인가. `문서오류` 에서만 ops_facts 로 넘어간다. */
export type UnansweredTriage =
  | "미분류"
  | "문서없음" // 지식에 원본이 아예 없다 → Documents 업로드
  | "검색못함" // 원문엔 있는데 검색이 못 짚었다 → 검색기·위키 트랙
  | "문서오류" // 문서가 틀렸거나 낡았다 → ops_facts
  | "해당없음" // 규정으로 안 갈리는 질문 (신학·가치·심경)

/** 질문 그룹 1건 — 같은 질문이 23번 들어와도 관리자에겐 한 줄이다. */
export type UnansweredGroup = {
  /** 그룹 식별자. 정규화된 질문 문자열이다. */
  question_norm: string
  /** 가장 최근 발생의 원문 */
  question_text: string
  count: number
  last_seen: string
  bot_id: number | null
  reasons: UnansweredReason[]
  triage: UnansweredTriage
  ops_fact_id: number | null
  admin_note: string
}

export type UnansweredListResponse = {
  items: UnansweredGroup[]
  total: number
}

/** 개별 발생 — `session_id` 로 `/chats` 로 넘어간다. */
export type UnansweredOccurrence = {
  id: number
  bot_id: number | null
  session_id: number | null
  message_id: number | null
  question_text: string
  reason: UnansweredReason
  detail: Record<string, unknown>
  created_at: string
}

export type UnansweredOccurrenceListResponse = {
  items: UnansweredOccurrence[]
  total: number
}

export type UnansweredListParams = {
  bot_id?: number
  reason?: UnansweredReason
  triage?: UnansweredTriage
  days?: number
  sort?: "count" | "recent"
  limit?: number
  offset?: number
}

export type UnansweredTriageRequest = {
  question_norm: string
  triage: UnansweredTriage
  ops_fact_id?: number | null
  admin_note?: string | null
  triaged_by?: string | null
}

export type UnansweredTriageResponse = {
  question_norm: string
  triage: UnansweredTriage
  updated: number
}
