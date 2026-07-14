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

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import {
  ChatSessionListResponse,
  ChatSessionResponse,
  MessageResponse,
} from "@/types/api";
import { useChatStore } from "@/store/useChatStore";
import { API_BASE_URL } from "@/lib/api";

/**
 * Clerk JWT 를 첨부한 fetch — 401 받으면 skipCache:true 로 fresh 토큰 minting 후 1회 자동 재시도.
 * Clerk SDK 의 ~50s 토큰 캐시와 60s JWT TTL 사이 타이밍 차이로 가끔 stale 토큰이 첨부되는 문제 회피.
 * (axios interceptor 와 동일한 패턴 — raw fetch 호출이라 직접 구현 필요.)
 */
async function authedFetch(
  url: string,
  init: RequestInit,
  getToken: (opts?: { template?: string; skipCache?: boolean }) => Promise<string | null>,
): Promise<Response> {
  const cached = await getToken({ template: "nexus-backend" });
  // Headers API 사용 — 호출자가 plain object / Headers 인스턴스 / [string,string][] 어느 형태를 줘도
  // 안전. plain object spread 만 쓰면 Headers 인스턴스가 그냥 비어버리는 footgun 있음.
  const headers = new Headers(init.headers);
  if (cached) headers.set("Authorization", `Bearer ${cached}`);

  let res = await fetch(url, { ...init, headers });
  if (res.status !== 401) return res;

  const fresh = await getToken({ template: "nexus-backend", skipCache: true });
  if (!fresh) return res;
  const retryHeaders = new Headers(init.headers);
  retryHeaders.set("Authorization", `Bearer ${fresh}`);
  res = await fetch(url, { ...init, headers: retryHeaders });
  return res;
}

// 단순화: 빈 상태 vs thread (메시지 영역 + 하단 입력) 두 가지뿐.
// /chat/new/{bot} 도 thread 의 빈 상태로 표시되어 입력칸이 처음부터 하단에 고정된다.
export type ChatPhase = "empty" | "thread";

interface ChatContextValue {
  phase: ChatPhase;
  sessionId: string | null;
  botId: string | null;
  messages: MessageResponse[];
  // 봇 응답을 기다리는 중. true 면 마지막 사용자 메시지 아래에 typing dots 노출.
  awaiting: boolean;
  // 사이드바 클릭/직접 URL 진입 시 해당 세션 메시지 fetch 중. 스켈레톤/스피너 표시용.
  isLoadingMessages: boolean;
  sendMessage: (content: string) => Promise<void>;
}

// 인용 백필(persona-free 재검색)은 응답 저장 후에야 시작해서 실서버 실측 ~15초 걸린다.
// 2초 간격 15회(최대 30초)로 그 지연을 덮는다 — 확보 즉시 중단하므로 대개 몇 회로 끝난다.
const CITATION_POLL_INTERVAL_MS = 2000;
const CITATION_POLL_MAX_TRIES = 15;

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
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [phase, setPhase] = useState<ChatPhase>(
    urlSessionId ? "thread" : urlBotId ? "thread" : "empty",
  );

  // in-flight sendMessage 가 응답을 받았을 때 사용자가 다른 세션으로 이동했는지 판단하기 위한 ref.
  // sessionId state 와 항상 sync — sendMessage 클로저에서 stale 한 sessionId 가 아닌 "지금 보고 있는" 세션을 비교.
  const activeSessionRef = useRef<string | null>(sessionId);
  useEffect(() => {
    activeSessionRef.current = sessionId;
  }, [sessionId]);

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
      setPhase("thread");
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
    if (!sessionId) {
      setIsLoadingMessages(false);
      return;
    }
    let cancelled = false;
    setIsLoadingMessages(true);
    (async () => {
      try {
        const res = await authedFetch(
          `${API_BASE_URL}/chats/${sessionId}/messages`,
          {},
          getToken,
        );
        if (!res.ok) return;
        const data: MessageResponse[] = await res.json();
        if (cancelled) return;
        setMessages((prev) => {
          // 사용자가 막 보낸 임시 메시지 보존 — 단, **현재 세션 의 것만**.
          // 세션 A 에서 보낸 직후 세션 B 로 사이드바 전환하면 A 의 임시 메시지가 B 화면에 새지 않도록.
          const sidNum = parseInt(sessionId, 10);
          const tempLocal = prev.filter((m) => m.id < 0 && m.session_id === sidNum);
          return [...data, ...tempLocal];
        });
      } catch (err) {
        console.error("messages fetch error", err);
      } finally {
        if (!cancelled) setIsLoadingMessages(false);
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
        // 세션이 없으면 (= /chat/new/{bot} 첫 submit) POST /chats 로 만들고 URL silent 변경
        if (!activeSessionId) {
          if (!activeBotId) throw new Error("no session or bot");
          const createRes = await authedFetch(
            `${API_BASE_URL}/chats?bot_id=${activeBotId}`,
            { method: "POST" },
            getToken,
          );
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
          // 방금 만든 세션 id 로 임시 user 메시지의 session_id 를 보정.
          // setSessionId 가 fetch effect 를 발화시키는데, 거기서 임시 메시지는 session-scoped
          // 필터(session_id === sidNum) 를 통과해야 살아남는다. 보정을 안 하면 sessionId=null
          // 시점에 들어간 session_id=0 짜리가 필터에서 탈락 → 첫 메시지가 화면에서 사라짐.
          const newSidNum = parseInt(activeSessionId, 10);
          setMessages((prev) =>
            prev.map((m) =>
              m.id < 0 && m.session_id === 0 ? { ...m, session_id: newSidNum } : m,
            ),
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
        const compRes = await authedFetch(
          `${API_BASE_URL}/chats/completions`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: trimmed,
              bot_id: resolvedBotId,
              session_id: parseInt(activeSessionId!, 10),
              stream: false,
              use_rag: true,
            }),
          },
          getToken,
        );
        if (!compRes.ok) throw new Error(`completions failed ${compRes.status}`);
        const data = await compRes.json();

        // ★ 응답 받은 시점에 사용자가 이미 다른 세션으로 이동했다면 state 오염 방지.
        // 사이드바 캐시(invalidate) 와 followups store 갱신은 그대로 (다른 세션과 무관).
        const stillOnSession = activeSessionRef.current === activeSessionId;

        if (Array.isArray(data.followups) && data.followups.length > 0) {
          setLatestFollowups(data.followups);
        }
        queryClient.invalidateQueries({ queryKey: ["chats"] });

        if (stillOnSession) {
          const assistantMsg: MessageResponse = {
            id: tmpAssistantId,
            session_id: parseInt(activeSessionId!, 10),
            role: "assistant",
            content: data.content || "",
            created_at: new Date().toISOString(),
          };
          setMessages((prev) => [...prev, assistantMsg]);

          // 서버에서 진짜 message id 를 갖는 메시지로 교체 — feedback PATCH 가 음수 임시 id 로
          // 호출되지 않도록. (음수는 PostgreSQL int32 범위를 벗어나 500 발생.)
          // 인용(citations)은 응답 반환 후 interactions 백필이 별도 세션으로 DB 에 늦게 채우므로,
          // 즉시 재조회로 못 잡으면 확보될 때까지 폴링해서 출처 카드를 노출한다.
          const refetchMessages = async (): Promise<MessageResponse[] | null> => {
            try {
              const res = await authedFetch(
                `${API_BASE_URL}/chats/${activeSessionId}/messages`,
                {},
                getToken,
              );
              // refetch 도중 사용자가 또 다른 세션으로 이동했을 수 있으므로 한 번 더 체크.
              if (res.ok && activeSessionRef.current === activeSessionId) {
                return (await res.json()) as MessageResponse[];
              }
            } catch (refetchErr) {
              // refetch 실패해도 사용자는 응답 자체는 본 상태 — silent. 다음 라우트 진입 시 정상화됨.
              console.warn("messages refetch after completion failed", refetchErr);
            }
            return null;
          };

          const hasCitations = (msgs: MessageResponse[]) =>
            msgs.some(
              (m) =>
                m.role === "assistant" &&
                Array.isArray(m.citations) &&
                m.citations.length > 0,
            );

          const first = await refetchMessages();
          if (first) setMessages(first);

          // 백필이 아직이면 확보될 때까지 폴링한다. 응답 반환을 막지 않도록 await 하지 않는다.
          // 이 시점엔 awaiting=false 라 사용자가 새 메시지를 보냈을 수 있으므로, 전체 교체 대신
          // id 로 citations 만 병합해 낙관적 메시지를 덮어쓰지 않는다.
          if (!first || !hasCitations(first)) {
            void (async () => {
              for (let i = 0; i < CITATION_POLL_MAX_TRIES; i++) {
                await new Promise((r) => setTimeout(r, CITATION_POLL_INTERVAL_MS));
                if (activeSessionRef.current !== activeSessionId) return;
                const next = await refetchMessages();
                if (!next || activeSessionRef.current !== activeSessionId) return;
                const citById = new Map(
                  next
                    .filter((m) => Array.isArray(m.citations) && m.citations.length > 0)
                    .map((m) => [m.id, m.citations]),
                );
                if (citById.size === 0) continue;
                setMessages((prev) =>
                  prev.map((m) =>
                    citById.has(m.id) ? { ...m, citations: citById.get(m.id) } : m,
                  ),
                );
                return;
              }
            })();
          }
        }
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
      value={{ phase, sessionId, botId, messages, awaiting, isLoadingMessages, sendMessage }}
    >
      {children}
    </ChatContext.Provider>
  );
}
