// 채팅 스트리밍 진행 상태 + 후속 질문 + 활성 세션 ID. 유저 메시지는 React Query 캐시가 단일 진실원.
// activeSessionId 는 URL 의 useParams 대신 쓰는 단일 진실원 — Gemini 스타일 in-place URL 전환(history.replaceState) 을
// 가능하게 하기 위함. URL 은 history API 로 비동기적으로 갱신되고, ChatLayout/ChatArea 는 이 store 를 구독한다.
import { create } from "zustand";

interface ChatState {
  isStreaming: boolean;
  streamingText: string;
  // 가장 마지막 봇 응답의 후속 질문 (페이지 리로드 시 휘발 — ephemeral)
  latestFollowups: string[];
  // 현재 활성 세션 ID — Next.js useParams 대신 쓰는 단일 진실원
  activeSessionId: string | null;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingText: (text: string) => void;
  setLatestFollowups: (items: string[]) => void;
  clearLatestFollowups: () => void;
  setActiveSessionId: (id: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingText: "",
  latestFollowups: [],
  activeSessionId: null,
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingText: (streamingText) => set({ streamingText }),
  setLatestFollowups: (latestFollowups) => set({ latestFollowups }),
  clearLatestFollowups: () => set({ latestFollowups: [] }),
  setActiveSessionId: (activeSessionId) => set({ activeSessionId }),
}));
