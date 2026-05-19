// 채팅 스트리밍 진행 상태만 보관. 유저 메시지는 React Query 캐시가 단일 진실원이라 zustand 에 두지 않는다.
import { create } from "zustand";

interface ChatState {
  isStreaming: boolean;
  streamingText: string;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingText: (text: string) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingText: "",
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingText: (streamingText) => set({ streamingText }),
}));
