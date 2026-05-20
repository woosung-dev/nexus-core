// chat 도메인의 단일 상태 컨테이너.
//
// 설계 원칙:
// 1) phase 는 **3가지**만 갖는다: empty / composer / thread.
//    제출 직후 ~ 응답 도착 전까지의 중간 상태(submitting/searching/streaming) 는
//    별도 phase 가 아니라 thread 안의 `awaiting` 플래그로 표현 → 화면이 깜빡이지 않음.
// 2) 메시지는 Provider 의 로컬 state. 사용자가 submit 하는 순간 UI 에 즉시 push 한다 —
//    POST /chats 응답을 기다리는 동안 사용자가 자기 메시지를 못 보는 사고를 차단.
// 3) URL 은 history.replaceState 로만 갱신, Next.js 내부 route tree(__PRIVATE_NEXTJS_INTERNALS_TREE) 보존.
"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  ChatSessionListResponse,
  ChatSessionResponse,
  MessageResponse,
} from "@/types/api";
import { useChatStore } from "@/store/useChatStore";

export type ChatPhase = "empty" | "composer" | "thread";

interface ChatContextValue {
  phase: ChatPhase;
  sessionId: string | null;
  botId: string | null;
  messages: MessageResponse[];
  // 봇 응답을 기다리는 중. true 면 마지막 사용자 메시지 아래에 typing dots 노출.
  awaiting: boolean;
  sendMessage: (content: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat called outside <ChatProvider>");
  return ctx;
}

function parseSlug(slug: string[] | undefined): {
  urlSessionId: string | null;
  urlBotId: string | null;
} {
  const segs = slug ?? [];
  if (segs.length === 1 && /^\d+$/.test(segs[0])) {
    return { urlSessionId: segs[0], urlBotId: null };
  }
  if (segs.length === 2 && segs[0] === "new") {
    return { urlSessionId: null, urlBotId: segs[1] };
  }
  return { urlSessionId: null, urlBotId: null };
}

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const params = useParams<{ slug?: string[] }>();
  const queryClient = useQueryClient();
  const { getToken } = useAuth();
  const setLatestFollowups = useChatStore((s) => s.setLatestFollowups);
  const clearLatestFollowups = useChatStore((s) => s.clearLatestFollowups);

  const { urlSessionId, urlBotId } = parseSlug(params?.slug);

  const [sessionId, setSessionId] = useState<string | null>(urlSessionId);
  const [botId, setBotId] = useState<string | null>(urlBotId);
  const [messages, setMessages] = useState<MessageResponse[]>([]);
  const [awaiting, setAwaiting] = useState(false);
  const [phase, setPhase] = useState<ChatPhase>(
    urlSessionId ? "thread" : urlBotId ? "composer" : "empty",
  );

  // URL 변경(사이드바 클릭, 뒤로가기) → 내부 상태 sync.
  // history.replaceState 는 useParams 를 갱신하지 않으므로 안전.
  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId);
      setBotId(null);
      setPhase("thread");
      setAwaiting(false);
      setMessages([]); // 새 세션 메시지는 아래 fetch 에서 채움
    } else if (urlBotId) {
      setSessionId(null);
      setBotId(urlBotId);
      setPhase("composer");
      setAwaiting(false);
      setMessages([]);
    } else {
      setSessionId(null);
      setBotId(null);
      setPhase("empty");
      setAwaiting(false);
      setMessages([]);
    }
  }, [urlSessionId, urlBotId]);

  // sessionId 가 정해지면 기존 메시지 fetch (사이드바 클릭/직접 URL 진입 케이스)
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    (async () => {
      try {
        const token = await getToken({ template: "nexus-backend" });
        const res = await fetch(`/api/v1/chats/${sessionId}/messages`, {
          headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        });
        if (!res.ok) return;
        const data: MessageResponse[] = await res.json();
        if (cancelled) return;
        setMessages((prev) => {
          // 사용자가 막 보낸 임시 메시지(음수 id)가 있으면 보존
          const tempLocal = prev.filter((m) => m.id < 0);
          // 서버에서 받은 메시지에 중복(서버가 같은 메시지를 갖고 있는 경우) 없으면 그대로
          return [...data, ...tempLocal];
        });
      } catch (err) {
        console.error("messages fetch error", err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId, getToken]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || awaiting) return;

      const trimmed = content.trim();
      const tmpUserId = -Date.now();
      const tmpAssistantId = tmpUserId - 1;

      const userMsg: MessageResponse = {
        id: tmpUserId,
        session_id: sessionId ? parseInt(sessionId, 10) : 0,
        role: "user",
        content: trimmed,
        created_at: new Date().toISOString(),
      };

      // ★ 사용자 메시지 즉시 노출 + phase 'thread' 로 전환 (POST 응답 기다리는 동안의 빈 화면 차단)
      setMessages((prev) => [...prev, userMsg]);
      setPhase("thread");
      setAwaiting(true);
      clearLatestFollowups();

      let activeSessionId = sessionId;
      const activeBotId = botId;

      try {
        const token = await getToken({ template: "nexus-backend" });

        // 세션이 없으면 (= /chat/new/{bot} 첫 submit) POST /chats 로 만들고 URL silent 변경
        if (!activeSessionId) {
          if (!activeBotId) throw new Error("no session or bot");
          const createRes = await fetch(`/api/v1/chats?bot_id=${activeBotId}`, {
            method: "POST",
            headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          });
          if (!createRes.ok) throw new Error(`session create failed ${createRes.status}`);
          const created: ChatSessionResponse = await createRes.json();
          activeSessionId = String(created.id);

          // 사이드바 캐시 prepend (idempotent precreate dedupe)
          queryClient.setQueryData<ChatSessionListResponse>(
            ["chats"],
            (old) => {
              if (!old) return { sessions: [created], total: 1 };
              const filtered = old.sessions.filter((s) => s.id !== created.id);
              const wasNew = filtered.length === old.sessions.length;
              return {
                sessions: [created, ...filtered],
                total: wasNew ? old.total + 1 : old.total,
              };
            },
          );

          // URL 만 silent 변경 — Next.js 내부 route tree 보존
          window.history.replaceState(
            window.history.state,
            "",
            `/chat/${activeSessionId}`,
          );
          setSessionId(activeSessionId);
        }

        // botId 확정
        let resolvedBotId: number | undefined;
        if (activeBotId) {
          resolvedBotId = Number(activeBotId);
        } else {
          const chatData = queryClient.getQueryData<ChatSessionListResponse>(["chats"]);
          const found = chatData?.sessions.find(
            (s) => s.id === parseInt(activeSessionId!, 10),
          );
          if (found?.bot_id) resolvedBotId = found.bot_id;
        }
        if (!resolvedBotId) throw new Error("botId resolve 실패");

        // /completions
        const compRes = await fetch("/api/v1/chats/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: trimmed,
            bot_id: resolvedBotId,
            session_id: parseInt(activeSessionId!, 10),
            stream: false,
            use_rag: true,
          }),
        });
        if (!compRes.ok) throw new Error(`completions failed ${compRes.status}`);
        const data = await compRes.json();

        const assistantMsg: MessageResponse = {
          id: tmpAssistantId,
          session_id: parseInt(activeSessionId!, 10),
          role: "assistant",
          content: data.content || "",
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);

        if (Array.isArray(data.followups) && data.followups.length > 0) {
          setLatestFollowups(data.followups);
        }

        queryClient.invalidateQueries({ queryKey: ["chats"] });
      } catch (err) {
        console.error("sendMessage error:", err);
      } finally {
        setAwaiting(false);
      }
    },
    [
      awaiting,
      sessionId,
      botId,
      getToken,
      queryClient,
      setLatestFollowups,
      clearLatestFollowups,
    ],
  );

  return (
    <ChatContext.Provider
      value={{ phase, sessionId, botId, messages, awaiting, sendMessage }}
    >
      {children}
    </ChatContext.Provider>
  );
}
