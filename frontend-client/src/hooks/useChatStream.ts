import { useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { useChatStore } from "@/store/useChatStore";
import { ChatCompletionRequest, ChatSessionListResponse, ChatSessionResponse } from "@/types/api";

interface UseChatStreamOptions {
  sessionId?: string;
}

export function useChatStream({ sessionId: initialSessionId }: UseChatStreamOptions) {
  const { isStreaming, setIsStreaming, setStreamingText, setOptimisticUserMessage } = useChatStore();
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

    setIsStreaming(true);
    setStreamingText("");
    setOptimisticUserMessage(content);

    try {
      const supabase = createClient();
      const { data: { session } } = await supabase.auth.getSession();

      let resolvedBotId = botId;

      // 만약 봇 ID가 없고 현재 세션 ID가 존재한다면, 사이드바 목록 캐시에서 봇 ID를 찾음
      if (!resolvedBotId && currentSessionIdRef.current) {
        const cachedData = queryClient.getQueryData<ChatSessionListResponse>(['chats']);
        // ChatSessionListResponse는 { sessions: [], total: number } 구조임
        if (cachedData && cachedData.sessions && Array.isArray(cachedData.sessions)) {
          const currentSession = cachedData.sessions.find(
            (chat: ChatSessionResponse) => chat.id.toString() === currentSessionIdRef.current
          );
          if (currentSession && currentSession.bot_id) {
            resolvedBotId = currentSession.bot_id;
          }
        }
      }

      if (!resolvedBotId) {
        console.error("Bot ID is unexpectedly undefined");
        // 에러를 던져 UI 진행을 막거나 기본 행동 지정
        setIsStreaming(false);
        return;
      }

      const currentSessionId = currentSessionIdRef.current ? parseInt(currentSessionIdRef.current, 10) : undefined;
      
      const payload: ChatCompletionRequest = {
        message: content,
        bot_id: resolvedBotId!,
        stream: false,
        use_rag: true,
        ...(currentSessionId ? { session_id: currentSessionId } : {})
      };

      const fullUrl = "/api/v1/chats/completions";
      console.log(`[useChatStream] Sending request to: ${fullUrl}`, payload);

      const response = await fetch(fullUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {})
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        // 422 에러 발생 시 상세 로그 확인을 위해 response body 로깅 시도 가능
        const errorDetail = await response.text();
        throw new Error(`Failed to send message: ${response.status} - ${errorDetail}`);
      }

      // JSON 응답인 경우 (RAG 사용 시 또는 stream: false인 경우)
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        
        const newSessionId = data.session_id?.toString();
        if (newSessionId && !currentSessionIdRef.current) {
           currentSessionIdRef.current = newSessionId;
           // 낙관적으로 캐시 채우기
           queryClient.setQueryData(["messages", newSessionId], [
             { id: Date.now(), role: "user", content, created_at: new Date().toISOString() }
           ]);
           router.replace(`/chat/${newSessionId}`);
           queryClient.invalidateQueries({ queryKey: ["chats"] });
        }
        
        // 응답 텍스트를 UI에 즉시 반영한 뒤 쿼리 무효화로 새로고침
        setStreamingText(data.content || "");
        
        if (currentSessionIdRef.current) {
          // 서버에서 새로운 메시지들을 다 들고 올 때까지 명시적으로 기다림 (Promise 결의)
          await queryClient.invalidateQueries({ queryKey: ["messages", currentSessionIdRef.current] });
          queryClient.invalidateQueries({ queryKey: ["chats"] });
        }
        
        setIsStreaming(false);
        setStreamingText("");
        setOptimisticUserMessage(null);
        return;
      }

      // 1. 응답 헤더에서 새로 생성된 타겟 Session ID 추출 (만약 스트리밍일 경우, 헤더 방식 대비)
      const newSessionId = response.headers.get('x-chat-session-id');
      if (newSessionId && !currentSessionIdRef.current) {
         currentSessionIdRef.current = newSessionId;
         // 여기서 window.history.pushState('', '', `/chat/${newSessionId}`) 를 호출할 수도 있음
      }

      // 2. 메시지를 보냈으니(사용자 메시지 DB 적재 완), 즉시 캐시 무효화하여 보낸 메시지 화면에 띄움
      if (currentSessionIdRef.current) {
        queryClient.invalidateQueries({ queryKey: ["messages", currentSessionIdRef.current] });
      }

      // 3. SSE 스트림 파싱
      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");

      if (!reader) return;

      let tempText = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        // EventSource 포맷 파싱: `data: ...\n\n`
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') {
              continue;
            }
            try {
              const data = JSON.parse(dataStr);
              
              // 1. 세션 정보가 포함된 메타데이터인 경우 (최초 응답)
              if (data.session_id && !currentSessionIdRef.current) {
                const newId = data.session_id.toString();
                currentSessionIdRef.current = newId;
                // 낙관적으로 캐시 채우기
                queryClient.setQueryData(["messages", newId], [
                  { id: Date.now(), role: "user", content, created_at: new Date().toISOString() }
                ]);
                // 새로운 세션으로 URL 이동 (Next.js client-side navigation)
                router.replace(`/chat/${newId}`);
                queryClient.invalidateQueries({ queryKey: ["chats"] });
                continue;
              }

              // 2. 메시지 조각인 경우 (우리 서버 구조: { "content": "..." })
              if (data.content) {
                tempText += data.content;
                setStreamingText(tempText);
              }
              // 3. (Optional) 이전 OpenAI 호환 구조 대응
              else if (data.choices && data.choices[0].delta && data.choices[0].delta.content) {
                tempText += data.choices[0].delta.content;
                setStreamingText(tempText);
              }
            } catch {
              // JSON 파싱 에러 방지 (불완전한 청크 등)
            }
          }
        }
      }

      // 스트리밍 종료 후, 서버에 저장된 최종 Assistant 메시지가 포함된 기록 전체를 다시 불러옴
      if (currentSessionIdRef.current) {
        await queryClient.invalidateQueries({ queryKey: ["messages", currentSessionIdRef.current] });
        queryClient.invalidateQueries({ queryKey: ["chats"] }); // 사이드바 목록도 갱신
      }

    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsStreaming(false);
      setStreamingText("");
      setOptimisticUserMessage(null);
    }
  }, [isStreaming, queryClient, router, setIsStreaming, setStreamingText, setOptimisticUserMessage]);

  return {
    sendMessage,
    isStreaming,
    newSessionId: currentSessionIdRef.current,
  };
}
