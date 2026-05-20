// 채팅 스트리밍 진행 상태 + 가장 최근 봇 응답에 딸려온 후속 질문. 유저 메시지는 React Query 캐시가 단일 진실원.
import { create } from "zustand";

interface ChatState {
  isStreaming: boolean;
  streamingText: string;
  // 가장 마지막 봇 응답의 후속 질문 (페이지 리로드 시 휘발 — ephemeral)
  latestFollowups: string[];
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingText: (text: string) => void;
  setLatestFollowups: (items: string[]) => void;
  clearLatestFollowups: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingText: "",
  latestFollowups: [],
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingText: (streamingText) => set({ streamingText }),
  setLatestFollowups: (latestFollowups) => set({ latestFollowups }),
  clearLatestFollowups: () => set({ latestFollowups: [] }),
}));
