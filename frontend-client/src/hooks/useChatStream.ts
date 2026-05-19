// 채팅 전송 훅 — 유저 메시지를 React Query 캐시에 stable id 로 박아 넣어 라우트 전환 중 정체성 변동 없이 동일 노드로 유지한다.
import { useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { useChatStore } from "@/store/useChatStore";
import {
  ChatCompletionRequest,
  ChatSessionListResponse,
  ChatSessionResponse,
  MessageResponse,
} from "@/types/api";

interface UseChatStreamOptions {
  sessionId?: string;
}

// sessionId 가 아직 없을 때 보관하는 임시 캐시 키. ChatArea 도 같은 상수를 알고 있어야 함.
const PENDING_KEY = "__pending__";

export function useChatStream({ sessionId: initialSessionId }: UseChatStreamOptions) {
  const { isStreaming, setIsStreaming, setStreamingText } = useChatStore();
  const { getToken } = useAuth();
  // 현재 세션 ID를 추적 (선택적 리다이렉트 및 후속 메시지용)
  const currentSessionIdRef = useRef<string | undefined>(initialSessionId);
  const queryClient = useQueryClient();
  const router = useRouter();

  // initialSessionId가 바뀌면 ref 업데이트 (페이지 이동 대응)
  if (initialSessionId && initialSessionId !== currentSessionIdRef.current) {
    currentSessionIdRef.current = initialSessionId;
  }

  const sendMessage = useCallback(async (content: string, botId?: number) => {
    if (!content.trim() || isStreaming) return;

    // framer-motion key 안정성을 위해 클라이언트가 발급한 stable id. 음수로 발급해 서버 PK 와 충돌 회피.
    const tmpUserId = -Date.now();
    const tmpAssistantId = tmpUserId - 1;

    setIsStreaming(true);
    setStreamingText("");

    // 1) 유저 메시지를 즉시 캐시에 append (이전 optimisticUserMessage zustand 흐름 폐기)
    const initialKey = currentSessionIdRef.current ?? PENDING_KEY;
    queryClient.setQueryData<MessageResponse[]>(
      ["messages", initialKey],
      (old = []) => [
        ...old,
        {
          id: tmpUserId,
          session_id: currentSessionIdRef.current ? parseInt(currentSessionIdRef.current, 10) : 0,
          role: "user",
          content,
          created_at: new Date().toISOString(),
        },
      ],
    );

    try {
      const token = await getToken({ template: "nexus-backend" });

      let resolvedBotId = botId;

      // 봇 ID가 없고 현재 세션 ID가 존재한다면 사이드바 캐시에서 추출
      if (!resolvedBotId && currentSessionIdRef.current) {
        const cachedData = queryClient.getQueryData<ChatSessionListResponse>(["chats"]);
        if (cachedData?.sessions && Array.isArray(cachedData.sessions)) {
          const currentSession = cachedData.sessions.find(
            (chat: ChatSessionResponse) => chat.id.toString() === currentSessionIdRef.current,
          );
          if (currentSession?.bot_id) {
            resolvedBotId = currentSession.bot_id;
          }
        }
      }

      if (!resolvedBotId) {
        console.error("Bot ID is unexpectedly undefined");
        setIsStreaming(false);
        return;
      }

      const currentSessionId = currentSessionIdRef.current
        ? parseInt(currentSessionIdRef.current, 10)
        : undefined;

      const payload: ChatCompletionRequest = {
        message: content,
        bot_id: resolvedBotId,
        stream: false,
        use_rag: true,
        ...(currentSessionId ? { session_id: currentSessionId } : {}),
      };

      const response = await fetch("/api/v1/chats/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorDetail = await response.text();
        throw new Error(`Failed to send message: ${response.status} - ${errorDetail}`);
      }

      const contentType = response.headers.get("content-type");

      // JSON 응답 (RAG 사용 또는 stream:false)
      if (contentType?.includes("application/json")) {
        const data = await response.json();
        const newSessionId = data.session_id?.toString();
        const isFirstResponse = newSessionId && !currentSessionIdRef.current;

        if (isFirstResponse) {
          currentSessionIdRef.current = newSessionId;

          // 2) PENDING 캐시를 실제 세션 키로 이전, AI 메시지를 동일 흐름에 append
          const pending = queryClient.getQueryData<MessageResponse[]>([
            "messages",
            PENDING_KEY,
          ]) ?? [];
          queryClient.setQueryData<MessageResponse[]>(
            ["messages", newSessionId],
            [
              ...pending.map((m) => ({ ...m, session_id: parseInt(newSessionId, 10) })),
              {
                id: tmpAssistantId,
                session_id: parseInt(newSessionId, 10),
                role: "assistant",
                content: data.content || "",
                created_at: new Date().toISOString(),
              },
            ],
          );
          queryClient.removeQueries({ queryKey: ["messages", PENDING_KEY] });

          // 공유 layout 이 ChatLayout 인스턴스를 유지하므로 router.replace 가 안전.
          router.replace(`/chat/${newSessionId}`);
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        } else if (currentSessionIdRef.current) {
          // 기존 세션 — AI 메시지를 같은 캐시에 append
          queryClient.setQueryData<MessageResponse[]>(
            ["messages", currentSessionIdRef.current],
            (old = []) => [
              ...old,
              {
                id: tmpAssistantId,
                session_id: parseInt(currentSessionIdRef.current!, 10),
                role: "assistant",
                content: data.content || "",
                created_at: new Date().toISOString(),
              },
            ],
          );
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }

        return;
      }

      // SSE 스트리밍 분기 (현재 백엔드는 stream:false JSON 만 쓰지만 호환 유지)
      const headerSessionId = response.headers.get("x-chat-session-id");
      if (headerSessionId && !currentSessionIdRef.current) {
        currentSessionIdRef.current = headerSessionId;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) return;

      let tempText = "";
      let migrated = false;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const dataStr = line.replace("data: ", "").trim();
          if (dataStr === "[DONE]") continue;

          try {
            const data = JSON.parse(dataStr);

            // 최초 메타데이터 (세션 ID)
            if (data.session_id && !currentSessionIdRef.current) {
              const newId = data.session_id.toString();
              currentSessionIdRef.current = newId;
              const pending = queryClient.getQueryData<MessageResponse[]>([
                "messages",
                PENDING_KEY,
              ]) ?? [];
              queryClient.setQueryData<MessageResponse[]>(
                ["messages", newId],
                pending.map((m) => ({ ...m, session_id: parseInt(newId, 10) })),
              );
              queryClient.removeQueries({ queryKey: ["messages", PENDING_KEY] });
              router.replace(`/chat/${newId}`);
              queryClient.invalidateQueries({ queryKey: ["chats"] });
              migrated = true;
              continue;
            }

            // 본문 청크
            const chunkText: string | undefined = data.content
              ?? data.choices?.[0]?.delta?.content;
            if (chunkText) {
              tempText += chunkText;
              setStreamingText(tempText);
            }
          } catch {
            // 부분 청크 JSON 파싱 실패 무시
          }
        }
      }

      // SSE 종료 후 AI 메시지를 캐시에 영구 append (streamingText 와 동일 내용)
      if (currentSessionIdRef.current && tempText) {
        queryClient.setQueryData<MessageResponse[]>(
          ["messages", currentSessionIdRef.current],
          (old = []) => [
            ...old,
            {
              id: tmpAssistantId,
              session_id: parseInt(currentSessionIdRef.current!, 10),
              role: "assistant",
              content: tempText,
              created_at: new Date().toISOString(),
            },
          ],
        );
        if (migrated) {
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
      // 실패 시 PENDING 버킷의 유저 메시지는 남겨 사용자에게 보이도록 두고, 진행 상태만 정리.
    } finally {
      setIsStreaming(false);
      setStreamingText("");
    }
  }, [isStreaming, queryClient, router, getToken, setIsStreaming, setStreamingText]);

  return {
    sendMessage,
    isStreaming,
    newSessionId: currentSessionIdRef.current,
  };
}

export { PENDING_KEY };
