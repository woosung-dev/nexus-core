import { z } from "zod";

export const chatMessageSchema = z.object({
  id: z.number(),
  session_id: z.number(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  feedback: z.string().nullable().optional(),
  created_at: z.string(),
});

export const chatSessionSchema = z.object({
  id: z.number(),
  bot_id: z.number().nullable(),
  bot_name: z.string().optional(),
  user_email: z.string().optional(),
  title: z.string(),
  like_count: z.number().optional().default(0),
  dislike_count: z.number().optional().default(0),
  created_at: z.string(),
  updated_at: z.string(),
});

export const chatFilterSchema = z.object({
  title: z.string().optional(),
  user_email: z.string().optional(),
  bot_id: z.string().optional(),
  role: z.string().optional(),
  has_feedback: z.string().optional(),
  page: z.number().optional(),
  pageSize: z.number().optional(),
});

export type ChatMessage = z.infer<typeof chatMessageSchema>;
export type ChatSession = z.infer<typeof chatSessionSchema>;
export type ChatFilter = z.infer<typeof chatFilterSchema>;

// [1단계] 피드백 메시지 전용 필터 타입
export interface FeedbackFilter {
  feedback_type?: string;
  bot_id?: string;
  reason?: string;
  session_id?: number;
  page?: number;
  pageSize?: number;
}

export interface FeedbackMessageResponse {
  id: number;
  session_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  feedback: "up" | "down";
  feedback_reasons?: string[];
  feedback_comment?: string | null;
  created_at: string;
  bot_name?: string | null;
  user_email?: string | null;
  session_title?: string | null;
}

export const POSITIVE_REASON_LABELS: Record<string, string> = {
  accurate: "정확함",
  helpful: "도움 됨",
  kind: "친절함",
  clear: "명확함",
  other: "기타",
};

export const NEGATIVE_REASON_LABELS: Record<string, string> = {
  inaccurate: "부정확함",
  not_helpful: "도움 안 됨",
  unsupported: "근거 부족",
  too_long: "너무 김",
  inappropriate: "부적절",
  other: "기타",
};

export const ALL_REASON_LABELS: Record<string, string> = {
  ...POSITIVE_REASON_LABELS,
  ...NEGATIVE_REASON_LABELS,
};
