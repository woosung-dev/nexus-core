/**
 * Backend API와 동기화된 타입 정의
 * backend/app/schemas/ 및 models/ 참조
 */

export type PlanType = "FREE" | "PRO";

export type MessageRole = "user" | "assistant" | "system";

export interface BotResponse {
  id: number;
  name: string;
  description: string;
  image_url: string | null;
  tags: string[];
  is_verified: boolean;
  is_new: boolean;
  plan_required: PlanType;
  llm_model: string;
  system_prompt: string;
}

export interface BotListResponse {
  bots: BotResponse[];
  total: number;
}

export interface ChatSessionResponse {
  id: number;
  bot_id: number | null;
  bot: BotResponse | null;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatSessionListResponse {
  sessions: ChatSessionResponse[];
  total: number;
}

// 봇 답변이 참고한 RAG 출처 (backend RAGCitation 의 title/content 부분).
export interface Citation {
  title?: string | null;
  content?: string | null;
  // true = 표시된 답변이 직접 인용한 것이 아니라, 같은 질문으로 재검색한 근사 출처.
  approximate?: boolean | null;
  uri?: string | null;
  page_number?: number | null;
  // 이 청크가 뒷받침한 구간 수. 문서 단위 랭킹 점수로만 쓴다(수치 노출 금지 — 근사 인용의
  // 구간은 표시된 답변이 아니라 백필이 새로 생성한 답변 기준이므로).
  cite_count?: number | null;
  // 이 청크가 뒷받침한 답변 본문 구간. 답변에 그대로 존재해 문자열 검색으로 앵커할 수 있다.
  segments?: string[] | null;
  // content 중 실제 근거가 된 구절 — 형광펜 대상. 백엔드가 원문 대조로 스냅해 넣으므로
  // 항상 content 의 부분문자열이다(모델이 지어낸 문자는 들어오지 않는다).
  evidence?: string[] | null;
}

export interface MessageResponse {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  citations?: Citation[] | null;
  followups?: string[] | null;
  feedback?: "up" | "down" | null;
  feedback_reasons?: string[];
  feedback_comment?: string | null;
  created_at: string;
}

export type FeedbackType = "up" | "down";

export const POSITIVE_FEEDBACK_REASONS = [
  { code: "accurate", label: "정확함" },
  { code: "helpful", label: "도움 됨" },
  { code: "kind", label: "친절함" },
  { code: "clear", label: "명확함" },
  { code: "other", label: "기타" },
] as const;

export const NEGATIVE_FEEDBACK_REASONS = [
  { code: "inaccurate", label: "부정확함" },
  { code: "not_helpful", label: "도움 안 됨" },
  { code: "unsupported", label: "근거 부족" },
  { code: "too_long", label: "너무 김" },
  { code: "inappropriate", label: "부적절" },
  { code: "other", label: "기타" },
] as const;

export interface ChatCompletionRequest {
  bot_id: number;
  message: string;
  session_id?: number | null;
  stream?: boolean;
  use_rag?: boolean;
}

export interface ChatCompletionResponse {
  session_id: number;
  content: string;
  bot_id: number;
  citations?: Citation[] | null;
  // "faq_override" | "rag" | "llm" | "policy_block"
  source?: string | null;
  followups?: string[] | null;
}

export interface UserResponse {
  id: number;
  email?: string | null;
  display_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}
