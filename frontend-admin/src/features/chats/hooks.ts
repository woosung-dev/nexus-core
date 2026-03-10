import { useQuery } from "@tanstack/react-query";
import { chatApi } from "./api";
import { ChatFilter, FeedbackFilter } from "./schemas";

export const chatKeys = {
  all: ["chats"] as const,
  sessions: (filters: ChatFilter) => [...chatKeys.all, "sessions", filters] as const,
  messages: (sessionId: number) => [...chatKeys.all, "messages", sessionId] as const,
  feedbacks: (filters: FeedbackFilter) => [...chatKeys.all, "feedbacks", filters] as const,
};

// [3단계] 세션 목록 전용 훅 — page.tsx의 수동 fetch를 대체
export function useChatSessions(filters: ChatFilter) {
  return useQuery({
    queryKey: chatKeys.sessions(filters),
    queryFn: () => chatApi.getSessions(filters),
  });
}

export function useChatMessages(sessionId: number | null) {
  return useQuery({
    queryKey: chatKeys.messages(sessionId!),
    queryFn: () => chatApi.getMessagesBySession(sessionId!),
    enabled: sessionId !== null,
  });
}

export function useFeedbackMessages(filters: FeedbackFilter) {
  return useQuery({
    queryKey: chatKeys.feedbacks(filters),
    queryFn: () => chatApi.getFeedbackMessages(filters),
  });
}
