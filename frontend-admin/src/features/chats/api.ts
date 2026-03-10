import { apiClient } from "@/lib/api-client";
import { ChatSession, ChatMessage, ChatFilter, FeedbackFilter, FeedbackMessageResponse } from "./schemas";

// [2단계] pagination 파라미터 공통 헬퍼
function appendPaginationParams(params: URLSearchParams, page = 1, pageSize = 10) {
  params.append("limit", pageSize.toString());
  params.append("offset", ((page - 1) * pageSize).toString());
}

export const chatApi = {
  getSessions: async (filters?: ChatFilter) => {
    const params = new URLSearchParams();
    if (filters?.title) params.append("title", filters.title);
    if (filters?.user_email) params.append("user_email", filters.user_email);
    if (filters?.bot_id) params.append("bot_id", filters.bot_id);
    if (filters?.role) params.append("role", filters.role);
    if (filters?.has_feedback && filters.has_feedback !== "all") {
      params.append("has_feedback", filters.has_feedback);
    }
    appendPaginationParams(params, filters?.page, filters?.pageSize);

    const response = await apiClient.get<{ items: ChatSession[]; total: number }>(
      "/api/v1/admin/chats",
      { params }
    );
    return response.data;
  },

  getMessagesBySession: async (sessionId: number) => {
    const response = await apiClient.get<ChatMessage[]>(
      `/api/v1/admin/chats/${sessionId}/messages`
    );
    return response.data;
  },

  getFeedbackMessages: async (filters?: FeedbackFilter) => {
    const params = new URLSearchParams();
    if (filters?.feedback_type && filters.feedback_type !== "all") {
      params.append("feedback_type", filters.feedback_type);
    }
    if (filters?.bot_id) params.append("bot_id", filters.bot_id);
    appendPaginationParams(params, filters?.page, filters?.pageSize);

    const response = await apiClient.get<{ items: FeedbackMessageResponse[]; total: number }>(
      "/api/v1/admin/chats/feedbacks",
      { params }
    );
    return response.data;
  },
};
