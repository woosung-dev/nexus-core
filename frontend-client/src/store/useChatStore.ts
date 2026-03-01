import { create } from "zustand";

interface ChatState {
  isStreaming: boolean;
  streamingText: string;
  optimisticUserMessage: string | null;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingText: (text: string) => void;
  setOptimisticUserMessage: (msg: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingText: "",
  optimisticUserMessage: null,
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingText: (streamingText) => set({ streamingText }),
  setOptimisticUserMessage: (optimisticUserMessage) => set({ optimisticUserMessage }),
}));
