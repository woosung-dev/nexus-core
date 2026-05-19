// 채팅 전송 훅. sessionId 는 화면에 들어오기 전에 이미 서버에서 생성돼 있으므로, 이 훅은
// 단 하나의 캐시 키 ['messages', sessionId] 에 메시지를 append 하는 단순한 흐름만 유지한다.
import { useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
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

export function useChatStream({ sessionId: initialSessionId }: UseChatStreamOptions) {
  const { isStreaming, setIsStreaming, setStreamingText } = useChatStore();
  const { getToken } = useAuth();
  const currentSessionIdRef = useRef<string | undefined>(initialSessionId);
  const queryClient = useQueryClient();

  // 라우트 이동 시 prop 갱신을 반영
  if (initialSessionId && initialSessionId !== currentSessionIdRef.current) {
    currentSessionIdRef.current = initialSessionId;
  }

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return;

    const sessionId = currentSessionIdRef.current;
    if (!sessionId) {
      console.error("sendMessage called without sessionId — 이 컴포넌트는 sessionId 가 보장된 상태에서만 마운트되어야 함");
      return;
    }

    // framer-motion key 안정성을 위한 클라이언트 발급 음수 id (서버 PK 와 충돌 회피)
    const tmpUserId = -Date.now();
    const tmpAssistantId = tmpUserId - 1;
    const sessionIdNum = parseInt(sessionId, 10);

    setIsStreaming(true);
    setStreamingText("");

    // 1) 유저 메시지를 캐시에 즉시 append
    queryClient.setQueryData<MessageResponse[]>(
      ["messages", sessionId],
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

    try {
      const token = await getToken({ template: "nexus-backend" });

      // 사이드바 캐시에서 봇 ID 추출 (세션 생성 시 prepend 되어 항상 있음)
      let resolvedBotId: number | undefined;
      const cachedData = queryClient.getQueryData<ChatSessionListResponse>(["chats"]);
      if (cachedData?.sessions && Array.isArray(cachedData.sessions)) {
        const currentSession = cachedData.sessions.find(
          (chat: ChatSessionResponse) => chat.id.toString() === sessionId,
        );
        if (currentSession?.bot_id) {
          resolvedBotId = currentSession.bot_id;
        }
      }

      if (!resolvedBotId) {
        console.error("Bot ID is unexpectedly undefined for session", sessionId);
        setIsStreaming(false);
        return;
      }

      const payload: ChatCompletionRequest = {
        message: content,
        bot_id: resolvedBotId,
        session_id: sessionIdNum,
        stream: false,
        use_rag: true,
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

      // JSON 응답 (RAG / stream:false)
      if (contentType?.includes("application/json")) {
        const data = await response.json();
        queryClient.setQueryData<MessageResponse[]>(
          ["messages", sessionId],
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
        queryClient.invalidateQueries({ queryKey: ["chats"] });
        return;
      }

      // SSE 스트리밍 분기
      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) return;

      let tempText = "";
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
            const chunkText: string | undefined =
              data.content ?? data.choices?.[0]?.delta?.content;
            if (chunkText) {
              tempText += chunkText;
              setStreamingText(tempText);
            }
          } catch {
            // 부분 JSON 무시
          }
        }
      }

      if (tempText) {
        queryClient.setQueryData<MessageResponse[]>(
          ["messages", sessionId],
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
      queryClient.invalidateQueries({ queryKey: ["chats"] });
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsStreaming(false);
      setStreamingText("");
    }
  }, [isStreaming, queryClient, getToken, setIsStreaming, setStreamingText]);

  return {
    sendMessage,
    isStreaming,
    newSessionId: currentSessionIdRef.current,
  };
}
