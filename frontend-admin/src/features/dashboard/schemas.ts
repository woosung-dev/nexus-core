import { z } from "zod";

// DTOs for Chats (재사용할 부분이지만, 순환 참조를 피하기 위해 필요한 필드만 정의하거나 분리된 파일을 사용할 수도 있음. 일단 독립적으로 정의)
export const dashboardFeedbackMessageSchema = z.object({
  id: z.number(),
  session_id: z.number(),
  role: z.string(),
  content: z.string(),
  feedback: z.string().nullable(),
  created_at: z.string(),
  session_title: z.string().nullable().optional(),
  bot_name: z.string().nullable().optional(),
  user_email: z.string().nullable().optional(),
});

export const dashboardStatsSchema = z.object({
  total_bots: z.number(),
  total_users: z.number(),
  today_chats: z.number(),
  cs_score_today: z.number(),
});

export const dailyChatTrendSchema = z.object({
  date: z.string(),
  count: z.number(),
});

export const botChatShareSchema = z.object({
  bot_name: z.string(),
  count: z.number(),
});

export const dashboardDataSchema = z.object({
  stats: dashboardStatsSchema,
  recent_trends: z.array(dailyChatTrendSchema),
  bot_shares: z.array(botChatShareSchema),
  recent_negative_feedbacks: z.array(dashboardFeedbackMessageSchema),
  recent_positive_feedbacks: z.array(dashboardFeedbackMessageSchema),
  neg_total: z.number(),
  pos_total: z.number(),
});

export type DashboardStats = z.infer<typeof dashboardStatsSchema>;
export type DailyChatTrend = z.infer<typeof dailyChatTrendSchema>;
export type BotChatShare = z.infer<typeof botChatShareSchema>;
export type DashboardData = z.infer<typeof dashboardDataSchema>;
export type DashboardFeedbackMessage = z.infer<typeof dashboardFeedbackMessageSchema>;
