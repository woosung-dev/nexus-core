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

export interface MessageResponse {
  id: number;
  session_id: number;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ChatCompletionRequest {
  bot_id: number;
  message: string;
  session_id?: number | null;
  stream?: boolean;
  use_rag?: boolean;
}

export interface UserResponse {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  is_active: boolean;
  created_at: string;
}
