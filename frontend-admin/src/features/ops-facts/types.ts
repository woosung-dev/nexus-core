/**
 * 운영 사실(ops_facts) 도메인 — BE 응답 타입.
 * backend/app/schemas/ops_facts.py 를 1:1로 옮긴 것.
 */

export type OpsFactKind =
  | "deprecated" // 폐지·현행 미적용 기준
  | "forbidden" // 존재하지 않는 제도·용어
  | "term" // 표기 통일 (응답 후처리 치환 대상)
  | "contact" // 검증된 연락처
  | "crisis" // 위기 자원

export type OpsFactStatus = "초안" | "승인" | "수정승인" | "반려"

export type OpsFactEvidence = {
  doc: string
  locator: string
  quote: string
}

export type OpsFactResponse = {
  id: number
  /** null 이면 전역 (모든 봇에 적용) */
  bot_id: number | null
  kind: OpsFactKind
  title: string
  /** 쓰면 안 되는 것 */
  superseded: string
  /** 대신 쓸 것 / 현행 사실 */
  statement: string
  /** 비면 항상 주입, 값이 있으면 질문에 그 표현이 있을 때만 주입 */
  triggers: string[]
  /** 채점기(L2)가 위반을 찾을 정규식. 비면 superseded 문자열 포함으로 검사 */
  detect: string[]
  evidence: OpsFactEvidence[]
  source_docs: string[]
  priority: number
  status: OpsFactStatus
  approver: string | null
  approved_at: string | null
  admin_note: string
  /** 관리자가 고치기 전 초안 원문 */
  draft_statement: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export type OpsFactListResponse = {
  items: OpsFactResponse[]
  total: number
}

export type OpsFactCreateRequest = {
  bot_id?: number | null
  kind: OpsFactKind
  title?: string
  superseded?: string
  statement?: string
  triggers?: string[]
  detect?: string[]
  evidence?: OpsFactEvidence[]
  source_docs?: string[]
  priority?: number
}

export type OpsFactUpdateRequest = Partial<Omit<OpsFactCreateRequest, "bot_id">> & {
  status?: OpsFactStatus
  approver?: string
  admin_note?: string
  is_active?: boolean
}

export type OpsFactListParams = {
  bot_id?: number
  scope?: "global"
  kind?: OpsFactKind
  status?: OpsFactStatus
}
