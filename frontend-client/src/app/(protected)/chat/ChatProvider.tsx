// chat 도메인의 단일 상태 컨테이너.
// - URL (useParams) 을 watch 해서 phase/sessionId/botId 결정
// - 첫 submit 시점에 POST /chats → history.replaceState 로 URL 만 silent 변경 → POST /completions
// - 메시지 캐시는 React Query 가 권리원. 본 Provider 는 phase 와 임시 streaming/searching 상태만 보관.
"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useQueryClient, useQuery } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  ChatSessionListResponse,
  ChatSessionResponse,
  MessageResponse,
} from "@/types/api";
import { useChatStore } from "@/store/useChatStore";

export type ChatPhase =
  | "empty"        // /chat — 봇 미선택
  | "new"          // /chat/new/{botId} — 봇 선택, 첫 입력 대기
  | "session"      // /chat/{id} — 세션 활성, idle
  | "submitting"   // 첫 메시지 submit 직후, POST /chats 중
  | "searching"    // POST /completions 중 (Gemini 의 "찾고 있음" 단계)
  | "streaming";   // streaming 응답 중

interface ChatContextValue {
  phase: ChatPhase;
  sessionId: string | null;
  botId: string | null;
  messages: MessageResponse[];
  streamingText: string;
  // 화면에 보여줄 상태 라벨 ("찾고 있음…" 등). null 이면 비표시.
  statusLabel: string | null;
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

  // 내부 상태 — URL 이 1차 입력, submit/응답 단계는 setState 로 직접 갱신
  const [sessionId, setSessionId] = useState<string | null>(urlSessionId);
  const [botId, setBotId] = useState<string | null>(urlBotId);
  const [phase, setPhase] = useState<ChatPhase>(
    urlSessionId ? "session" : urlBotId ? "new" : "empty",
  );
  const [streamingText, setStreamingText] = useState("");
  const [statusLabel, setStatusLabel] = useState<string | null>(null);

  // URL 변경(사이드바 클릭, 뒤로가기) → 내부 상태 sync
  // history.replaceState 는 useParams 를 변경하지 않으므로 안전.
  useEffect(() => {
    if (urlSessionId) {
      setSessionId(urlSessionId);
      setBotId(null);
      setPhase("session");
    } else if (urlBotId) {
      setSessionId(null);
      setBotId(urlBotId);
      setPhase("new");
    } else {
      setSessionId(null);
      setBotId(null);
      setPhase("empty");
    }
    setStreamingText("");
    setStatusLabel(null);
  }, [urlSessionId, urlBotId]);

  // 메시지 캐시 (sessionId 있을 때만 fetch)
  const { data: messagesData } = useQuery<MessageResponse[]>({
    queryKey: ["messages", sessionId],
    queryFn: async () => {
      const token = await getToken({ template: "nexus-backend" });
      const res = await fetch(`/api/v1/chats/${sessionId}/messages`, {
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      });
      if (!res.ok) throw new Error("messages fetch failed");
      return res.json();
    },
    enabled: !!sessionId,
  });

  const messages = messagesData ?? [];

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;
      if (phase === "submitting" || phase === "searching" || phase === "streaming") return;

      let activeSessionId = sessionId;
      const activeBotId = botId;
      clearLatestFollowups();

      try {
        const token = await getToken({ template: "nexus-backend" });

        // 1) submit-time 세션 생성 (없을 때만)
        if (!activeSessionId) {
          if (!activeBotId) {
            console.error("sendMessage: 세션도 봇도 없음");
            return;
          }
          setPhase("submitting");
          setStatusLabel("대화를 준비하고 있어요…");

          const createRes = await fetch(`/api/v1/chats?bot_id=${activeBotId}`, {
            method: "POST",
            headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
          });
          if (!createRes.ok) throw new Error(`세션 생성 실패 ${createRes.status}`);
          const created: ChatSessionResponse = await createRes.json();
          activeSessionId = String(created.id);

          // 사이드바 캐시 prepend (dedupe — 백엔드 idempotent precreate 대응)
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

          // ★ 핵심: history.replaceState 로 URL 만 변경 (Next.js 내부 route tree 보존)
          window.history.replaceState(
            window.history.state,
            "",
            `/chat/${activeSessionId}`,
          );

          // 내부 state 도 동기 — useParams 는 stale 이어도 ChatProvider 가 sessionId 를 알고 있음.
          setSessionId(activeSessionId);
        }

        // 2) 유저 메시지를 캐시에 즉시 append
        const tmpUserId = -Date.now();
        const tmpAssistantId = tmpUserId - 1;
        const sessionIdNum = parseInt(activeSessionId, 10);

        queryClient.setQueryData<MessageResponse[]>(
          ["messages", activeSessionId],
          (old = []) => [
            ...old,
            {
              id: tmpUserId,
              session_id: sessionIdNum,
              role: "user",
              content,
              created_at: new Date().toISOString(),
            },
          ],
        );

        // 3) /completions
        setPhase("searching");
        setStatusLabel("찾고 있어요…");

        // botId 확정 (세션을 막 만들었으면 이미 가짐, 기존 세션이면 캐시에서 추출)
        let resolvedBotId: number | undefined;
        if (activeBotId) {
          resolvedBotId = Number(activeBotId);
        } else {
          const chatData = queryClient.getQueryData<ChatSessionListResponse>(["chats"]);
          const found = chatData?.sessions.find(
            (s) => s.id === sessionIdNum,
          );
          if (found?.bot_id) resolvedBotId = found.bot_id;
        }
        if (!resolvedBotId) {
          throw new Error("botId resolve 실패");
        }

        const compRes = await fetch("/api/v1/chats/completions", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            message: content,
            bot_id: resolvedBotId,
            session_id: sessionIdNum,
            stream: false,
            use_rag: true,
          }),
        });
        if (!compRes.ok) throw new Error(`completions 실패 ${compRes.status}`);

        const contentType = compRes.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
          const data = await compRes.json();
          setPhase("streaming");
          setStatusLabel(null);

          queryClient.setQueryData<MessageResponse[]>(
            ["messages", activeSessionId],
            (old = []) => [
              ...old,
              {
                id: tmpAssistantId,
                session_id: sessionIdNum,
                role: "assistant",
                content: data.content || "",
                created_at: new Date().toISOString(),
              },
            ],
          );
          if (Array.isArray(data.followups) && data.followups.length > 0) {
            setLatestFollowups(data.followups);
          }
        } else {
          // SSE 스트리밍 — 챙겨두긴 하지만 현재 클라이언트는 stream:false 만 씀
          const reader = compRes.body?.getReader();
          if (!reader) throw new Error("no body reader");
          const decoder = new TextDecoder("utf-8");
          let tempText = "";
          setPhase("streaming");
          setStatusLabel(null);

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            for (const line of chunk.split("\n")) {
              if (!line.startsWith("data: ")) continue;
              const dataStr = line.replace("data: ", "").trim();
              if (dataStr === "[DONE]") continue;
              try {
                const data = JSON.parse(dataStr);
                if (typeof data.content === "string") {
                  tempText += data.content;
                  setStreamingText(tempText);
                }
              } catch {
                /* ignore partial json */
              }
            }
          }

          if (tempText) {
            queryClient.setQueryData<MessageResponse[]>(
              ["messages", activeSessionId],
              (old = []) => [
                ...old,
                {
                  id: tmpAssistantId,
                  session_id: sessionIdNum,
                  role: "assistant",
                  content: tempText,
                  created_at: new Date().toISOString(),
                },
              ],
            );
          }
        }

        queryClient.invalidateQueries({ queryKey: ["chats"] });
        setStreamingText("");
        setPhase("session");
        setStatusLabel(null);
      } catch (err) {
        console.error("sendMessage error:", err);
        setStreamingText("");
        setPhase(activeSessionId ? "session" : botId ? "new" : "empty");
        setStatusLabel(null);
      }
    },
    [phase, sessionId, botId, getToken, queryClient, setLatestFollowups, clearLatestFollowups],
  );

  return (
    <ChatContext.Provider
      value={{
        phase,
        sessionId,
        botId,
        messages,
        streamingText,
        statusLabel,
        sendMessage,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}
