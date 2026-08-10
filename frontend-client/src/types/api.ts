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

// 봇이 되물을 때 나오는 선택지 카드. 백엔드 `ChatClarification` 과 같은 모양이다.
// `questions` 는 관리자가 쓴 슬롯 문구 그대로다 — LLM 이 짓지 않는다.
export interface ClarificationQuestion {
  id: string;
  question: string;
  selection_mode: "single" | "multiple";
  options: string[];
  allow_custom: boolean;
  required: boolean;
  policy: boolean;
}

export interface ChatClarification {
  status: "ask" | "handoff";
  questions: ClarificationQuestion[];
  rule_id?: string | null;
  // 되묻기는 한 번까지. 이 값 + 1 을 다음 요청에 실어 보내면 서버가 판정을 건너뛴다.
  round: number;
}

export interface MessageResponse {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  citations?: Citation[] | null;
  followups?: string[] | null;
  // 되물은 턴에만 채워진다. 응답 직후 refetch 가 메시지를 통째로 갈아 끼우므로
  // DB 에서 다시 실려 온다 — 새로고침해도 카드가 남는다.
  clarification?: ChatClarification | null;
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
  // 되묻기 카드에 답해서 보내는 요청이면 그 라운드. 1 이상이면 서버가 판정을 건너뛴다.
  clarification_round?: number;
}

export interface ChatCompletionResponse {
  session_id: number;
  content: string;
  bot_id: number;
  citations?: Citation[] | null;
  // "faq_override" | "rag" | "llm" | "policy_block"
  //   | "clarification_ask" | "clarification_handoff"
  source?: string | null;
  followups?: string[] | null;
  clarification?: ChatClarification | null;
}

export interface UserResponse {
  id: number;
  email?: string | null;
  display_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}
