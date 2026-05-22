// 채팅 스트리밍 진행 상태 + 후속 질문 + (new flow 한정) 갓 생성된 세션 매핑.
//
// sessionId 의 단일 진실원은 URL (useParams) 이다. store 의 newFlowSession 은 오직
// `/chat/new/{botId}` URL 에서 POST /chats 직후 history.replaceState 로 URL 만 바꾼
// "useParams 가 아직 stale 인 짧은 윈도우" 동안에만 ChatLayout 의 fallback 으로 쓰인다.
// botId 키를 함께 갖고 있어 직전 봇의 잔존 값이 다른 봇 흐름에 새어들어가지 않는다.
import { create } from "zustand";

export interface NewFlowSession {
  botId: string;          // 현재 진행 중인 new flow 의 봇 (URL /chat/new/{botId} 와 일치해야 유효)
  sessionId: string | null;  // POST /chats 응답 후 채워짐. 그 전엔 null (Loader 단계).
}

interface ChatState {
  isStreaming: boolean;
  streamingText: string;
  // 가장 마지막 봇 응답의 후속 질문 (페이지 리로드 시 휘발 — ephemeral)
  latestFollowups: string[];
  // 입력창 텍스트. ChatComposer 가 controlled 로 읽고, FollowupPills 클릭 시
  // 즉시 전송 대신 이 값을 채워 사용자가 send 를 직접 누르도록 한다.
  composerDraft: string;
  // new flow 한정 세션 매핑 (URL 이 /chat/new/{botId} 인 동안에만 의미 있음)
  newFlowSession: NewFlowSession | null;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingText: (text: string) => void;
  setLatestFollowups: (items: string[]) => void;
  clearLatestFollowups: () => void;
  setComposerDraft: (text: string) => void;
  beginNewFlow: (botId: string) => void;
  completeNewFlow: (botId: string, sessionId: string) => void;
  clearNewFlow: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  isStreaming: false,
  streamingText: "",
  latestFollowups: [],
  composerDraft: "",
  newFlowSession: null,
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setStreamingText: (streamingText) => set({ streamingText }),
  setLatestFollowups: (latestFollowups) => set({ latestFollowups }),
  clearLatestFollowups: () => set({ latestFollowups: [] }),
  setComposerDraft: (composerDraft) => set({ composerDraft }),
  // new flow 시작 — 직전 봇의 잔존 값을 덮어쓴다. sessionId 는 아직 null.
  beginNewFlow: (botId) => set({ newFlowSession: { botId, sessionId: null } }),
  // POST 응답 도착 — 같은 botId 인지 확인 후 sessionId 채운다 (out-of-order 응답 방어).
  completeNewFlow: (botId, sessionId) =>
    set((s) =>
      s.newFlowSession?.botId === botId
        ? { newFlowSession: { botId, sessionId } }
        : s,
    ),
  clearNewFlow: () => set({ newFlowSession: null }),
}));
