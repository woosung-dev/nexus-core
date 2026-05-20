// 봇 선택 직후 들어오는 라우트. 서버에서 빈 세션을 미리 생성한 뒤 영구 URL(/chat/{id})로 즉시 교체한다.
// 이렇게 하면 첫 메시지 시점부터 sessionId 가 항상 존재해 PENDING 캐시·migration·route churn 이 원천 제거.
"use client";

import { useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import api from "@/lib/api";
import { ChatSessionListResponse, ChatSessionResponse } from "@/types/api";

export default function NewChatRedirectPage() {
  const router = useRouter();
  const params = useParams<{ bot_id: string }>();
  const queryClient = useQueryClient();
  // StrictMode 의 effect 중복 실행으로 세션을 두 번 만들지 않도록 가드.
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    const botId = params?.bot_id;
    if (!botId) return;
    startedRef.current = true;

    api
      .post<ChatSessionResponse>(`/chats?bot_id=${botId}`)
      .then((res) => {
        const created = res.data;

        // 사이드바 목록 캐시에 prepend. 백엔드가 idempotent 라 기존 세션이 재사용될 수 있으므로
        // 같은 id 가 이미 있으면 중복 추가 대신 맨 위로만 올린다.
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

        router.replace(`/chat/${created.id}`);
      })
      .catch((err) => {
        console.error("Failed to create chat session:", err);
        startedRef.current = false; // 사용자가 다시 시도할 수 있도록
        router.replace("/");
      });
  }, [params, router, queryClient]);

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 text-zinc-400 bg-linear-to-b from-sky-50/50 via-white to-white">
      <Loader2 className="w-6 h-6 animate-spin text-amber-500" />
      <span className="text-sm font-medium">대화를 준비하고 있어요…</span>
    </div>
  );
}
